# pragma: no cover

import asyncio
import base64
import hashlib
import logging
from datetime import datetime
from typing import Any, List, Optional, cast

import rclpy
import rclpy.client
import rclpy.node
import rclpy.qos
from fastapi import HTTPException
from rclpy.subscription import Subscription
from rmf_building_map_msgs.msg import AffineImage as RmfAffineImage
from rmf_building_map_msgs.msg import BuildingMap as RmfBuildingMap
from rmf_building_map_msgs.msg import Level as RmfLevel
from rmf_dispenser_msgs.msg import DispenserState as RmfDispenserState
from rmf_door_msgs.msg import DoorMode as RmfDoorMode
from rmf_door_msgs.msg import DoorRequest as RmfDoorRequest
from rmf_door_msgs.msg import DoorState as RmfDoorState
from rmf_fleet_msgs.msg import BeaconState as RmfBeaconState
from rmf_fleet_msgs.msg import DeliveryAlert as RmfDeliveryAlert
from rmf_fleet_msgs.msg import DeliveryAlertAction as RmfDeliveryAlertAction
from rmf_fleet_msgs.msg import DeliveryAlertCategory as RmfDeliveryAlertCategory
from rmf_fleet_msgs.msg import DeliveryAlertTier as RmfDeliveryAlertTier
from rmf_fleet_msgs.msg import MutexGroupManualRelease as RmfMutexGroupManualRelease
from rmf_ingestor_msgs.msg import IngestorState as RmfIngestorState
from rmf_lift_msgs.msg import LiftRequest as RmfLiftRequest
from rmf_lift_msgs.msg import LiftState as RmfLiftState
from rmf_task_msgs.srv import CancelTask as RmfCancelTask
from rmf_task_msgs.srv import SubmitTask as RmfSubmitTask
from rosidl_runtime_py.convert import message_to_ordereddict
from std_msgs.msg import Bool as BoolMsg

from api_server.fast_io.singleton_dep import SingletonDep
from api_server.repositories.rmf import RmfRepository
from api_server.rmf_io.events import RmfEvents

from .models import (
    BeaconState,
    BuildingMap,
    DeliveryAlert,
    DispenserState,
    DoorState,
    FireAlarmTriggerState,
    IngestorState,
    LiftState,
)
from .repositories import CachedFilesRepository


class RmfGateway(SingletonDep):
    def __init__(
        self,
        cached_files: CachedFilesRepository,
        ros_node: rclpy.node.Node,
        rmf_events: RmfEvents,
        rmf_repo: RmfRepository,
        *,
        logger: Optional[logging.Logger] = None,
    ):
        self._cached_files = cached_files
        self._ros_node = ros_node
        self._rmf_events = rmf_events
        self._rmf_repo = rmf_repo
        self._logger = logger or logging.getLogger()

        self._door_req = self._ros_node.create_publisher(
            RmfDoorRequest, "adapter_door_requests", 10
        )

        transient_qos = rclpy.qos.QoSProfile(
            history=rclpy.qos.HistoryPolicy.KEEP_LAST,
            depth=100,
            reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
            durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self._adapter_lift_req = self._ros_node.create_publisher(
            RmfLiftRequest, "adapter_lift_requests", transient_qos
        )
        self._submit_task_srv = self._ros_node.create_client(
            RmfSubmitTask, "submit_task"
        )
        self._cancel_task_srv = self._ros_node.create_client(
            RmfCancelTask, "cancel_task"
        )

        self._delivery_alert_response = self._ros_node.create_publisher(
            RmfDeliveryAlert,
            "delivery_alert_response",
            rclpy.qos.QoSProfile(
                history=rclpy.qos.HistoryPolicy.KEEP_LAST,
                depth=10,
                reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
                durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL,
            ),
        )

        self._mutex_group_release = self._ros_node.create_publisher(
            RmfMutexGroupManualRelease,
            "mutex_group_manual_release",
            rclpy.qos.QoSProfile(
                history=rclpy.qos.HistoryPolicy.KEEP_LAST,
                depth=10,
                reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
                durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL,
            ),
        )

        self._fire_alarm_trigger = self._ros_node.create_publisher(
            BoolMsg,
            "fire_alarm_trigger",
            rclpy.qos.QoSProfile(
                history=rclpy.qos.HistoryPolicy.KEEP_LAST,
                depth=10,
                reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
                durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL,
            ),
        )

        self._subscriptions: List[Subscription] = []

        self._subscribe_all()

    async def call_service(self, client: rclpy.client.Client, req, timeout=1) -> Any:
        """
        Utility to wrap a ros service call in an awaitable,
        raises HTTPException if service call fails.
        """
        fut = client.call_async(req)
        try:
            result = await asyncio.wait_for(fut, timeout=timeout)
            return result
        except asyncio.TimeoutError as e:
            raise HTTPException(503, "ros service call timed out") from e

    def _process_building_map(
        self,
        rmf_building_map: RmfBuildingMap,
    ) -> BuildingMap:
        """
        1. Converts a `BuildingMap` message to an ordered dict.
        2. Saves the images into `{cache_directory}/{map_name}/`.
        3. Change the `AffineImage` `data` field to the url of the image.
        """
        processed_map = message_to_ordereddict(rmf_building_map)

        for i, level in enumerate(rmf_building_map.levels):
            level: RmfLevel
            for j, image in enumerate(level.images):
                image = cast(RmfAffineImage, image)
                # look at non-crypto hashes if we need more performance
                sha1_hash = hashlib.sha1()
                sha1_hash.update(image.data)
                fingerprint = base64.b32encode(sha1_hash.digest()).lower().decode()
                relpath = f"{rmf_building_map.name}/{level.name}-{image.name}.{fingerprint}.{image.encoding}"  # pylint: disable=line-too-long
                urlpath = self._cached_files.add_file(cast(bytes, image.data), relpath)
                processed_map["levels"][i]["images"][j]["data"] = urlpath
        return BuildingMap(**processed_map)

    def _subscribe_all(self):
        def handle_door_state(msg):
            async def save(door_state: DoorState):
                await self._rmf_repo.save_door_state(door_state)
                self._rmf_events.door_states.on_next(door_state)
                logging.debug("%s", door_state)

            asyncio.create_task(save(DoorState.model_validate(msg)))

        door_states_sub = self._ros_node.create_subscription(
            RmfDoorState,
            "door_states",
            handle_door_state,
            10,
        )
        self._subscriptions.append(door_states_sub)

        def handle_lift_state(msg):
            async def save(lift_state: LiftState):
                await self._rmf_repo.save_lift_state(lift_state)
                self._rmf_events.lift_states.on_next(lift_state)
                logging.debug("%s", lift_state)

            dic = message_to_ordereddict(msg)
            asyncio.create_task(save(LiftState(**dic)))

        lift_states_sub = self._ros_node.create_subscription(
            RmfLiftState,
            "lift_states",
            handle_lift_state,
            10,
        )
        self._subscriptions.append(lift_states_sub)

        def handle_dispenser_state(msg):
            async def save(dispenser_state: DispenserState):
                await self._rmf_repo.save_dispenser_state(dispenser_state)
                self._rmf_events.dispenser_states.on_next(dispenser_state)
                logging.debug("%s", dispenser_state)

            asyncio.create_task(save(DispenserState.model_validate(msg)))

        dispenser_states_sub = self._ros_node.create_subscription(
            RmfDispenserState,
            "dispenser_states",
            handle_dispenser_state,
            10,
        )
        self._subscriptions.append(dispenser_states_sub)

        def handle_ingestor_state(msg):
            async def save(ingestor_state: IngestorState):
                await self._rmf_repo.save_ingestor_state(ingestor_state)
                self._rmf_events.ingestor_states.on_next(ingestor_state)
                logging.debug("%s", ingestor_state)

            asyncio.create_task(save(IngestorState.model_validate(msg)))

        ingestor_states_sub = self._ros_node.create_subscription(
            RmfIngestorState,
            "ingestor_states",
            handle_ingestor_state,
            10,
        )
        self._subscriptions.append(ingestor_states_sub)

        def handle_building_map(msg):
            async def save(building_map: BuildingMap):
                await self._rmf_repo.save_building_map(building_map)
                self._rmf_events.building_map.on_next(building_map)
                logging.debug("%s", building_map)

            bm = self._process_building_map(cast(RmfBuildingMap, msg))
            asyncio.create_task(save(bm))

        map_sub = self._ros_node.create_subscription(
            RmfBuildingMap,
            "map",
            handle_building_map,
            rclpy.qos.QoSProfile(
                history=rclpy.qos.HistoryPolicy.KEEP_ALL,
                depth=1,
                reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
                durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL,
            ),
        )
        self._subscriptions.append(map_sub)

        def handle_beachandle_state(msg):
            async def save(beachandle_state: BeaconState):
                await self._rmf_repo.save_beacon_state(beachandle_state)
                self._rmf_events.beacons.on_next(beachandle_state)
                logging.debug("%s", beachandle_state)

            msg = cast(RmfBeaconState, msg)
            bs = BeaconState(
                id=msg.id,
                online=msg.online,
                category=msg.category,
                activated=msg.activated,
                level=msg.level,
            )
            asyncio.create_task(save(bs))

        beachandle_sub = self._ros_node.create_subscription(
            RmfBeaconState,
            "beachandle_state",
            handle_beachandle_state,
            10,
        )
        self._subscriptions.append(beachandle_sub)

        def handle_delivery_alert(msg):
            msg = cast(RmfDeliveryAlert, msg)
            da = DeliveryAlert(
                id=msg.id,
                category=DeliveryAlert.Category(msg.category.value),
                tier=DeliveryAlert.Tier(msg.tier.value),
                task_id=msg.task_id,
                action=DeliveryAlert.Action(msg.action.value),
                message=msg.message,
            )
            self._rmf_events.delivery_alerts.on_next(da)
            logging.debug("%s", da)

        delivery_alert_request_sub = self._ros_node.create_subscription(
            RmfDeliveryAlert,
            "delivery_alert_request",
            handle_delivery_alert,
            rclpy.qos.QoSProfile(
                history=rclpy.qos.HistoryPolicy.KEEP_LAST,
                depth=10,
                reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
                durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL,
            ),
        )
        self._subscriptions.append(delivery_alert_request_sub)

        def handle_fire_alarm_trigger(msg):
            async def save(delivery_alert: DeliveryAlert):
                # await self._rmf_repo.(delivery_alert)
                self._rmf_events.delivery_alerts.on_next(delivery_alert)
                logging.debug("%s", delivery_alert)

            msg = cast(BoolMsg, msg)
            if msg.data:
                logging.info("Fire alarm triggered")
            else:
                logging.info("Fire alarm trigger reset")
            fire_alarm_trigger_state = FireAlarmTriggerState(
                unix_millis_time=round(datetime.now().timestamp() * 1000),
                trigger=msg.data,
            )
            self._rmf_events.fire_alarm_trigger.on_next(fire_alarm_trigger_state)

        fire_alarm_trigger_sub = self._ros_node.create_subscription(
            BoolMsg,
            "fire_alarm_trigger",
            handle_fire_alarm_trigger,
            rclpy.qos.QoSProfile(
                history=rclpy.qos.HistoryPolicy.KEEP_LAST,
                depth=10,
                reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
                durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL,
            ),
        )
        self._subscriptions.append(fire_alarm_trigger_sub)

    async def __aexit__(self, *exc):
        for sub in self._subscriptions:
            sub.destroy()

    def request_door(self, door_name: str, mode: int) -> None:
        msg = RmfDoorRequest(
            door_name=door_name,
            request_time=self._ros_node.get_clock().now().to_msg(),
            requester_id=self._ros_node.get_name(),  # FIXME: use username
            requested_mode=RmfDoorMode(
                value=mode,
            ),
        )
        self._door_req.publish(msg)

    def request_lift(
        self,
        lift_name: str,
        destination: str,
        request_type: int,
        door_mode: int,
        additional_session_ids: List[str],
    ):
        msg = RmfLiftRequest(
            lift_name=lift_name,
            request_time=self._ros_node.get_clock().now().to_msg(),
            session_id=self._ros_node.get_name(),
            request_type=request_type,
            destination_floor=destination,
            door_state=door_mode,
        )
        self._adapter_lift_req.publish(msg)

        for session_id in additional_session_ids:
            msg.session_id = session_id
            self._adapter_lift_req.publish(msg)

    def respond_to_delivery_alert(
        self,
        alert_id: str,
        category: int,
        tier: int,
        task_id: str,
        action: int,
        message: str,
    ):
        msg = RmfDeliveryAlert()
        msg.id = alert_id
        msg.category = RmfDeliveryAlertCategory(value=category)
        msg.tier = RmfDeliveryAlertTier(value=tier)
        msg.task_id = task_id
        msg.action = RmfDeliveryAlertAction(value=action)
        msg.message = message
        self._delivery_alert_response.publish(msg)

    def manual_release_mutex_groups(
        self,
        mutex_groups: List[str],
        fleet: str,
        robot: str,
    ):
        msg = RmfMutexGroupManualRelease()
        msg.release_mutex_groups = mutex_groups
        msg.fleet = fleet
        msg.robot = robot
        self._mutex_group_release.publish(msg)

    def reset_fire_alarm_trigger(self):
        reset_msg = BoolMsg()
        reset_msg.data = False
        self._fire_alarm_trigger.publish(reset_msg)

from typing import List, Optional, Tuple, cast

from fastapi import Depends, HTTPException
from tortoise.exceptions import FieldError
from tortoise.query_utils import Prefetch
from tortoise.queryset import QuerySet

from api_server.authenticator import user_dep
from api_server.models import LogEntry, Pagination, TaskEventLog, TaskState, User
from api_server.models import tortoise_models as ttm
from api_server.models.tortoise_models import TaskState as DbTaskState
from api_server.query import add_pagination


class TaskRepository:
    def __init__(self, user: User):
        self.user = user

    async def query_task_states(
        self, query: QuerySet[DbTaskState], pagination: Optional[Pagination] = None
    ) -> List[TaskState]:
        try:
            if pagination:
                query = add_pagination(query, pagination)
            # TODO: enforce with authz
            results = await query.values_list("data", flat=True)
            return [TaskState(**r) for r in results]
        except FieldError as e:
            raise HTTPException(422, str(e))

    async def get_task_state(self, task_id: str) -> Optional[TaskState]:
        # TODO: enforce with authz
        result = await DbTaskState.get_or_none(id_=task_id)
        if result is None:
            return None
        return TaskState(**result.data)

    async def get_task_log(
        self, task_id: str, between: Tuple[int, int]
    ) -> Optional[TaskEventLog]:
        """
        :param between: The period in unix millis to fetch.
        """
        between_filters = {
            "unix_millis_time__gte": between[0],
            "unix_millis_time__lte": between[1],
        }
        result = cast(
            Optional[ttm.TaskEventLog],
            await ttm.TaskEventLog.get_or_none(task_id=task_id).prefetch_related(
                Prefetch(
                    "log",
                    ttm.TaskEventLogLog.filter(**between_filters),
                ),
                Prefetch(
                    "phases__log", ttm.TaskEventLogPhasesLog.filter(**between_filters)
                ),
                Prefetch(
                    "phases__events__log",
                    ttm.TaskEventLogPhasesEventsLog.filter(**between_filters),
                ),
            ),
        )
        if result is None:
            return None
        phases = {}
        for db_phase in result.phases:
            phase = {}
            phase["log"] = [LogEntry(**dict(x)) for x in db_phase.log]
            events = {}
            for db_event in db_phase.events:
                events[db_event.event] = [LogEntry(**dict(x)) for x in db_event.log]
            phase["events"] = events
            phases[db_phase.phase] = phase
        return TaskEventLog.construct(
            task_id=result.task_id,
            log=[LogEntry(**dict(x)) for x in result.log],
            phases=phases,
        )


def task_repo_dep(user: User = Depends(user_dep)):
    return TaskRepository(user)

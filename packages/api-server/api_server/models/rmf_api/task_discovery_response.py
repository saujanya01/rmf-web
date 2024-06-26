# generated by datamodel-codegen:
#   filename:  task_discovery_response.json

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from typing_extensions import Literal


class Task(BaseModel):
    category: str = Field(
        ...,
        description="The category of this task. There must not be any duplicate task categories per fleet.",
    )
    detail: str = Field(..., description="Details about the behavior of the task.")
    description_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="The schema for this task description"
    )


class Data(BaseModel):
    fleet_name: Optional[str] = Field(
        default=None, description="Name of the fleet that supports these tasks"
    )
    tasks: Optional[List[Task]] = Field(
        default=None, description="(list:replace) List of tasks that the fleet supports"
    )


class TaskDiscovery(BaseModel):
    type: Literal["task_discovery_update"] = Field(
        ..., description="Indicate that this is an task discovery update"
    )
    data: Data

# generated by datamodel-codegen:
#   filename:  task_description_Clean.json

from __future__ import annotations

from pydantic import Field, RootModel

from . import event_description_Clean


class CleanTask(RootModel[event_description_Clean.CleanEvent]):
    root: event_description_Clean.CleanEvent = Field(
        ..., description="Clean a zone", title="Clean Task"
    )

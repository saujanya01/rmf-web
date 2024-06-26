# generated by datamodel-codegen:
#   filename:  event_description_GoToPlace.json

from __future__ import annotations

from pydantic import Field, RootModel

from . import Place


class GoToPlaceEventDescription(RootModel[Place.PlaceDescription]):
    root: Place.PlaceDescription = Field(
        ...,
        description="Have a robot go to a place",
        title="Go To Place Event Description",
    )

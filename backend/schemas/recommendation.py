
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from schemas.common import BaseSchema, ORMResponseSchema


RecommendationStatus = Literal[
    "new",
    "accepted",
    "dismissed"
]

RecommendationText = Annotated[
    str,
    StringConstraints(min_length=1, max_length=5000)
]


class RecommendationCreate(BaseSchema):
    """Internal schema for creating an AI-generated recommendation."""

    recommendation_type: Annotated[
        str,
        StringConstraints(min_length=1, max_length=50)
    ] = Field(
        ...,
        description="Category of recommendation.",
        examples=["reorder", "slow_moving_stock"]
    )

    message: RecommendationText = Field(
        ...,
        description="Explanation of the recommendation."
    )


class RecommendationUpdate(BaseSchema):
    """Schema for updating a recommendation's status."""

    status: RecommendationStatus = Field(
        ...,
        description="Current status of the recommendation."
    )


class RecommendationResponse(ORMResponseSchema):
    """Response schema for displaying an AI recommendation."""

    id: int
    recommendation_type: str
    message: str
    status: RecommendationStatus
    created_at: datetime


from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Common configuration for StockSaathi API schemas."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True
    )


class ORMResponseSchema(BaseModel):
    """Base schema for responses created from ORM objects."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore"
    )

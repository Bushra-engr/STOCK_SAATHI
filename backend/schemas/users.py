from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator

from schemas.common import BaseSchema, ORMResponseSchema

PersonName = Annotated[str, StringConstraints(min_length=2, max_length=100)]
ShopName = Annotated[str, StringConstraints(min_length=2, max_length=150)]
ShopCategory = Annotated[str, StringConstraints(min_length=2, max_length=100)]

class UserCreate(BaseSchema):
    """Create the shop owner profile. The user ID comes from the verified login, never from here."""

    name: PersonName = Field(..., description="Shop owner's display name.")
    shop_name: ShopName = Field(..., examples=["Rahul General Store"])
    shop_category: ShopCategory | None = Field(default=None, examples=["Kirana"])

    @field_validator("name", "shop_name", mode="before")
    @classmethod
    def clean_required_fields(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator("shop_category", mode="before")
    @classmethod
    def clean_shop_category(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value if value else None
        return value

class UserUpdate(BaseSchema):
    name: PersonName | None = None
    shop_name: ShopName | None = None
    shop_category: ShopCategory | None = None

    @field_validator("name", "shop_name", mode="before")
    @classmethod
    def clean_optional_name(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value if value else None
        return value

    @field_validator("shop_category", mode="before")
    @classmethod
    def clean_optional_category(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value if value else None
        return value

class UserResponse(ORMResponseSchema):
    id: str
    name: str
    shop_name: str
    shop_category: str | None
    created_at: datetime

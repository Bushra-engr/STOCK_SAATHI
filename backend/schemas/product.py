
from typing import Annotated

from pydantic import Field, StringConstraints

from schemas.common import BaseSchema, ORMResponseSchema


ProductName = Annotated[
    str,
    StringConstraints(min_length=2, max_length=150)
]

ProductText = Annotated[
    str,
    StringConstraints(min_length=1, max_length=100)
]

ProductUnit = Annotated[
    str,
    StringConstraints(min_length=1, max_length=30)
]


class ProductCreate(BaseSchema):
    """Request schema for adding a product to the catalogue."""

    name: ProductName = Field(
        ...,
        description="Name of the product.",
        examples=["Maggi"]
    )

    brand: ProductText | None = Field(
        default=None,
        description="Product brand.",
        examples=["Nestle"]
    )

    category: ProductText | None = Field(
        default=None,
        description="Product category.",
        examples=["Packaged Food"]
    )

    variant: ProductText | None = Field(
        default=None,
        description="Product variant or pack size.",
        examples=["70g"]
    )

    unit: ProductUnit = Field(
        default="piece",
        description="Unit used to measure this product.",
        examples=["packet"]
    )


class ProductUpdate(BaseSchema):
    """Request schema for updating catalogue product details."""

    name: ProductName | None = None
    brand: ProductText | None = None
    category: ProductText | None = None
    variant: ProductText | None = None
    unit: ProductUnit | None = None


class ProductResponse(ORMResponseSchema):
    """Response schema for displaying product details."""

    id: int
    name: str
    brand: str | None
    category: str | None
    variant: str | None
    unit: str

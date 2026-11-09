from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field

from schemas.common import BaseSchema, ORMResponseSchema
from schemas.product import ProductResponse

NonNegativeQuantity = Annotated[
    Decimal, Field(ge=0, max_digits=12, decimal_places=3, allow_inf_nan=False)
]
NonNegativePrice = Annotated[
    Decimal, Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
]

class InventoryCreate(BaseSchema):
    product_id: int = Field(..., gt=0, examples=[1])
    current_stock: NonNegativeQuantity = Field(default=Decimal("0"))
    purchase_price: NonNegativePrice
    selling_price: NonNegativePrice
    reorder_level: NonNegativeQuantity = Field(default=Decimal("5"))

class InventoryUpdate(BaseSchema):
    current_stock: NonNegativeQuantity | None = None
    purchase_price: NonNegativePrice | None = None
    selling_price: NonNegativePrice | None = None
    reorder_level: NonNegativeQuantity | None = None

class InventoryResponse(ORMResponseSchema):
    id: int
    product_id: int
    current_stock: Decimal
    purchase_price: Decimal
    selling_price: Decimal
    reorder_level: Decimal
    updated_at: datetime
    product: ProductResponse | None = None

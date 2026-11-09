from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from schemas.common import BaseSchema, ORMResponseSchema

MovementType = Literal["opening_stock","purchase", "sale", "damage", "adjustment_in", "adjustment_out"]

PositiveQuantity = Annotated[
    Decimal, Field(gt=0, max_digits=12, decimal_places=3, allow_inf_nan=False)
]
NonNegativePrice = Annotated[
    Decimal, Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
]
MovementNotes = Annotated[str, StringConstraints(max_length=500)]

class StockMovementCreate(BaseSchema):
    inventory_id: int = Field(..., gt=0)
    movement_type: MovementType
    quantity: PositiveQuantity
    unit_price: NonNegativePrice | None = None
    unit_cost: NonNegativePrice | None = None
    notes: MovementNotes | None = None

class StockMovementResponse(ORMResponseSchema):
    id: int
    inventory_id: int
    movement_type: MovementType
    quantity: Decimal
    unit_price: Decimal | None
    unit_cost: Decimal | None
    notes: str | None
    created_at: datetime
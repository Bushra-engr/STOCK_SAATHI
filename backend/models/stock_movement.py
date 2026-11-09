from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.base import Base

class StockMovement(Base):
    __tablename__ = "stock_movements"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_movement_quantity_positive"),
        CheckConstraint(
            "movement_type IN ('opening_stock','purchase', 'sale', 'damage', 'adjustment_in', 'adjustment_out')",
            name="check_movement_type",
        ),
        CheckConstraint("unit_price IS NULL OR unit_price >= 0", name="ck_movement_unit_price"),
        CheckConstraint("unit_cost IS NULL OR unit_cost >= 0", name="ck_movement_unit_cost"),
        Index("ix_stock_movements_user_created", "user_id", "created_at"),
        Index("ix_stock_movements_inventory_id", "inventory_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    inventory_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inventory.id", ondelete="RESTRICT"), nullable=False
    )

    movement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    inventory = relationship("Inventory", back_populates="movements")
    user = relationship("User", back_populates="stock_movements")
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Integer, Numeric, Text, UniqueConstraint, text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.base import Base

class Inventory(Base):
    __tablename__ = "inventory"

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="unique_user_product"),
        CheckConstraint("current_stock >= 0", name="ck_inventory_stock_non_negative"),
        CheckConstraint("purchase_price >= 0", name="ck_inventory_purchase_price_non_negative"),
        CheckConstraint("selling_price >= 0", name="ck_inventory_selling_price_non_negative"),
        CheckConstraint("reorder_level >= 0", name="ck_inventory_reorder_level_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )

    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, server_default=text("0")
    )
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, server_default=text("5")
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner = relationship("User", back_populates="inventory_items")
    product = relationship("Product", back_populates="inventory_items")
    movements = relationship("StockMovement", back_populates="inventory")
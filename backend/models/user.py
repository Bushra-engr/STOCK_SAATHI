from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Text, primary_key=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    shop_name: Mapped[str] = mapped_column(String(150), nullable=False)
    shop_category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    inventory_items = relationship("Inventory", back_populates="owner")
    chat_messages = relationship("ChatMessage", back_populates="user")
    recommendations = relationship("Recommendation", back_populates="user")
    stock_movements = relationship("StockMovement", back_populates="user")

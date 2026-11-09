"""Read-only business intelligence tools for the shop owner."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from models.inventory import Inventory
from models.product import Product
from models.stock_movement import StockMovement
from services.inventory import get_low_stock_inventory

def _period_start(period: str | None) -> datetime:
    today = date.today()
    if period == "today":
        start = today
    elif period == "yesterday":
        start = today - timedelta(days=1)
    elif period == "this_week":
        start = today - timedelta(days=today.weekday())
    elif period == "last_month":
        first = today.replace(day=1)
        start = (first - timedelta(days=1)).replace(day=1)
    else:
        start = today.replace(day=1)
    return datetime.combine(start, time.min, tzinfo=timezone.utc)

def _sales_query(user_id: str, start: datetime):
    return (
        select(
            func.coalesce(func.sum(StockMovement.quantity), 0),
            func.coalesce(func.sum(StockMovement.quantity * func.coalesce(StockMovement.unit_price, 0)), 0),
            func.coalesce(
                func.sum(StockMovement.quantity * (func.coalesce(StockMovement.unit_price, 0) - func.coalesce(StockMovement.unit_cost, 0))),
                0,
            ),
        )
        .where(
            StockMovement.user_id == user_id,
            StockMovement.movement_type == "sale",
            StockMovement.created_at >= start,
        )
    )

def _purchase_query(user_id: str, start: datetime):
    return (
        select(
            func.coalesce(func.sum(StockMovement.quantity), 0),
            func.coalesce(
                func.sum(StockMovement.quantity * func.coalesce(StockMovement.unit_cost, StockMovement.unit_price, 0)),
                0,
            ),
        )
        .where(
            StockMovement.user_id == user_id,
            StockMovement.movement_type == "purchase",
            StockMovement.created_at >= start,
        )
    )

def run_bi_task(task: str, entities: dict, user_id: str, db: Session) -> dict:
    """Answer a read-only analytics task using database values."""
    period = entities.get("period") or "this_month"
    start = _period_start(period)

    if task in {"sales_summary", "profit_summary"}:
        quantity, revenue, gross_profit = db.execute(_sales_query(user_id, start)).one()
        return {
            "period": period,
            "quantity_sold": str(quantity),
            "sales_revenue": str(revenue),
            "estimated_gross_profit": str(gross_profit),
            "note": "Profit is estimated gross profit using the stored weighted-average purchase cost.",
        }

    if task == "purchase_summary":
        quantity, total_cost = db.execute(_purchase_query(user_id, start)).one()
        return {
            "period": period,
            "quantity_purchased": str(quantity),
            "purchase_cost": str(total_cost),
        }

    if task == "stock_valuation":
        stmt = select(
            func.coalesce(func.sum(Inventory.current_stock * Inventory.purchase_price), 0)
        ).where(Inventory.user_id == user_id)
        return {"stock_valuation_at_cost": str(db.scalar(stmt)), "as_of": date.today().isoformat()}

    if task == "low_stock":
        items = get_low_stock_inventory(user_id, db)
        return {
            "items": [
                {
                    "product": item.product.name,
                    "current_stock": str(item.current_stock),
                    "reorder_level": str(item.reorder_level),
                    "unit": item.product.unit,
                }
                for item in items
            ],
            "count": len(items),
        }

    sales = func.coalesce(func.sum(StockMovement.quantity), 0).label("units_sold")
    stmt = (
        select(Product.id, Product.name, Product.unit, sales)
        .join(Inventory, Inventory.product_id == Product.id)
        .outerjoin(
            StockMovement,
            (StockMovement.inventory_id == Inventory.id)
            & (StockMovement.user_id == user_id)
            & (StockMovement.movement_type == "sale")
            & (StockMovement.created_at >= start),
        )
        .where(Inventory.user_id == user_id)
        .group_by(Product.id, Product.name, Product.unit)
    )
    if entities.get("product_name"):
        stmt = stmt.where(Product.name.ilike(f"%{entities['product_name']}%"))

    if task == "top_selling":
        rows = db.execute(stmt.order_by(sales.desc()).limit(10)).all()
        return {
            "period": period,
            "items": [
                {"product": name, "units_sold": str(units), "unit": unit}
                for _, name, unit, units in rows
            ],
        }

    if task in {"slow_moving", "reorder_suggestions"}:
        rows = db.execute(stmt.order_by(sales.asc())).all()
        items = []
        for product_id, name, unit, units in rows:
            inventory = db.scalar(
                select(Inventory)
                .options(joinedload(Inventory.product))
                .where(Inventory.user_id == user_id, Inventory.product_id == product_id)
            )
            if task == "slow_moving":
                items.append({"product": name, "units_sold": str(units), "period": period})
            elif inventory and inventory.current_stock <= inventory.reorder_level:
                items.append(
                    {
                        "product": name,
                        "current_stock": str(inventory.current_stock),
                        "suggested_quantity": str(max(inventory.reorder_level * 2 - inventory.current_stock, Decimal("1"))),
                        "unit": unit,
                        "reason": "Current stock is at or below the configured reorder level.",
                    }
                )
        return {"period": period, "items": items[:10]}

    raise ValueError(f"Unsupported business intelligence task: {task}")

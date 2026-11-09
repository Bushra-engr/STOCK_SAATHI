from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from database.connection import get_db
from models.inventory import Inventory
from models.product import Product
from models.stock_movement import StockMovement
from services.get_auth_id import get_current_user_id

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/overview")
def dashboard_overview(
    days: int = 7,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """High-speed unified endpoint: returns summary, activity, top products, and movements in 1 DB session."""
    inventory = db.execute(
        select(
            func.count(Inventory.id),
            func.coalesce(func.sum(Inventory.current_stock), 0),
            func.coalesce(func.sum(Inventory.current_stock * Inventory.purchase_price), 0),
            func.coalesce(func.sum(Inventory.current_stock * Inventory.selling_price), 0),
            func.coalesce(func.sum((Inventory.current_stock <= Inventory.reorder_level).cast(Integer)), 0),
            func.coalesce(func.sum((Inventory.current_stock == 0).cast(Integer)), 0),
        ).where(Inventory.user_id == user_id)
    ).one()

    today_start = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
    today_sales = db.execute(
        select(
            func.coalesce(func.sum(StockMovement.quantity * StockMovement.unit_price), 0),
            func.coalesce(func.sum(StockMovement.quantity), 0),
        ).where(
            StockMovement.user_id == user_id,
            StockMovement.movement_type == "sale",
            StockMovement.created_at >= today_start,
        )
    ).one()

    summary_data = {
        "product_count": inventory[0],
        "stock_units": str(inventory[1]),
        "stock_value_at_cost": str(inventory[2]),
        "potential_retail_value": str(inventory[3]),
        "low_stock_count": inventory[4],
        "out_of_stock_count": inventory[5],
        "today_sales_revenue": str(today_sales[0]),
        "today_units_sold": str(today_sales[1]),
    }

    days = min(max(days, 1), 90)
    start = datetime.now(timezone.utc) - timedelta(days=days - 1)
    act_rows = db.execute(
        select(
            func.date(StockMovement.created_at).label("day"),
            StockMovement.movement_type,
            func.sum(StockMovement.quantity).label("quantity"),
            func.sum(StockMovement.quantity * func.coalesce(StockMovement.unit_price, StockMovement.unit_cost, 0)).label("amount"),
        )
        .where(StockMovement.user_id == user_id, StockMovement.created_at >= start)
        .group_by(func.date(StockMovement.created_at), StockMovement.movement_type)
        .order_by(func.date(StockMovement.created_at))
    ).all()
    activity_data = {
        "days": days,
        "items": [
            {
                "date": row.day.isoformat() if hasattr(row.day, "isoformat") else str(row.day),
                "type": row.movement_type,
                "quantity": str(row.quantity or 0),
                "amount": str(row.amount or 0),
            }
            for row in act_rows
        ],
    }

    top_rows = db.execute(
        select(Product.name, func.sum(StockMovement.quantity).label("units"))
        .join(Inventory, Inventory.product_id == Product.id)
        .join(StockMovement, StockMovement.inventory_id == Inventory.id)
        .where(
            Inventory.user_id == user_id,
            StockMovement.user_id == user_id,
            StockMovement.movement_type == "sale",
            StockMovement.created_at >= datetime.now(timezone.utc) - timedelta(days=30),
        )
        .group_by(Product.name)
        .order_by(func.sum(StockMovement.quantity).desc())
        .limit(8)
    ).all()
    top_data = {
        "period_days": 30,
        "items": [{"product": name, "units_sold": str(units)} for name, units in top_rows],
    }

    mov_rows = db.execute(
        select(StockMovement, Product.name, Product.unit)
        .join(Inventory, Inventory.id == StockMovement.inventory_id)
        .join(Product, Product.id == Inventory.product_id)
        .where(StockMovement.user_id == user_id, Inventory.user_id == user_id)
        .order_by(StockMovement.created_at.desc())
        .limit(100)
    ).all()
    movements_data = {
        "items": [
            {
                "id": m.id,
                "date": m.created_at.isoformat(),
                "product": name,
                "unit": unit,
                "type": m.movement_type,
                "quantity": str(m.quantity),
                "amount": str(m.quantity * (m.unit_price if m.unit_price is not None else (m.unit_cost or 0))),
            }
            for m, name, unit in mov_rows
        ]
    }

    return {
        "summary": summary_data,
        "activity": activity_data,
        "top_products": top_data,
        "movements": movements_data,
    }

@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    inventory = db.execute(
        select(
            func.count(Inventory.id),
            func.coalesce(func.sum(Inventory.current_stock), 0),
            func.coalesce(func.sum(Inventory.current_stock * Inventory.purchase_price), 0),
            func.coalesce(func.sum(Inventory.current_stock * Inventory.selling_price), 0),
            func.coalesce(func.sum((Inventory.current_stock <= Inventory.reorder_level).cast(Integer)), 0),
            func.coalesce(func.sum((Inventory.current_stock == 0).cast(Integer)), 0),
        ).where(Inventory.user_id == user_id)
    ).one()

    today_start = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
    today_sales = db.execute(
        select(
            func.coalesce(func.sum(StockMovement.quantity * StockMovement.unit_price), 0),
            func.coalesce(func.sum(StockMovement.quantity), 0),
        ).where(
            StockMovement.user_id == user_id,
            StockMovement.movement_type == "sale",
            StockMovement.created_at >= today_start,
        )
    ).one()
    return {
        "product_count": inventory[0],
        "stock_units": str(inventory[1]),
        "stock_value_at_cost": str(inventory[2]),
        "potential_retail_value": str(inventory[3]),
        "low_stock_count": inventory[4],
        "out_of_stock_count": inventory[5],
        "today_sales_revenue": str(today_sales[0]),
        "today_units_sold": str(today_sales[1]),
    }

@router.get("/activity")
def dashboard_activity(
    days: int = 7,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    days = min(max(days, 1), 90)
    start = datetime.now(timezone.utc) - timedelta(days=days - 1)
    rows = db.execute(
        select(
            func.date(StockMovement.created_at).label("day"),
            StockMovement.movement_type,
            func.sum(StockMovement.quantity).label("quantity"),
            func.sum(StockMovement.quantity * func.coalesce(StockMovement.unit_price, StockMovement.unit_cost, 0)).label("amount"),
        )
        .where(StockMovement.user_id == user_id, StockMovement.created_at >= start)
        .group_by(func.date(StockMovement.created_at), StockMovement.movement_type)
        .order_by(func.date(StockMovement.created_at))
    ).all()
    return {
        "days": days,
        "items": [
            {
                "date": row.day.isoformat() if hasattr(row.day, "isoformat") else str(row.day),
                "type": row.movement_type,
                "quantity": str(row.quantity or 0),
                "amount": str(row.amount or 0),
            }
            for row in rows
        ],
    }

@router.get("/top-products")
def dashboard_top_products(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    rows = db.execute(
        select(Product.name, func.sum(StockMovement.quantity).label("units"))
        .join(Inventory, Inventory.product_id == Product.id)
        .join(StockMovement, StockMovement.inventory_id == Inventory.id)
        .where(
            Inventory.user_id == user_id,
            StockMovement.user_id == user_id,
            StockMovement.movement_type == "sale",
            StockMovement.created_at >= datetime.now(timezone.utc) - timedelta(days=30),
        )
        .group_by(Product.name)
        .order_by(func.sum(StockMovement.quantity).desc())
        .limit(8)
    ).all()
    return {"period_days": 30, "items": [{"product": name, "units_sold": str(units)} for name, units in rows]}

@router.get("/movements")
def dashboard_movements(
    limit: int = 100,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    limit = min(max(limit, 1), 250)
    rows = db.execute(
        select(StockMovement, Product.name, Product.unit)
        .join(Inventory, Inventory.id == StockMovement.inventory_id)
        .join(Product, Product.id == Inventory.product_id)
        .where(StockMovement.user_id == user_id, Inventory.user_id == user_id)
        .order_by(StockMovement.created_at.desc())
        .limit(limit)
    ).all()
    return {
        "items": [
            {
                "id": movement.id,
                "date": movement.created_at.isoformat(),
                "product": name,
                "unit": unit,
                "type": movement.movement_type,
                "quantity": str(movement.quantity),
                "amount": str(movement.quantity * (movement.unit_price if movement.unit_price is not None else (movement.unit_cost or 0))),
            }
            for movement, name, unit in rows
        ]
    }

from decimal import Decimal

from models.inventory import Inventory
from models.stock_movement import StockMovement
from schemas.inventory import InventoryUpdate, InventoryCreate
from database.connection import get_db
from models.product import Product
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

"""
Inventory M/m :
- Add Opening Stock
- Record purchase
- Record sale
- Stock adjustment
- Record damage
- Record return
- View stock
"""

"""
Update purchase price     Change the cost price
Update selling price      Change the selling price
View product pricing      Retrieve current prices
View price history        Track previous price changes
"""

"""
create_inventory()
get_inventory()
update_inventory()
"""

def create_inventory(
    data: InventoryCreate,
    user_id: str,
    db: Session
):
    try:
        if data.current_stock < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Initial stock cannot be negative."
            )

        if data.purchase_price < 0 or data.selling_price < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prices cannot be negative."
            )

        if data.reorder_level < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reorder level cannot be negative."
            )

        product_stmt = select(Product).where(
            Product.id == data.product_id,
            Product.user_id == user_id,
        )

        product = db.scalar(product_stmt)

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found or access denied."
            )

        inventory_stmt = select(Inventory).where(
            Inventory.user_id == user_id,
            Inventory.product_id == data.product_id
        )

        existing_inventory = db.scalar(inventory_stmt)

        if existing_inventory is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventory for this product already exists."
            )

        new_stock = Inventory(
            user_id=user_id,
            product_id=data.product_id,
            current_stock=data.current_stock,
            purchase_price=data.purchase_price,
            selling_price=data.selling_price,
            reorder_level=data.reorder_level
        )

        db.add(new_stock)

        db.flush()

        if data.current_stock > 0:

            opening_movement = StockMovement(
                user_id=user_id,
                inventory_id=new_stock.id,
                movement_type="opening_stock",
                quantity=data.current_stock,
                unit_cost=data.purchase_price,
                notes="Initial opening stock"
            )

            db.add(opening_movement)

        db.commit()
        db.refresh(new_stock)
        return new_stock

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory already exists or database constraint failed."
        )

    except Exception:
        db.rollback()
        raise

def get_inventory(
    user_id: str,
    inventory_id: int,
    db: Session
):
    stmt = select(Inventory).where(
        Inventory.id == inventory_id,
        Inventory.user_id == user_id
    )

    item = db.scalar(stmt)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found."
        )

    return item

def update_inventory(
    data: InventoryUpdate,
    inventory_id: int,
    user_id: str,
    db: Session
):
    try:
        inventory_stmt = select(Inventory).where(
            Inventory.id == inventory_id,
            Inventory.user_id == user_id
        )

        existing_stock = db.scalar(inventory_stmt)

        if existing_stock is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory for this product does not exist."
            )

        update_data = data.model_dump(exclude_unset=True)

        allowed_fields = {
            "current_stock",
            "purchase_price",
            "selling_price",
            "reorder_level"
        }

        update_data = {
            key: value
            for key, value in update_data.items()
            if key in allowed_fields
        }

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid inventory fields provided for update."
            )

        for field, value in update_data.items():

            if value is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field} cannot be null."
                )

            if value < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field} cannot be negative."
                )

        if "current_stock" in update_data:
            new_stock = Decimal(str(update_data["current_stock"]))
            old_stock = existing_stock.current_stock
            diff = new_stock - old_stock
            if diff != Decimal("0"):
                movement = StockMovement(
                    user_id=user_id,
                    inventory_id=existing_stock.id,
                    movement_type="adjustment_in" if diff > 0 else "adjustment_out",
                    quantity=abs(diff),
                    unit_cost=existing_stock.purchase_price,
                    unit_price=existing_stock.selling_price,
                    notes="Manual stock update via dashboard"
                )
                db.add(movement)

        for field, value in update_data.items():
            setattr(existing_stock, field, value)

        db.commit()
        db.refresh(existing_stock)
        return existing_stock

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

def get_all_inventory(
    user_id: str,
    db: Session,
    limit: int = 50,
    offset: int = 0
):
    stmt = (
        select(Inventory)
        .options(joinedload(Inventory.product))
        .where(Inventory.user_id == user_id)
        .order_by(Inventory.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return db.execute(stmt).scalars().all()

def get_inventory_by_id(
    inventory_id: int,
    user_id: str,
    db: Session
):
    stmt = (
        select(Inventory)
        .options(joinedload(Inventory.product))
        .where(
            Inventory.id == inventory_id,
            Inventory.user_id == user_id
        )
    )

    inventory = db.execute(stmt).scalar_one_or_none()

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found."
        )

    return inventory

def get_low_stock_inventory(
    user_id: str,
    db: Session
):
    stmt = (
        select(Inventory)
        .options(joinedload(Inventory.product))
        .where(
            Inventory.user_id == user_id,
            Inventory.current_stock <= Inventory.reorder_level
        )
        .order_by(Inventory.current_stock.asc())
    )

    return db.execute(stmt).scalars().all()

def get_out_of_stock_products(
    user_id: str,
    db: Session
):
    stmt = (
        select(Inventory)
        .options(joinedload(Inventory.product))
        .where(
            Inventory.user_id == user_id,
            Inventory.current_stock == 0
        )
    )

    result = db.execute(stmt).unique().scalars().all()

    return [item.product for item in result]

def get_inventory_summary(
    user_id: str,
    db: Session
):
    stmt = select(
        func.count(Inventory.id).label("total_products"),
        func.coalesce(
            func.sum(Inventory.current_stock), 0
        ).label("total_stock_units"),
        func.sum(
            case(
                (Inventory.current_stock <= Inventory.reorder_level, 1),
                else_=0
            )
        ).label("low_stock_count"),
        func.sum(
            case(
                (Inventory.current_stock == 0, 1),
                else_=0
            )
        ).label("out_of_stock_count")
    ).where(Inventory.user_id == user_id)

    result = db.execute(stmt).one()

    return {
        "total_products": result.total_products,
        "total_stock_units": result.total_stock_units,
        "low_stock_count": result.low_stock_count or 0,
        "out_of_stock_count": result.out_of_stock_count or 0
    }


from decimal import Decimal
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.inventory import Inventory
from models.stock_movement import StockMovement
from schemas.stock_movement import StockMovementCreate

def _get_locked_inventory(
    db: Session,
    user_id: str,
    inventory_id: int
) -> Inventory:
    """
    Fetch inventory belonging to the authenticated user.
    Lock the row so concurrent stock operations cannot
    overwrite each other's changes.
    """

    stmt = (
        select(Inventory)
        .where(
            Inventory.id == inventory_id,
            Inventory.user_id == user_id
        )
        .with_for_update()
    )

    inventory = db.scalar(stmt)

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found."
        )

    return inventory

def _validate_quantity(quantity: Decimal) -> None:
    if quantity <= Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than zero."
        )

def _validate_price(price: Decimal | None, field_name: str) -> None:
    if price is not None and price < Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} cannot be negative."
        )

def _create_movement(
    db: Session,
    user_id: str,
    inventory_id: int,
    movement_type: str,
    quantity: Decimal,
    unit_price: Decimal | None = None,
    unit_cost: Decimal | None = None,
    notes: str | None = None
) -> StockMovement:

    movement = StockMovement(
        user_id=user_id,
        inventory_id=inventory_id,
        movement_type=movement_type,
        quantity=quantity,
        unit_price=unit_price,
        unit_cost=unit_cost,
        notes=notes
    )

    db.add(movement)
    return movement

def _commit_transaction(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

def record_purchase(
    data: StockMovementCreate,
    user_id: str,
    inventory_id: int,
    db: Session
):
    """
    Purchase increases stock.

    Updates weighted average purchase cost.
    """

    try:
        inventory = _get_locked_inventory(
            db, user_id, inventory_id
        )

        quantity = Decimal(str(data.quantity))
        _validate_quantity(quantity)

        purchase_cost = (
            Decimal(str(data.unit_cost))
            if data.unit_cost is not None
            else Decimal(str(data.unit_price))
            if data.unit_price is not None
            else None
        )

        if purchase_cost is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase cost is required."
            )

        _validate_price(purchase_cost, "Purchase cost")

        old_stock = inventory.current_stock
        old_cost = inventory.purchase_price

        new_stock = old_stock + quantity

        if new_stock > 0:
            new_average_cost = (
                (old_stock * old_cost) +
                (quantity * purchase_cost)
            ) / new_stock

            inventory.purchase_price = new_average_cost

        inventory.current_stock = new_stock

        movement = _create_movement(
            db=db,
            user_id=user_id,
            inventory_id=inventory_id,
            movement_type="purchase",
            quantity=quantity,
            unit_price=purchase_cost,
            unit_cost=purchase_cost,
            notes=data.notes
        )

        db.commit()
        db.refresh(inventory)
        db.refresh(movement)

        return {
            "message": "Purchase recorded successfully.",
            "quantity_added": quantity,
            "current_stock": inventory.current_stock,
            "average_purchase_price": inventory.purchase_price,
            "movement": movement
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

def record_sale(
    data: StockMovementCreate,
    user_id: str,
    inventory_id: int,
    db: Session
):
    """
    Sale decreases stock.
    Records selling price and cost at the current
    weighted average purchase cost.
    """

    try:
        inventory = _get_locked_inventory(
            db, user_id, inventory_id
        )

        quantity = Decimal(str(data.quantity))
        _validate_quantity(quantity)

        if quantity > inventory.current_stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient stock for this sale."
            )

        selling_price = (
            Decimal(str(data.unit_price))
            if data.unit_price is not None
            else inventory.selling_price
        )

        _validate_price(selling_price, "Selling price")

        cost_price = inventory.purchase_price

        inventory.current_stock -= quantity

        movement = _create_movement(
            db=db,
            user_id=user_id,
            inventory_id=inventory_id,
            movement_type="sale",
            quantity=quantity,
            unit_price=selling_price,
            unit_cost=cost_price,
            notes=data.notes
        )

        db.commit()
        db.refresh(inventory)
        db.refresh(movement)

        return {
            "message": "Sale recorded successfully.",
            "quantity_sold": quantity,
            "current_stock": inventory.current_stock,
            "sale_amount": quantity * selling_price,
            "estimated_cost": quantity * cost_price,
            "estimated_profit": quantity * (selling_price - cost_price),
            "movement": movement
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

def record_damage(
    data: StockMovementCreate,
    user_id: str,
    inventory_id: int,
    db: Session
):
    """
    Damaged goods decrease available stock.
    """

    try:
        inventory = _get_locked_inventory(
            db, user_id, inventory_id
        )

        quantity = Decimal(str(data.quantity))
        _validate_quantity(quantity)

        if quantity > inventory.current_stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Damage quantity cannot exceed available stock."
            )

        inventory.current_stock -= quantity

        movement = _create_movement(
            db=db,
            user_id=user_id,
            inventory_id=inventory_id,
            movement_type="damage",
            quantity=quantity,
            unit_cost=inventory.purchase_price,
            notes=data.notes
        )

        db.commit()
        db.refresh(inventory)
        db.refresh(movement)

        return {
            "message": "Damaged stock recorded successfully.",
            "damaged_quantity": quantity,
            "current_stock": inventory.current_stock,
            "estimated_loss": quantity * inventory.purchase_price,
            "movement": movement
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

def record_stock_adjustment(
    data: StockMovementCreate,
    user_id: str,
    inventory_id: int,
    db: Session,
    direction: Literal["in", "out"]
):
    """
    Corrects stock after a physical stock count.

    direction='in'  -> stock increases
    direction='out' -> stock decreases
    """

    try:
        inventory = _get_locked_inventory(
            db, user_id, inventory_id
        )

        quantity = Decimal(str(data.quantity))
        _validate_quantity(quantity)

        if direction == "in":
            inventory.current_stock += quantity
            movement_type = "adjustment_in"

        elif direction == "out":
            if quantity > inventory.current_stock:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Adjustment quantity cannot exceed available stock."
                )

            inventory.current_stock -= quantity
            movement_type = "adjustment_out"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Direction must be either 'in' or 'out'."
            )

        movement = _create_movement(
            db=db,
            user_id=user_id,
            inventory_id=inventory_id,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=inventory.purchase_price,
            notes=data.notes
        )

        db.commit()
        db.refresh(inventory)
        db.refresh(movement)

        return {
            "message": "Stock adjustment recorded successfully.",
            "adjustment_type": movement_type,
            "adjusted_quantity": quantity,
            "current_stock": inventory.current_stock,
            "movement": movement
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

def record_return(
    data: StockMovementCreate,
    user_id: str,
    inventory_id: int,
    db: Session,
    return_type: Literal["sales_return", "purchase_return"]
):
    """
    sales_return:
        Customer returns goods.
        Stock increases.

    purchase_return:
        Shop returns goods to supplier.
        Stock decreases.
    """

    try:
        inventory = _get_locked_inventory(
            db, user_id, inventory_id
        )

        quantity = Decimal(str(data.quantity))
        _validate_quantity(quantity)

        if return_type == "sales_return":
            inventory.current_stock += quantity
            movement_type = "sales_return"

        elif return_type == "purchase_return":
            if quantity > inventory.current_stock:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Purchase return quantity cannot exceed available stock."
                )

            inventory.current_stock -= quantity
            movement_type = "purchase_return"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid return type."
            )

        movement = _create_movement(
            db=db,
            user_id=user_id,
            inventory_id=inventory_id,
            movement_type=movement_type,
            quantity=quantity,
            unit_price=data.unit_price,
            unit_cost=inventory.purchase_price,
            notes=data.notes
        )

        db.commit()
        db.refresh(inventory)
        db.refresh(movement)

        return {
            "message": "Return recorded successfully.",
            "return_type": movement_type,
            "returned_quantity": quantity,
            "current_stock": inventory.current_stock,
            "movement": movement
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

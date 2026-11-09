from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.connection import get_db
from schemas.inventory import (
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse,
)
from schemas.product import ProductResponse
from schemas.stock_movement import StockMovementCreate

from services.inventory import (
    create_inventory,
    get_inventory,
    get_all_inventory,
    update_inventory,
    get_low_stock_inventory,
    get_out_of_stock_products,
    get_inventory_summary as inventory_summary_service,
)
from services.stock_operations import record_stock_adjustment

from services.get_auth_id import get_current_user_id

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)

class StockAdjustmentRequest(BaseModel):
    direction: Literal["in", "out"]
    quantity: Decimal = Field(..., gt=0)
    notes: str | None = None

@router.get("/", response_model=list[InventoryResponse])
def list_inventory(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    return get_all_inventory(
        user_id=current_user_id,
        db=db,
    )

@router.post("/", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_new_inventory(
    data: InventoryCreate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    return create_inventory(
        data=data,
        user_id=current_user_id,
        db=db,
    )

@router.get("/alerts/low-stock", response_model=list[InventoryResponse])
def low_stock_alerts(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    return get_low_stock_inventory(
        user_id=current_user_id,
        db=db,
    )

@router.get("/out_of_stock", response_model=list[ProductResponse])
def out_of_stock_products(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    return get_out_of_stock_products(
        user_id=current_user_id,
        db=db,
    )

@router.get("/summary")
def inventory_summary(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    return inventory_summary_service(
        user_id=current_user_id,
        db=db,
    )

@router.get("/{inventory_id}", response_model=InventoryResponse)
def inventory_details(
    inventory_id: int,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    return get_inventory(
        inventory_id=inventory_id,
        user_id=current_user_id,
        db=db,
    )

@router.put("/{inventory_id}", response_model=InventoryResponse)
@router.patch("/{inventory_id}", response_model=InventoryResponse)
def edit_inventory(
    inventory_id: int,
    data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    return update_inventory(
        inventory_id=inventory_id,
        data=data,
        user_id=current_user_id,
        db=db,
    )

@router.post("/{inventory_id}/adjust")
def adjust_inventory_stock(
    inventory_id: int,
    payload: StockAdjustmentRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    movement_data = StockMovementCreate(
        inventory_id=inventory_id,
        movement_type="adjustment_in" if payload.direction == "in" else "adjustment_out",
        quantity=payload.quantity,
        notes=payload.notes or "Manual stock adjustment",
    )
    return record_stock_adjustment(
        data=movement_data,
        user_id=current_user_id,
        inventory_id=inventory_id,
        db=db,
        direction=payload.direction,
    )

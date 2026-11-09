from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import List

from schemas.product import ProductCreate, ProductUpdate, ProductResponse
from services.get_auth_id import get_current_user_id
from services.products import (
    create_product,
    update_product,
    delete_product,
    get_product_by_id,
    get_all_products
)
from database.connection import get_db

router = APIRouter(
    prefix="/products", 
    tags=["products"]
)

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_new_product(
    data: ProductCreate,
    db: Session = Depends(get_db), 
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Creates a new product in the user's private catalog after duplicate verification.
    """
    return create_product(data=data, user_id=current_user_id, db=db)

@router.get("/{product_id}", response_model=ProductResponse, status_code=status.HTTP_200_OK)
def get_single_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Fetches a single product. Enforces ownership and visibility limits.
    """
    return get_product_by_id(product_id=product_id, user_id=current_user_id, db=db)

@router.put("/{product_id}", response_model=ProductResponse, status_code=status.HTTP_200_OK)
def update_existing_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Dynamically updates a product's fields after confirming ownership.
    """
    return update_product(product_id=product_id, data=data, user_id=current_user_id, db=db)

@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def delete_existing_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Removes a product completely from the user's catalog.
    """
    return delete_product(product_id=product_id, user_id=current_user_id, db=db)

@router.delete("/", status_code=status.HTTP_200_OK)
def delete_product_query(
    product_id: int | None = None,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Safe fallback for delete query without path param.
    """
    if not product_id:
        raise HTTPException(status_code=400, detail="product_id is required.")
    return delete_product(product_id=product_id, user_id=current_user_id, db=db)

@router.get("/", response_model=list[ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return get_all_products(
        user_id=user_id,
        db=db
    )

from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from fastapi import HTTPException, status
from models.product import Product
from models.inventory import Inventory
from models.stock_movement import StockMovement
from schemas.product import ProductCreate, ProductUpdate

def create_product(
    data: ProductCreate,
    user_id: str,
    db: Session
) -> Product:
    
    try:
        existing_product = db.execute(
            select(Product).where(
                Product.name == data.name,
                Product.brand == data.brand,
                Product.variant == data.variant,
                Product.user_id == user_id
            )
        ).scalar_one_or_none()
        
        if existing_product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{data.name}' with this brand/variant already exists in your catalog."
            )
            
        db_product = Product(
            name=data.name,
            brand=data.brand,
            category=data.category,
            variant=data.variant,
            unit=data.unit,
            user_id=user_id,
        )
        
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        return db_product
    
    except HTTPException:
        raise
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Product: {str(e)}"
        )
        
def get_product_by_id(
    product_id:int,
    user_id:str,
    db:Session
):
    result = db.execute(select(Product).where(Product.id==product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=F"Product with ID {product_id} not found"
        )

    if  product.user_id!=user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this product"
        )

    else:
        return product
    
def update_product(
    product_id: int, data: ProductUpdate, user_id: str, db: Session
):
    
    db_product = get_product_by_id(product_id, user_id, db)
    
    try:
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_product, key, value)
            
        db.commit()
        db.refresh(db_product)
        return db_product
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update product: {str(e)}"
        )

    
def delete_product(product_id: int, user_id: str, db: Session) -> dict:
    db_product = get_product_by_id(product_id, user_id, db)
    
    try:
        inv_stmt = select(Inventory).where(
            Inventory.product_id == product_id,
            Inventory.user_id == user_id,
        )
        inventories = db.scalars(inv_stmt).all()

        for inv in inventories:
            db.execute(
                delete(StockMovement).where(
                    StockMovement.inventory_id == inv.id,
                    StockMovement.user_id == user_id,
                )
            )
            db.delete(inv)
        
        db.flush()

        prod_name = db_product.name
        db.delete(db_product)
        db.commit()
        return {"success": True, "message": f"Product '{prod_name}' deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete product: {str(e)}"
        )
        

def get_all_products(user_id: str, db: Session):
    try:
        stmt = (
            select(Product)
            .where(
                    Product.user_id == user_id,
            )
            .order_by(Product.name.asc())
        )

        result = db.execute(stmt)
        products = result.scalars().all()

        return products

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch products"
        )

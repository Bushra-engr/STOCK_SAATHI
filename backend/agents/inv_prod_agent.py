"""Deterministic inventory specialist: resolves a plan to existing services."""

from decimal import Decimal
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from models.inventory import Inventory
from models.product import Product
from schemas.inventory import InventoryCreate
from schemas.product import ProductCreate
from schemas.stock_movement import StockMovementCreate
from services.inventory import create_inventory, get_inventory_summary
from services.products import create_product
from services.stock_operations import (
    record_damage,
    record_purchase,
    record_sale,
    record_stock_adjustment,
)

def find_product(user_id: str, entities: dict, db: Session) -> Product:
    name = (entities.get("product_name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Product name is required.")

    SYNONYMS = {
        "शैंपू": {"shampoo", "champo"},
        "शैम्पू": {"shampoo", "champo"},
        "shampoo": {"शैंपू", "शैम्पू"},
        "दूध": {"milk", "doodh"},
        "doodh": {"दूध", "milk"},
        "milk": {"दूध", "doodh"},
        "दही": {"dahi", "curd"},
        "dahi": {"दही", "curd"},
        "मक्खन": {"butter", "makhan"},
        "तेल": {"oil", "tel"},
        "oil": {"तेल", "tel"},
        "tel": {"तेल", "oil"},
        "साबुन": {"soap", "sabun"},
        "soap": {"साबुन", "sabun"},
        "sabun": {"साबुन", "soap"},
        "चावल": {"rice", "chawal"},
        "rice": {"चावल", "chawal"},
        "chawal": {"चावल", "rice"},
        "आटा": {"atta", "flour"},
        "atta": {"आटा", "flour"},
        "दाल": {"dal", "pulse"},
        "dal": {"दाल"},
        "चीनी": {"sugar", "chini"},
        "शक्कर": {"sugar", "shakkar"},
        "sugar": {"चीनी", "शक्कर"},
        "चाय": {"tea", "chai"},
        "tea": {"चाय", "chai"},
        "chai": {"चाय", "tea"},
        "बिस्कुट": {"biscuit", "biscuits"},
        "बिस्किट": {"biscuit", "biscuits"},
        "biscuit": {"बिस्कुट", "बिस्किट", "biscuits"},
        "biscuits": {"biscuit", "बिस्कुट", "बिस्किट"},
        "ब्रेड": {"bread"},
        "bread": {"ब्रेड"},
        "नमक": {"salt", "namak"},
        "salt": {"नमक", "namak"},
    }

    NOISE_WORDS = {"product", "प्रोडक्ट", "item", "saman", "सामान", "चीज़"}

    candidates = db.scalars(select(Product).where(Product.user_id == user_id)).all()
    if not candidates:
        raise HTTPException(status_code=404, detail=f"I couldn't find {name} in your products.")

    for p in candidates:
        if p.name.casefold() == name.casefold():
            return p

    search_query = " ".join(filter(None, [entities.get("brand"), name, entities.get("variant")]))
    raw_tokens = set(re.findall(r"[^\W_]+", search_query.casefold(), flags=re.UNICODE))
    query_tokens = {t for t in raw_tokens if t not in NOISE_WORDS} or raw_tokens

    matches = []
    for product in candidates:
        prod_full = " ".join(filter(None, [product.name, product.brand, product.variant])).casefold()
        prod_tokens = set(re.findall(r"[^\W_]+", prod_full, flags=re.UNICODE))

        token_match = True
        for qt in query_tokens:
            possible = {qt} | SYNONYMS.get(qt, set())
            found = any(p in prod_tokens or any(p in pt for pt in prod_tokens) for p in possible)
            if not found:
                token_match = False
                break

        if token_match:
            matches.append(product)

    if matches:
        exact = [p for p in matches if p.name.casefold() == name.casefold()]
        if exact:
            return exact[0]
        return matches[0]

    for product in candidates:
        prod_full = " ".join(filter(None, [product.name, product.brand, product.variant])).casefold()
        for qt in query_tokens:
            possible = {qt} | SYNONYMS.get(qt, set())
            if any(p in prod_full for p in possible):
                matches.append(product)
                break

    if matches:
        return matches[0]

    raise HTTPException(status_code=404, detail=f"I couldn't find {name} in your products.")

def _inventory_for_product(user_id: str, product_id: int, db: Session) -> Inventory:
    inventory = db.scalar(
        select(Inventory)
        .options(joinedload(Inventory.product))
        .where(Inventory.user_id == user_id, Inventory.product_id == product_id)
    )
    if inventory is None:
        raise HTTPException(status_code=404, detail="This product has no inventory record yet.")
    return inventory

def _result(inventory: Inventory) -> dict:
    prod_name = getattr(inventory.product, "name", None) if hasattr(inventory, "product") and inventory.product else None
    brand = getattr(inventory.product, "brand", None) if hasattr(inventory, "product") and inventory.product else None
    variant = getattr(inventory.product, "variant", None) if hasattr(inventory, "product") and inventory.product else None
    unit = getattr(inventory.product, "unit", "piece") if hasattr(inventory, "product") and inventory.product else "piece"
    return {
        "inventory_id": inventory.id,
        "product_id": inventory.product_id,
        "product_name": prod_name or "Product",
        "brand": brand,
        "variant": variant,
        "unit": unit,
        "current_stock": str(inventory.current_stock),
        "purchase_price": str(inventory.purchase_price),
        "selling_price": str(inventory.selling_price),
        "reorder_level": str(inventory.reorder_level),
    }

def execute_inventory_task(task: str, entities: dict, user_id: str, db: Session) -> dict:
    """Execute one already validated task. Caller must enforce confirmation first."""
    if task == "create_product":
        product = create_product(
            ProductCreate(
                name=entities["product_name"],
                brand=entities.get("brand"),
                variant=entities.get("variant"),
                category=entities.get("category"),
                unit=entities.get("unit") or "piece",
            ),
            user_id,
            db,
        )
        p_price = entities.get("purchase_price")
        p_val = Decimal(str(p_price)) if p_price is not None else Decimal("0")
        s_price = entities.get("selling_price")
        s_val = Decimal(str(s_price)) if s_price is not None else Decimal("0")
        qty = entities.get("quantity")
        qty_val = Decimal(str(qty)) if qty is not None else Decimal("0")

        try:
            inventory = create_inventory(
                InventoryCreate(
                    product_id=product.id,
                    current_stock=qty_val,
                    purchase_price=p_val,
                    selling_price=s_val,
                    reorder_level=entities.get("reorder_level") or Decimal("5"),
                ),
                user_id,
                db,
            )
        except Exception as inv_err:
            try:
                db.delete(product)
                db.commit()
            except Exception:
                db.rollback()
            raise inv_err

        res = _result(inventory)
        res["product_name"] = product.name
        res["brand"] = product.brand
        res["variant"] = product.variant
        res["unit"] = product.unit
        return res

    product = find_product(user_id, entities, db)
    if task == "inventory_lookup":
        return _result(_inventory_for_product(user_id, product.id, db))

    if task == "update_product":
        if entities.get("new_name"):
            product.name = entities["new_name"]
        if entities.get("brand"):
            product.brand = entities["brand"]
        if entities.get("variant"):
            product.variant = entities["variant"]
        if entities.get("category"):
            product.category = entities["category"]
        if entities.get("unit"):
            product.unit = entities["unit"]

        db.flush()

        inventory = db.scalar(
            select(Inventory).where(
                Inventory.user_id == user_id,
                Inventory.product_id == product.id,
            )
        )
        if inventory is not None:
            if entities.get("purchase_price") is not None:
                inventory.purchase_price = Decimal(str(entities["purchase_price"]))
            if entities.get("selling_price") is not None:
                inventory.selling_price = Decimal(str(entities["selling_price"]))
            if entities.get("reorder_level") is not None:
                inventory.reorder_level = Decimal(str(entities["reorder_level"]))
            db.commit()
            db.refresh(inventory)
            return _result(inventory)

        db.commit()
        db.refresh(product)
        return {
            "product_id": product.id,
            "product_name": product.name,
            "brand": product.brand,
            "variant": product.variant,
            "unit": product.unit,
            "message": f"{product.name} successfully update ho gaya.",
        }

    if task == "delete_product":
        from services.products import delete_product as service_delete_product
        service_delete_product(product_id=product.id, user_id=user_id, db=db)
        return {
            "product_id": product.id,
            "product_name": product.name,
            "message": f"{product.name} successfully delete ho gaya.",
        }

    if task == "opening_stock":
        existing = db.scalar(
            select(Inventory).where(
                Inventory.user_id == user_id,
                Inventory.product_id == product.id,
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="Opening stock is already set. Use a stock adjustment for the current physical count.",
            )
        inventory = create_inventory(
            InventoryCreate(
                product_id=product.id,
                current_stock=entities["quantity"],
                purchase_price=entities["purchase_price"],
                selling_price=entities["selling_price"],
                reorder_level=entities.get("reorder_level") or Decimal("5"),
            ),
            user_id,
            db,
        )
        return _result(inventory)

    if task == "record_purchase":
        inventory = db.scalar(
            select(Inventory).where(
                Inventory.user_id == user_id,
                Inventory.product_id == product.id,
            )
        )
        if inventory is None:
            if entities.get("selling_price") is None:
                raise HTTPException(
                    status_code=400,
                    detail="This product has no inventory yet. Please tell me its selling price per unit too.",
                )
            inventory = create_inventory(
                InventoryCreate(
                    product_id=product.id,
                    current_stock=Decimal("0"),
                    purchase_price=entities["purchase_price"],
                    selling_price=entities["selling_price"],
                ),
                user_id,
                db,
            )
    else:
        inventory = _inventory_for_product(user_id, product.id, db)
    quantity = entities.get("quantity")
    if task == "record_purchase":
        p_cost = entities.get("purchase_price")
        if p_cost is None and inventory and inventory.purchase_price is not None:
            p_cost = inventory.purchase_price
        payload = StockMovementCreate(
            inventory_id=inventory.id,
            movement_type="purchase",
            quantity=quantity,
            unit_cost=p_cost,
        )
        return record_purchase(payload, user_id, inventory.id, db)
    if task == "record_sale":
        payload = StockMovementCreate(
            inventory_id=inventory.id,
            movement_type="sale",
            quantity=quantity,
            unit_price=entities.get("selling_price"),
        )
        return record_sale(payload, user_id, inventory.id, db)
    if task == "record_damage":
        payload = StockMovementCreate(
            inventory_id=inventory.id,
            movement_type="damage",
            quantity=quantity,
        )
        return record_damage(payload, user_id, inventory.id, db)
    if task == "adjust_stock":
        count_val = entities.get("actual_count") if entities.get("actual_count") is not None else entities.get("quantity")
        if count_val is None:
            raise HTTPException(status_code=400, detail="Stock adjustment ke liye actual count zaroori hai.")
        actual_count = Decimal(str(count_val))
        difference = actual_count - inventory.current_stock
        if difference == 0:
            return {"message": "Stock already matches the physical count.", **_result(inventory)}
        direction = "in" if difference > 0 else "out"
        payload = StockMovementCreate(
            inventory_id=inventory.id,
            movement_type="adjustment_in" if direction == "in" else "adjustment_out",
            quantity=abs(difference),
        )
        record_stock_adjustment(payload, user_id, inventory.id, db, direction)
        db.refresh(inventory)
        return _result(inventory)

    raise HTTPException(status_code=400, detail=f"Unsupported inventory task: {task}")

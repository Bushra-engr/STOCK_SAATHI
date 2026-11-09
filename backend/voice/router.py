"""Voice-first request flow: Gnani STT -> Manager -> specialists -> Gnani TTS."""

import asyncio
import json
import os
import re
from decimal import Decimal
from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
from gnani.stt import GnaniSTTStreamClient, StreamErrorEvent, StreamTranscriptEvent
from gnani.tts import GnaniTTSClient
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from agents.business_intell_agent import run_bi_task
from agents.inv_prod_agent import execute_inventory_task, find_product
from agents.supervisor_agent import ManagerPlan, run_manager_agent
from database.connection import SessionLocal, get_db
from models.chat_message import ChatMessage
from services.get_auth_id import get_current_user_id
from models.inventory import Inventory
from models.user import User
from models.product import  Product
from services.get_auth_id import verify_access_token
from voice.session import voice_sessions

router = APIRouter(prefix="/voice", tags=["voice"])

YES = {
    "yes", "y", "haan", "haan kar do", "haan ji", "ha", "han", "ji",
    "हां", "हाँ", "जी", "confirm", "confirmed", "confirm karo", "kar do",
    "ok", "theek hai", "कर दो", "हाँ कर दो", "ठीक है", "save karo", "save",
}
NO = {
    "no", "n", "nahi", "nahi chahiye", "mat karo", "nahin",
    "नहीं", "ना", "cancel", "rehne do", "मत करो", "रहने दो",
}

def _is_confirmation(text: str, words: set[str]) -> bool:
    normalized = " ".join(text.lower().translate(str.maketrans("", "", ".,! ?।".replace(" ", ""))).split())
    return normalized in words

ACTIONABLE_TASKS = {
    "create_product", "update_product", "delete_product",
    "record_purchase", "record_sale", "record_damage",
    "adjust_stock", "opening_stock"
}

def _format_task_for_ui(task: dict) -> dict:
    e = task.get("entities", {})
    name = " ".join(filter(None, [e.get("brand"), e.get("product_name"), e.get("variant")])) or e.get("product_name") or "Product"
    qty = e.get("actual_count") if task.get("task") == "adjust_stock" else (e.get("quantity") if e.get("quantity") is not None else e.get("actual_count"))
    return {
        "task": task.get("task"),
        "product_name": name,
        "quantity": float(qty) if qty is not None else None,
        "unit": e.get("unit") or "piece",
        "purchase_price": float(e.get("purchase_price")) if e.get("purchase_price") is not None else None,
        "selling_price": float(e.get("selling_price")) if e.get("selling_price") is not None else None,
        "actual_count": float(e.get("actual_count")) if e.get("actual_count") is not None else (float(qty) if qty is not None else None),
    }

def _actionable_ui_tasks(tasks_list: list[dict]) -> list[dict]:
    res = []
    for t in tasks_list:
        task_name = t.get("task")
        if task_name in ACTIONABLE_TASKS:
            e = t.get("entities", {})
            p_name = e.get("product_name") or e.get("brand")
            if p_name and p_name.strip() and p_name.strip().lower() != "product":
                res.append(_format_task_for_ui(t))
    return res

def _is_new_command(text: str) -> bool:
    t = text.lower().strip()
    if not t:
        return False

    confirm_words = {
        "haan", "ha", "yes", "yep", "yeah", "ok", "okay", "theek", "theek hai",
        "confirm", "save", "save karo", "kar do", "kardo", "sahi hai", "हाँ", "हा", "हाँजी",
        "nahi", "na", "no", "nope", "cancel", "cancel karo", "mat karo", "ruk jao", "rehne do", "नहीं", "ना"
    }
    if t in confirm_words:
        return False

    if re.search(r'[\u0900-\u097F]', t):
        return True

    if len(t.split()) >= 3:
        return True

    keywords = [
        "sale", "sales", "sell", "sold", "bik", "bech", "kharid", "purchase", "buy", "bought",
        "stock", "maal", "saman", "item", "product", "add", "naya", "new", "delete", "remove",
        "hata", "nikal", "profit", "loss", "kamai", "munafa", "fayda", "kya", "kaise", "kitna",
        "kitni", "batao", "bataiye", "check", "dikhao", "summary", "list", "total", "today",
        "yesterday", "month", "week", "aaj", "kal", "hafta", "mahina"
    ]
    return any(w in t for w in keywords)

def _process_text(user_id: str, text: str, session) -> dict:
    """Synchronous agent/service work, run in a worker thread by the WS/HTTP route."""
    db: Session = SessionLocal()
    try:
        user_lang = getattr(session, "detected_language", None) or "hi-IN"
        if user_lang == "hi-IN":
            user_lang = _detect_text_language(text)

        user = db.get(User, user_id)
        if not user:
            return {
                "reply": "Pehle dashboard par shop profile complete kar lo, phir main voice se stock manage kar paunga.",
                "language": user_lang,
                "status": "needs_profile",
                "tasks": [],
                "pending_confirmation": False,
            }

        try:
            db.add(ChatMessage(user_id=user_id, role="user", message=text))
            db.commit()
        except Exception as msg_err:
            db.rollback()
            print(f"Error saving user message to DB: {msg_err}")

        if session.pending_actions:
            if _is_confirmation(text, YES):
                result_messages = []
                executed_tasks = []
                has_error = False
                for task in session.pending_actions:
                    try:
                        result = _execute(task, user_id, db)
                        result_messages.append(_summarize_result(task, result))
                        executed_tasks.append(_format_task_for_ui(task))
                    except Exception as exc:
                        db.rollback()
                        detail = getattr(exc, "detail", None) or str(exc)
                        result_messages.append(f"Ruk gaya: {detail}")
                        has_error = True
                        break
                session.pending_actions = []
                session.pending_plan = None
                voice_sessions.save_persisted_state()
                status_header = "Ho gaya! " if not has_error else "Koshish ki par: "
                reply = status_header + " ".join(result_messages)
                _save_assistant_message(db, user_id, reply)
                return {
                    "reply": reply,
                    "language": user_lang,
                    "status": "done",
                    "tasks": executed_tasks,
                    "pending_confirmation": False,
                }
            elif _is_confirmation(text, NO):
                session.pending_actions = []
                session.pending_plan = None
                voice_sessions.save_persisted_state()
                reply = "Theek hai, maine stock mein koi change nahi kiya."
                _save_assistant_message(db, user_id, reply)
                return {
                    "reply": reply,
                    "language": user_lang,
                    "status": "cancelled",
                    "tasks": [],
                    "pending_confirmation": False,
                }
            elif _is_new_command(text):
                session.pending_actions = []
                session.pending_plan = None
            else:
                reply = "Ek baar confirm karo."
                _save_assistant_message(db, user_id, reply)
                return {
                    "reply": reply,
                    "language": user_lang,
                    "status": "awaiting_confirmation",
                    "tasks": [_format_task_for_ui(t) for t in session.pending_actions],
                    "pending_confirmation": True,
                }

        t_low = text.lower()
        new_transaction_action = any(
            re.search(r'\b' + re.escape(w) + r'\b', t_low)
            for w in ["becha", "beche", "bik gaya", "bik gayi", "hata do", "hatao", "delete", "remove", "add karo", "add kro", "naya product", "new product"]
        )
        if new_transaction_action or (not session.pending_plan and _is_new_command(text)):
            session.pending_actions = []
            session.pending_plan = None
            context = ""
        else:
            context = json.dumps(session.pending_plan, ensure_ascii=False) if session.pending_plan else ""
        output = run_manager_agent(text, context=context)
        plan = ManagerPlan.model_validate(output["plan"])
        if plan and getattr(plan, "language", None):
            plan_lang_str = str(plan.language).lower()
            if "english" in plan_lang_str:
                user_lang = "en-IN"
            elif "marathi" in plan_lang_str:
                user_lang = "mr-IN"
            elif "gujarati" in plan_lang_str:
                user_lang = "gu-IN"
            elif "tamil" in plan_lang_str:
                user_lang = "ta-IN"
            elif "telugu" in plan_lang_str:
                user_lang = "te-IN"
            elif "bengali" in plan_lang_str:
                user_lang = "bn-IN"
            elif "kannada" in plan_lang_str:
                user_lang = "kn-IN"
            elif "punjabi" in plan_lang_str:
                user_lang = "pa-IN"
            elif "malayalam" in plan_lang_str:
                user_lang = "ml-IN"

        if not plan.tasks and getattr(plan, "direct_reply", None) and plan.direct_reply.strip():
            reply = plan.direct_reply.strip()
            session.pending_plan = None
            session.pending_actions = []
            _save_assistant_message(db, user_id, reply)
            return {
                "reply": reply,
                "language": user_lang,
                "status": "done",
                "tasks": [],
                "pending_confirmation": False,
            }

        if output["status"] == "unsupported":
            reply = output["reply_text"]
            _save_assistant_message(db, user_id, reply)
            return {
                "reply": reply,
                "language": user_lang,
                "status": "unsupported",
                "tasks": [],
                "pending_confirmation": False,
            }

        if output["status"] == "needs_clarification":
            session.pending_plan = output["plan"]
            reply = output["reply_text"]
            _save_assistant_message(db, user_id, reply)
            ui_tasks = _actionable_ui_tasks([t.model_dump(mode="json") for t in plan.tasks])
            return {
                "reply": reply,
                "language": user_lang,
                "status": "needs_clarification",
                "tasks": ui_tasks,
                "pending_confirmation": False,
            }

        tasks = [item.model_dump(mode="json") for item in plan.tasks]
        for route in output.get("routes", []):
            task_index = route.get("task_index")
            if isinstance(task_index, int) and task_index < len(tasks):
                tasks[task_index]["specialist"] = route.get("specialist")

        write_tasks = [
            task for task in tasks
            if task["task"] in {
                "record_purchase", "record_sale", "record_damage",
                "adjust_stock", "create_product", "update_product", "delete_product", "opening_stock"
            }
        ]

        if write_tasks:
            session.pending_plan = output["plan"]
            preflight_reply = _preflight_write_tasks(write_tasks, user_id, db, session)
            if preflight_reply:
                _save_assistant_message(db, user_id, preflight_reply)
                ui_tasks = _actionable_ui_tasks(write_tasks)
                return {
                    "reply": preflight_reply,
                    "language": user_lang,
                    "status": "needs_clarification",
                    "tasks": ui_tasks,
                    "pending_confirmation": False,
                }

            session.pending_actions = write_tasks
            session.pending_plan = output["plan"]
            voice_sessions.save_persisted_state()
            reply = _confirmation_summary(write_tasks)
            _save_assistant_message(db, user_id, reply)
            ui_tasks = _actionable_ui_tasks(write_tasks)
            return {
                "reply": reply,
                "language": user_lang,
                "status": "awaiting_confirmation",
                "tasks": ui_tasks,
                "pending_confirmation": True,
            }
        else:
            session.pending_plan = None
            replies = [_summarize_result(task, _execute(task, user_id, db)) for task in tasks]
            reply = " ".join(replies) if replies else "Aap stock ya business ke baare mein kya poochna chahte hain?"
            _save_assistant_message(db, user_id, reply)
            ui_tasks = _actionable_ui_tasks(tasks)
            return {
                "reply": reply,
                "language": user_lang,
                "status": "done",
                "tasks": ui_tasks,
                "pending_confirmation": False,
            }

    except Exception as exc:
        db.rollback()
        message = getattr(exc, "detail", None) or str(exc)
        reply = f"Is request ko complete nahi kar paya: {message}"
        return {
            "reply": reply,
            "language": user_lang,
            "status": "error",
            "tasks": [],
            "pending_confirmation": False,
        }
    finally:
        db.close()

def _save_assistant_message(db: Session, user_id: str, message: str) -> None:
    try:
        db.add(ChatMessage(user_id=user_id, role="assistant", message=message))
        db.commit()
    except Exception as msg_err:
        db.rollback()
        print(f"Error saving assistant message to DB: {msg_err}")

def _preflight_write_tasks(tasks: list[dict], user_id: str, db: Session, session) -> str | None:
    """Resolve existing products before asking for confirmation; never writes."""
    for task in tasks:
        entities = task["entities"]
        if task["task"] == "create_product":
            p_name = (entities.get("product_name") or "").strip()
            existing = db.execute(
                select(Product).where(
                    Product.user_id == user_id,
                    func.lower(Product.name) == p_name.lower(),
                )
            ).scalar_one_or_none()
            if existing:
                return f"'{existing.name}' pehle se aapke catalogue mein hai. Kya iska purchase record karna hai?"
            continue

        if task["task"] in {"update_product", "delete_product"}:
            try:
                find_product(user_id, entities, db)
            except HTTPException as exc:
                return f"Product dhoondhne mein issue aaya: {exc.detail}"
            continue

        if task["task"] == "record_sale":
            try:
                product = find_product(user_id, entities, db)
            except HTTPException:
                product_name = entities.get("product_name") or "Ye product"
                return f"'{product_name}' aapke catalogue mein nahi mila. Pehle ise add karein."

            inventory = db.scalar(
                select(Inventory).where(
                    Inventory.user_id == user_id,
                    Inventory.product_id == product.id,
                )
            )
            if inventory is None:
                return f"'{product.name}' ka inventory abhi set nahi hai. Pehle iska opening stock set kar lein."
            sale_qty = Decimal(str(entities.get("quantity") or 1))
            if inventory.current_stock < sale_qty:
                return f"'{product.name}' ka stock kam hai: sirf {inventory.current_stock} {product.unit} available hai, jabki aap {sale_qty} bechna chahte hain."
            continue

        try:
            product = find_product(user_id, entities, db)
        except HTTPException as exc:
            if exc.status_code == 404 and task["task"] in {"record_purchase", "opening_stock"}:
                task["task"] = "create_product"
                product_name = entities.get("product_name") or "Ye product"
                if entities.get("selling_price") is None:
                    entities["selling_price"] = entities.get("purchase_price") or Decimal("0")
                return None
            return f"Product dhoondhne mein issue aaya: {exc.detail}"
        except Exception as exc:
            return f"Product dhoondhne mein issue aaya: {getattr(exc, 'detail', exc)}"

        if getattr(product, "unit", None) and (not entities.get("unit") or entities.get("unit") == "piece"):
            entities["unit"] = product.unit

        inventory = db.scalar(
            select(Inventory).where(
                Inventory.user_id == user_id,
                Inventory.product_id == product.id,
            )
        )
        if task["task"] == "record_purchase":
            if entities.get("purchase_price") is None and inventory and inventory.purchase_price is not None:
                entities["purchase_price"] = str(inventory.purchase_price)
            if inventory is None and entities.get("selling_price") is None:
                entities["selling_price"] = entities.get("purchase_price") or Decimal("0")
        elif inventory is not None and task["task"] == "opening_stock":
            task["task"] = "adjust_stock"
            task["entities"]["actual_count"] = task["entities"].get("quantity")
            return (
                f"{product.name} ka inventory pehle se set hai. Current stock {task['entities']['actual_count']} "
                "adjust kar dein?"
            )
        elif inventory is None and task["task"] != "opening_stock":
            return f"{product.name} ka inventory abhi set nahi hai. Pehle iska opening stock set kar lein."
    return None

def _execute(task: dict, user_id: str, db: Session):
    specialist = task.get("specialist")
    if specialist == "inventory":
        return execute_inventory_task(task["task"], task["entities"], user_id, db)
    if specialist == "business_intelligence":
        return run_bi_task(task["task"], task["entities"], user_id, db)

    if task["task"] in {
        "record_purchase", "record_sale", "record_damage", "adjust_stock",
        "create_product", "update_product", "delete_product", "opening_stock", "inventory_lookup",
    }:
        return execute_inventory_task(task["task"], task["entities"], user_id, db)
    return run_bi_task(task["task"], task["entities"], user_id, db)

def _confirmation_summary(tasks: list[dict]) -> str:
    summaries = []
    for item in tasks:
        e = item["entities"]
        name = " ".join(filter(None, [e.get("brand"), e.get("product_name"), e.get("variant")])) or e.get("product_name") or "Product"
        quantity = e.get("quantity") or 1
        unit = e.get("unit") or "piece"
        if item["task"] == "record_purchase":
            p_price = e.get('purchase_price')
            p_str = f" ₹{p_price} per unit" if p_price is not None else ""
            summaries.append(f"{quantity} {unit} {name}{p_str} purchase")
        elif item["task"] == "record_sale":
            summaries.append(f"{quantity} {unit} {name} sale")
        elif item["task"] == "record_damage":
            summaries.append(f"{quantity} {unit} {name} damage")
        elif item["task"] == "adjust_stock":
            count = e.get('actual_count') if e.get('actual_count') is not None else e.get('quantity')
            summaries.append(f"{name} ka stock {count} {unit} set karna")
        elif item["task"] == "update_product":
            changes = []
            if e.get("selling_price") is not None:
                changes.append(f"selling price ₹{e.get('selling_price')}")
            if e.get("purchase_price") is not None:
                changes.append(f"purchase price ₹{e.get('purchase_price')}")
            if e.get("new_name"):
                changes.append(f"naam '{e.get('new_name')}'")
            if e.get("brand"):
                changes.append(f"brand '{e.get('brand')}'")
            if e.get("unit"):
                changes.append(f"unit '{e.get('unit')}'")
            if e.get("category"):
                changes.append(f"category '{e.get('category')}'")
            summary_str = ", ".join(changes) if changes else "details"
            summaries.append(f"{name} ka {summary_str} update karna")
        elif item["task"] == "delete_product":
            summaries.append(f"{name} ko delete karna")
        elif item["task"] == "opening_stock":
            summaries.append(
                f"{name} opening stock {quantity} {unit} (purchase ₹{e.get('purchase_price')}, selling ₹{e.get('selling_price')})"
            )
        else:
            p_price = f"₹{e.get('purchase_price')}" if e.get('purchase_price') is not None else "N/A"
            s_price = f"₹{e.get('selling_price')}" if e.get('selling_price') is not None else "N/A"
            qty_str = f"{e.get('quantity')} {unit} " if e.get('quantity') is not None else ""
            summaries.append(f"naya product {name} {qty_str}add karna (purchase {p_price}, selling {s_price})")
    return "; aur ".join(summaries) + ". Ek baar confirm karo."

PERIOD_LABELS = {
    "this_month": "Is mahine",
    "today": "Aaj",
    "this_week": "Is hafte",
    "yesterday": "Kal",
    "last_month": "Pichle mahine",
    "last_7_days": "Pichle 7 din",
    "last_30_days": "Pichle 30 din",
}

def _fmt_qty(val) -> str:
    """Format quantity: remove trailing zeros (25.000 -> 25, 1.5 -> 1.5)."""
    try:
        from decimal import Decimal as _D
        d = _D(str(val)).normalize()
        return str(d)
    except Exception:
        return str(val)

def _fmt_money(val) -> str:
    """Format money to 2 decimal places (1600.00000 -> 1600.00)."""
    try:
        return f"{float(val):,.2f}"
    except Exception:
        return str(val)

def _summarize_result(task: dict, result) -> str:
    if isinstance(result, dict):
        period_key = result.get('period', '')
        period_hindi = PERIOD_LABELS.get(period_key, period_key or 'Is dauraan')

        if task["task"] == "delete_product":
            return f"{result.get('product_name', 'Product')} ko successfully delete kar diya gaya hai."
        if task["task"] == "inventory_lookup":
            return f"{result.get('product_name', 'Product')} ka current stock {result.get('current_stock', 0)} {result.get('unit', '')} hai."
        if task["task"] == "sales_summary":
            qty = _fmt_qty(result.get('quantity_sold', 0))
            rev = _fmt_money(result.get('sales_revenue', 0))
            return f"{period_hindi} mein {qty} units biki, total sales ₹{rev} rahi."
        if task["task"] == "purchase_summary":
            qty = _fmt_qty(result.get('quantity_purchased', 0))
            cost = _fmt_money(result.get('purchase_cost', 0))
            return f"{period_hindi} mein {qty} units purchase kiye, total khareed ₹{cost} rahi."
        if task["task"] == "profit_summary":
            gp = _fmt_money(result.get('estimated_gross_profit', 0))
            return f"{period_hindi} ka estimated gross profit ₹{gp} hai."
        if task["task"] == "stock_valuation":
            sv = _fmt_money(result.get('stock_valuation_at_cost', 0))
            return f"Purchase cost ke hisaab se inventory ki value ₹{sv} hai."
        if "items" in result:
            items = result.get("items", [])
            if not items:
                return "Abhi is category mein koi product nahi mila."
            if task["task"] == "low_stock":
                details = [f"{item['product']}: {item['current_stock']} {item['unit']} bache hain" for item in items]
                return "Low stock items: " + "; ".join(details) + "."
            if task["task"] == "top_selling":
                details = [f"{item['product']}: {item['units_sold']} {item['unit']}" for item in items]
                return f"{result.get('period', 'Is period')} ke top sellers: " + "; ".join(details) + "."
            if task["task"] == "slow_moving":
                details = [f"{item['product']}: {item['units_sold']} units sold" for item in items]
                return "Slow-moving products: " + "; ".join(details) + "."
            if task["task"] == "reorder_suggestions":
                details = [f"{item['product']} ke {item['suggested_quantity']} {item['unit']} reorder karo" for item in items]
                return "Reorder suggestions: " + "; ".join(details) + "."
            return "Ye raha result: " + "; ".join(str(item) for item in items)
        if task["task"] == "record_purchase" and "current_stock" in result:
            return f"Purchase record ho gayi. Ab total stock {_fmt_qty(result['current_stock'])} hai."
        if task["task"] == "record_sale" and "current_stock" in result:
            return f"Sale record ho gayi. Ab total stock {_fmt_qty(result['current_stock'])} hai."
        if task["task"] == "opening_stock" and "current_stock" in result:
            return f"Opening stock set ho gaya. Ab total stock {_fmt_qty(result['current_stock'])} hai."
        if task["task"] == "create_product" and "product_name" in result:
            return f"{result['product_name']} product add ho gaya aur opening stock set ho gaya."
        if task["task"] == "record_damage" and "current_stock" in result:
            return f"Damage record ho gaya. Ab total stock {_fmt_qty(result['current_stock'])} hai."
        if task["task"] == "adjust_stock" and "current_stock" in result:
            return f"Stock adjust ho gaya. Ab total stock {_fmt_qty(result['current_stock'])} hai."
        if task["task"] == "update_product":
            return f"{result.get('product_name', 'Product')} successfully update ho gaya."
        return "Kaam ho gaya. " + str(result.get("message", ""))
    return "Kaam complete hua: " + str(result)

def _detect_text_language(text: str) -> str:
    """Heuristic script-based Indic language detection if STT code not present."""
    if not text:
        return "hi-IN"
    if re.search(r'[஀-௿]', text):
        return "ta-IN"
    if re.search(r'[ఀ-౿]', text):
        return "te-IN"
    if re.search(r'[ಀ-೿]', text):
        return "kn-IN"
    if re.search(r'[ഀ-ൿ]', text):
        return "ml-IN"
    if re.search(r'[઀-૿]', text):
        return "gu-IN"
    if re.search(r'[ঀ-৿]', text):
        return "bn-IN"
    if re.search(r'[਀-੿]', text):
        return "pa-IN"
    if re.search(r'[ऀ-ॿ]', text):
        if any(w in text.lower() for w in ["ahe", "aahe", "ahet", "zala", "kiti", "vikri", "vikla"]):
            return "mr-IN"
        return "hi-IN"
    t_low = text.lower()
    hindi_roman = ["batao", "bataiye", "biki", "bika", "becha", "beche", "kharida", "kharide", "khareeda", "aaj", "kal", "karo", "kardo", "hatao", "kamai", "munafa", "fayda", "hai", "hain", "kya", "kitna", "kitni"]
    if any(re.search(r'\b' + re.escape(w) + r'\b', t_low) for w in hindi_roman):
        return "hi-IN"
    return "en-IN"

def _resolve_tts_lang_and_voice(lang_code: str) -> tuple[str, str]:
    """Map detected language to Gnani TTS timbre-v2.5 language code and natural voice."""
    code = (lang_code or "hi-IN").strip().lower()
    mapping = {
        "hi-in": ("hi-IN", "Pranav"),
        "hi": ("hi-IN", "Pranav"),
        "hindi": ("hi-IN", "Pranav"),
        "hinglish": ("hi-IN", "Pranav"),
        "en-in": ("en-IN", "Pranav"),
        "en": ("en-IN", "Pranav"),
        "english": ("en-IN", "Pranav"),
        "mr-in": ("mr-IN", "Pranav"),
        "mr": ("mr-IN", "Pranav"),
        "marathi": ("mr-IN", "Pranav"),
        "gu-in": ("gu-IN", "Pranav"),
        "gu": ("gu-IN", "Pranav"),
        "gujarati": ("gu-IN", "Pranav"),
        "ta-in": ("ta-IN", "Kavin"),
        "ta": ("ta-IN", "Kavin"),
        "tamil": ("ta-IN", "Kavin"),
        "te-in": ("te-IN", "Pranav"),
        "te": ("te-IN", "Pranav"),
        "telugu": ("te-IN", "Pranav"),
        "kn-in": ("kn-IN", "Pranav"),
        "kn": ("kn-IN", "Pranav"),
        "kannada": ("kn-IN", "Pranav"),
        "bn-in": ("bn-IN", "Pranav"),
        "bn": ("bn-IN", "Pranav"),
        "bengali": ("bn-IN", "Pranav"),
        "pa-in": ("pa-IN", "Pranav"),
        "pa": ("pa-IN", "Pranav"),
        "punjabi": ("pa-IN", "Pranav"),
        "ml-in": ("ml-IN", "Pranav"),
        "ml": ("ml-IN", "Pranav"),
        "malayalam": ("ml-IN", "Pranav"),
    }
    return mapping.get(code, ("hi-IN", "Pranav"))

def _language_code(language: str) -> str:
    lang, _ = _resolve_tts_lang_and_voice(language)
    return lang

async def _speak(websocket: WebSocket, text: str, language: str) -> None:
    api_key = os.getenv("GNANI_API_KEY")
    if not text.strip() or not api_key:
        try:
            await websocket.send_json({"event": "assistant_audio_failed"})
        except Exception:
            pass
        return
    tts_lang, tts_voice = _resolve_tts_lang_and_voice(language)
    try:
        client = GnaniTTSClient(api_key=api_key)
        audio = await asyncio.wait_for(
            asyncio.to_thread(
                client.synthesize,
                text,
                model="timbre-v2.5",
                voice=tts_voice,
                language=tts_lang,
            ),
            timeout=2.0,
        )
        await websocket.send_json({"event": "assistant_audio", "mime_type": "audio/wav"})
        await websocket.send_bytes(audio)
    except Exception as exc:
        print(f"Gnani TTS note: {exc}")
        try:
            await websocket.send_json({"event": "assistant_audio_failed"})
        except Exception:
            pass

class VoiceProcessRequest(BaseModel):
    text: str

@router.get("/messages")
def get_chat_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Retrieve chat history for the authenticated shop owner."""
    limit = min(max(limit, 1), 200)
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    ).all()
    rows = list(reversed(rows))
    return {
        "items": [
            {
                "id": m.id,
                "role": m.role,
                "message": m.message,
                "created_at": m.created_at.isoformat() if hasattr(m.created_at, "isoformat") else str(m.created_at),
            }
            for m in rows
        ]
    }

@router.post("/process")
@router.post("/process/")
@router.post("/text-command")
@router.post("/text-command/")
def process_voice_http(
    req: VoiceProcessRequest,
    authorization: str = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ")[1]
    user_id = verify_access_token(token)
    session = voice_sessions.get_or_create_for_user(user_id)
    result = _process_text(user_id, req.text, session)

    audio_b64 = None
    api_key = os.getenv("GNANI_API_KEY")
    reply_text = result.get("reply", "")
    reply_lang = result.get("language", "hi-IN")
    if api_key and reply_text and len(reply_text.strip()) > 0:
        tts_lang, tts_voice = _resolve_tts_lang_and_voice(reply_lang)
        try:
            client = GnaniTTSClient(api_key=api_key)
            audio_bytes = client.synthesize(
                reply_text,
                model="timbre-v2.5",
                voice=tts_voice,
                language=tts_lang,
            )
            import base64
            audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        except Exception as tts_err:
            print(f"Gnani TTS synthesis note: {tts_err}")

    result["audio"] = audio_b64
    return result

@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    session = None
    stt_task = None
    try:
        auth_message = await websocket.receive_json()
        if auth_message.get("event") != "auth" or not auth_message.get("token"):
            await websocket.close(code=4401, reason="Authentication required")
            return
        try:
            user_id = verify_access_token(auth_message["token"])
        except Exception:
            await websocket.close(code=4401, reason="Invalid authentication token")
            return

        session = voice_sessions.get_or_create_for_user(user_id)
        await websocket.send_json({"event": "connected", "session_id": session.session_id})

        while True:
            control = await websocket.receive()
            if control.get("text") is not None:
                data = json.loads(control["text"])
                event = data.get("event")
                if event == "start_turn":
                    if stt_task and not stt_task.done():
                        stt_task.cancel()
                        try:
                            await stt_task
                        except (asyncio.CancelledError, Exception):
                            pass
                        stt_task = None
                    session.is_active = True
                    session.audio_queue = asyncio.Queue(maxsize=100)
                    stt_task = asyncio.create_task(_receive_and_transcribe(websocket, session))
                elif event == "end_turn":
                    session.is_active = False
                    client_transcript = (data.get("client_transcript") or "").strip()
                    if stt_task:
                        try:
                            await session.audio_queue.put(None)
                            transcript = await asyncio.wait_for(stt_task, timeout=8.0)
                        except (asyncio.TimeoutError, asyncio.CancelledError):
                            transcript = ""
                        except Exception as stt_err:
                            print(f"STT await error: {stt_err}")
                            transcript = ""
                        finally:
                            stt_task = None
                        final_text = transcript.strip() or client_transcript
                        if final_text:
                            await websocket.send_json({"event": "transcript", "text": final_text})
                            result = await asyncio.to_thread(_process_text, user_id, final_text, session)
                            await websocket.send_json({
                                "event": "assistant_text",
                                "text": result["reply"],
                                "status": result["status"],
                                "tasks": result["tasks"],
                                "pending_confirmation": result["pending_confirmation"],
                            })
                            await _speak(websocket, result["reply"], result["language"])
                        else:
                            reply = "Awaaz clear nahi aayi. Ek baar phir bolenge?"
                            await websocket.send_json({
                                "event": "assistant_text",
                                "text": reply,
                                "status": "needs_clarification",
                                "tasks": [],
                                "pending_confirmation": False,
                            })
                            await _speak(websocket, reply, "hi-IN")
                elif event == "text":
                    input_text = str(data.get("text", "")).strip()
                    if input_text:
                        result = await asyncio.to_thread(_process_text, user_id, input_text, session)
                        await websocket.send_json({
                            "event": "assistant_text",
                            "text": result["reply"],
                            "status": result["status"],
                            "tasks": result["tasks"],
                            "pending_confirmation": result["pending_confirmation"],
                        })
                        await _speak(websocket, result["reply"], result["language"])
                elif event == "stop":
                    break
            elif control.get("bytes") is not None and session.is_active:
                if stt_task and not stt_task.done():
                    try:
                        session.audio_queue.put_nowait(control["bytes"])
                    except asyncio.QueueFull:
                        try:
                            session.audio_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                        try:
                            session.audio_queue.put_nowait(control["bytes"])
                        except asyncio.QueueFull:
                            pass

    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"event": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        if session:
            session.is_active = False
        if stt_task and not stt_task.done():
            stt_task.cancel()
            try:
                await stt_task
            except (asyncio.CancelledError, Exception):
                pass
        if session:
            voice_sessions.remove_session(session.session_id)

async def _receive_and_transcribe(websocket: WebSocket, session) -> str:
    api_key = os.getenv("GNANI_API_KEY")
    if not api_key:
        try:
            await websocket.send_json({"event": "error", "message": "GNANI_API_KEY check karo."})
        except Exception:
            pass
        return ""

    transcripts: list[str] = []
    event_task = None
    try:
        async with GnaniSTTStreamClient(
            api_key=api_key,
            language_code="indic-auto",
            model="prisma-v3.0",
            language_candidates=["hi-IN", "en-IN", "mr-IN", "gu-IN"],
            format="codemix",
            keywords=[
                "StockSaathi", "Amul", "milk", "packet", "packets", "purchase", "purchased",
                "sell", "sold", "stock", "inventory", "shampoo", "bread", "दूध", "पैकेट", "खरीदा", "बेचा",
            ],
            sample_rate=16000,
        ) as stream:
            async def collect_events():
                try:
                    async for event in stream.events():
                        if isinstance(event, StreamTranscriptEvent) and event.text.strip():
                            transcripts.append(event.text.strip())
                            if event.detected_language_code:
                                session.detected_language = event.detected_language_code
                            try:
                                await websocket.send_json({
                                    "event": "transcript_segment",
                                    "text": event.text,
                                    "detected_language": event.detected_language_code,
                                })
                            except Exception:
                                break
                        elif isinstance(event, StreamErrorEvent):
                            try:
                                await websocket.send_json({"event": "error", "message": event.message})
                            except Exception:
                                break
                except (asyncio.CancelledError, Exception):
                    pass

            event_task = asyncio.create_task(collect_events())
            buffer = bytearray()
            while True:
                chunk = await session.audio_queue.get()
                if chunk is None:
                    break
                buffer.extend(chunk)
                while len(buffer) >= 1024:
                    await stream.send_audio(bytes(buffer[:1024]))
                    del buffer[:1024]

            if buffer:
                buffer.extend(b"\x00" * (1024 - len(buffer)))
                await stream.send_audio(bytes(buffer))
            await stream.close()
            if event_task:
                try:
                    await asyncio.wait_for(asyncio.shield(event_task), timeout=1.5)
                except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                    pass
            return " ".join(transcripts)
    except (asyncio.CancelledError, Exception) as e:
        if not isinstance(e, asyncio.CancelledError):
            print(f"STT streaming note: {e}")
        return " ".join(transcripts)
    finally:
        if event_task and not event_task.done():
            event_task.cancel()
            try:
                await event_task
            except (asyncio.CancelledError, Exception):
                pass


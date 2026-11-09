"""LangGraph manager for understanding and routing StockSaathi requests.

This graph creates a validated task plan and clarification questions.
It does not execute database writes directly.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import TypedDict

from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, model_validator

from agents.llm_provider import llm
from agents.state import Entities, TaskName, find_missing_fields

class ManagerTask(BaseModel):
    """One product operation or one business question, with its own entities."""

    task: str = Field(
        default="record_purchase",
        description="The specific operation: create_product, record_purchase, record_sale, adjust_stock, opening_stock, inventory_lookup, sales_summary, profit_summary, low_stock, top_selling, etc.",
    )
    entities: Entities = Field(
        default_factory=Entities,
        description="Extracted entities for this product or operation",
    )

    @model_validator(mode="before")
    @classmethod
    def map_flat_to_entities(cls, data):
        if not isinstance(data, dict):
            return data
        raw_task = str(data.get("task") or data.get("action") or "").strip().lower()
        if raw_task in {"delete", "delete_product", "remove", "remove_product", "delete_item", "hatao", "hata_do", "hata do"}:
            task_name = "delete_product"
        elif raw_task in {"create", "create_product", "add", "add_product", "new_product", "naya_product"}:
            task_name = "create_product"
        elif raw_task in {"update", "update_product", "edit", "edit_product", "change_product", "modify"}:
            task_name = "update_product"
        elif raw_task in {"purchase", "record_purchase", "buy", "bought", "khareeda", "kharida"}:
            task_name = "record_purchase"
        elif raw_task in {"sale", "record_sale", "sell", "sold", "becha", "bik_gaya"}:
            task_name = "record_sale"
        elif raw_task in {"damage", "record_damage", "kharab", "toot_gaya"}:
            task_name = "record_damage"
        elif raw_task in {"adjust", "adjust_stock", "adjustment"}:
            task_name = "adjust_stock"
        else:
            task_name = raw_task or "record_purchase"
        entities_data = data.get("entities")
        if isinstance(entities_data, Entities):
            entities_data = entities_data.model_dump()
        elif not isinstance(entities_data, dict):
            entities_data = {
                k: v for k, v in data.items()
                if k not in ("task", "action", "specialist")
            }
        return {"task": task_name, "entities": entities_data}

class ManagerPlan(BaseModel):
    """Structured result returned by the manager's language-model step."""

    language: str = Field(
        default="Hinglish",
        description="Language used by the shop owner, e.g. Hinglish, Hindi, English",
    )
    tasks: list[ManagerTask] = Field(
        default_factory=list,
        description="Ordered list of tasks. When the user mentions MULTIPLE products or actions in one utterance, create a SEPARATE task for each product in this list.",
    )
    unsupported_request: bool = Field(
        default=False,
        description="Set to true only if the user request is completely unrelated to inventory or shop analytics",
    )
    unsupported_reason: str | None = Field(
        default=None,
        description="Polite Hinglish explanation if request is unsupported",
    )
    clarification_question: str | None = Field(
        default=None,
        description="Polite, conversational Hinglish question asking for missing required info (e.g. price, quantity)",
    )
    direct_reply: str | None = Field(
        default=None,
        description="Direct conversational answer, business advice, retail guidance, tips, explanations, or greeting in natural, supportive Hinglish when the user asks questions like 'sales kaise badhaun', 'kya krun jisse profit bade', 'loss ho raha hai', business guidance, greetings, etc. When direct_reply is provided, leave tasks empty.",
    )

class ManagerGraphState(TypedDict, total=False):
    raw_input: str
    context: str
    plan: dict
    missing_by_task: list[dict]
    routes: list[dict]
    status: str
    reply_text: str
    spoken_text: str

MANAGER_SYSTEM_PROMPT = """You are StockSaathi's AI Supervisor and Business Advisor for Indian retail shop owners.

Your role is to understand the shop owner's spoken or typed requests in real time (Hindi, English, or Hinglish) and return a structured JSON conforming to the ManagerPlan schema.

BUSINESS ADVISORY & CONSULTATIVE CONVERSATION (VERY IMPORTANT):
- When a shop owner asks strategic questions, business advice, tips, or shares concerns:
  - "sales nhi badh rhi h loss ho rha h" (Sales not growing, facing loss)
  - "kya krun jisse profit bade" (What should I do to increase profit)
  - "dukan me bikri kaise badhaun"
  - "loss kam karne ke liye kya karun"
  - "kuch suggestion do"
  - Greetings like "namaste", "kaise ho", "hello"
  CRITICAL: DO NOT map these consultative questions to database summary tasks like `profit_summary` or `sales_summary`!
  Instead, leave `tasks` empty (`[]`) and provide practical, encouraging, retail business guidance directly in `direct_reply` in natural Hindi/Hinglish.
  Provide 2-3 practical, actionable tips (e.g., fast-moving items ka stock hamesha maintain rakhein, slow-moving dead stock par discount ya combo offer dekar cash unlock karein, low-stock items track karein, aur customer demand ke according items rakhein).

MULTI-PRODUCT HANDLING (CRUCIAL):
- Shop owners frequently speak multiple items in a single sentence:
  - "Amul add kro product aur shampoo purchase kiya 100 rs" -> Two separate tasks:
    Task 1: {"task": "create_product", "entities": {"product_name": "Amul"}}
    Task 2: {"task": "record_purchase", "entities": {"product_name": "shampoo", "purchase_price": 100, "quantity": 1}}
  - "5 packet bread becha aur 2 packet amul butter purchase kiya 50 rs ka" -> Two separate tasks:
    Task 1: {"task": "record_sale", "entities": {"product_name": "bread", "quantity": 5}}
    Task 2: {"task": "record_purchase", "entities": {"product_name": "amul butter", "quantity": 2, "purchase_price": 50}}
- When multiple products are mentioned (separated by 'aur', 'and', 'ya', commas, or pauses), ALWAYS create one distinct task for EACH product in the `tasks` array. Never drop an item!

INTENT MAPPINGS:
- "add product / naya product add karo" -> create_product
- "update product / edit product / badal do / change karo / update karo / selling price update karo / price badlo / edit" -> update_product
- "delete product / remove karo / product hata do / delete kar do / product delete karo / product nikal do / delete / hata do / hatao / शैंपू हटा दो" -> delete_product

HINDI / DEVANAGARI & NOUN CLEANUP RULES (CRITICAL):
1. When user speaks in Hindi/Devanagari like "शैंपू प्रोडक्ट हटा दो", "शैम्पू डिलीट करो", "साबुन हटा दो", "अमुल दूध डिलीट करो":
   - The task is `delete_product`.
   - The product_name is the actual item (e.g. "shampoo" or "शैंपू").
   - Words like "प्रोडक्ट", "product", "item", "सामान", "चीज़" are category nouns and MUST NOT be extracted as product_name!
   - NEVER output product_name as "Product", "प्रोडक्ट", or "item"!
   - If user says "शैंपू प्रोडक्ट हटा दो", extract product_name as "shampoo".
- "purchase kiya / kharida / khareeda / purchased / stock aaya / maal aaya" -> record_purchase
- "becha / bik gaya / sale kiya / sold" -> record_sale
- "kharab ho gaya / toot gaya / damage / expired" -> record_damage
- "stock adjust karo / actual count itna hai" -> adjust_stock (use actual_count)
- "opening stock set karo / pehla stock" -> opening_stock
- "kitna stock hai / check stock / stock batao" -> inventory_lookup
- "kitna bik gaya / sales kitni hui / aaj ki kamai" -> sales_summary
- "munafa kitna hua / profit" -> profit_summary
- "low stock / kya khatam hone wala hai" -> low_stock
- "top selling / sabse zyada kya bika" -> top_selling

ENTITY EXTRACTION RULES:
1. `product_name`: ALWAYS populate with the item name (e.g. "Amul", "Dove shampoo", "Bread"). Never leave empty if an item is spoken.
2. `quantity`: Number of units (packets, bottles, pieces). If a user says a singular item like "shampoo purchased 100 rs" or "doodh becha 25 rs" without specifying a count, default quantity to 1.
3. `purchase_price`: Cost price per unit in rupees.
4. `selling_price`: Customer price per unit in rupees.
5. If creating a new product requires purchase and selling prices, or if an item is missing required details, provide a friendly, conversational Hinglish question in `clarification_question`.
   Example: "Amul product ka purchase price aur selling price kitna rakhna hai?"
"""

@tool
def validate_task_fields(task_name: str, entities_json: str) -> str:
    """Deterministically return required entity fields missing from one task."""
    entities = Entities.model_validate_json(entities_json)
    missing = find_missing_fields(task_name, entities)
    return ",".join(missing)

INVENTORY_TASKS = {
    "record_purchase",
    "record_sale",
    "record_damage",
    "adjust_stock",
    "create_product",
    "update_product",
    "delete_product",
    "opening_stock",
    "inventory_lookup",
}

@tool
def route_task_to_specialist(task_name: str) -> str:
    """Return the specialist that owns a supported task; this does not execute it."""
    if task_name in INVENTORY_TASKS:
        return "inventory"
    return "business_intelligence"

NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
    "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
    "eighty": "80", "ninety": "90", "hundred": "100",
    "ek": "1", "do": "2", "teen": "3", "chaar": "4", "char": "4",
    "paanch": "5", "panch": "5", "chhah": "6", "chhe": "6", "saat": "7",
    "aath": "8", "nau": "9", "das": "10", "gyarah": "11", "barah": "12",
    "terah": "13", "chaudah": "14", "pandrah": "15", "solah": "16",
    "satrah": "17", "atharah": "18", "unnis": "19", "bees": "20",
    "pachees": "25", "tees": "30", "chalis": "40", "pachas": "50",
    "saath": "60", "sattar": "70", "assi": "80", "nabbe": "90", "sau": "100",
    "एक": "1", "दो": "2", "तीन": "3", "चार": "4", "पांच": "5", "पाँच": "5",
    "छह": "6", "सात": "7", "आठ": "8", "नौ": "9", "दस": "10",
    "पंद्रह": "15", "बीस": "20", "पच्चीस": "25", "तीस": "30", "चालीस": "40",
    "पचास": "50", "साठ": "60", "सत्तर": "70", "अस्सी": "80", "नब्बे": "90", "सौ": "100"
}

def normalize_number_words(text: str) -> str:
    if not text:
        return text
    tokens = text.split()
    normalized_tokens = []
    for tok in tokens:
        clean_tok = tok.strip(".,!?:;।\"'()[]{}").lower()
        if clean_tok in NUMBER_WORDS:
            num = NUMBER_WORDS[clean_tok]
            normalized_tokens.append(re.sub(re.escape(clean_tok), num, tok, flags=re.IGNORECASE))
        else:
            normalized_tokens.append(tok)
    return " ".join(normalized_tokens)

def extract_transaction_fallback(raw_text: str) -> ManagerTask | None:
    text = (raw_text or "").strip().lower()
    if not text:
        return None

    sale_kw = ["beche", "becha", "becho", "bika", "bik gaya", "bik gaye", "bik gyi", "bik gayi", "sale", "sales", "sold", "बेचा", "बेचे", "बिका"]
    purchase_kw = ["kharida", "kharide", "khareeda", "purchase", "purchased", "stock aaya", "maal aaya", "buy", "bought", "खरीदा", "खरीदे", "ख़रीदा"]
    delete_kw = ["hata do", "hatao", "delete", "remove", "nikal do", "hata dena", "हटा दो", "हटाओ", "डिलीट"]
    add_kw = ["add karo", "add kro", "naya product", "new product", "add product", "product add", "item add", "जोड़ो", "नया प्रोडक्ट"]
    adjust_kw = ["current stock", "stock adjust", "actual count", "actual stock", "stock set", "stock hai", "current count", "physical count", "adjust karo", "adjust kro", "करंट स्टॉक", "स्टॉक सेट", "स्टॉक"]

    task_name = "record_purchase"
    if any(re.search(r'\b' + re.escape(kw) + r'\b', text) or kw in text for kw in sale_kw):
        task_name = "record_sale"
    elif any(re.search(r'\b' + re.escape(kw) + r'\b', text) or kw in text for kw in delete_kw):
        task_name = "delete_product"
    elif any(re.search(r'\b' + re.escape(kw) + r'\b', text) or kw in text for kw in add_kw):
        task_name = "create_product"
    elif any(re.search(r'\b' + re.escape(kw) + r'\b', text) or kw in text for kw in adjust_kw):
        task_name = "adjust_stock"
    elif any(re.search(r'\b' + re.escape(kw) + r'\b', text) or kw in text for kw in purchase_kw):
        task_name = "record_purchase"
    else:
        return None

    qty = None
    qty_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:packet|packets|pack|packs|piece|pieces|bottle|bottles|carton|cartons|kg|kilo|gm|gram|liter|litre|l|pouch|dabba|dabbe|किलोग्राम|किलो|लीटर|पैकेट|पीस)?', text)
    if qty_match:
        try:
            qty = Decimal(qty_match.group(1))
        except Exception:
            qty = None

    unit = "piece"
    unit_match = re.search(r'(packet|packets|pack|packs|piece|pieces|bottle|bottles|carton|cartons|kg|kilo|gm|gram|liter|litre|l|pouch|dabba|dabbe|किलोग्राम|किलो|लीटर|पैकेट|पीस|ग्राम)', text)
    if unit_match:
        u_raw = unit_match.group(1)
        if any(w in u_raw for w in ["packet", "pack", "पैकेट"]):
            unit = "packet"
        elif any(w in u_raw for w in ["bottle", "बोतल"]):
            unit = "bottle"
        elif any(w in u_raw for w in ["carton", "कार्टन"]):
            unit = "carton"
        elif any(w in u_raw for w in ["kg", "kilo", "किलोग्राम", "किलो"]):
            unit = "kg"
        elif any(w in u_raw for w in ["liter", "litre", "l", "लीटर"]):
            unit = "litre"
        elif any(w in u_raw for w in ["gm", "gram", "ग्राम"]):
            unit = "gram"

    p_price = None
    s_price = None
    p_match = re.search(r'(?:purchase|kharid|cost|rate|पर्चेज|खरीद)\s*(?:price|कॉस्ट)?\s*[:=]?\s*(\d+(?:\.\d+)?)', text)
    if p_match:
        p_price = Decimal(p_match.group(1))
    s_match = re.search(r'(?:selling|biki|sale|mrp|सेलिंग|बिक्री)\s*(?:price|कॉस्ट)?\s*[:=]?\s*(\d+(?:\.\d+)?)', text)
    if s_match:
        s_price = Decimal(s_match.group(1))

    if task_name == "record_purchase" and p_price is None:
        gen_price = re.search(r'(?:₹|rs\.?|rupaye|rupees)?\s*(\d+(?:\.\d+)?)\s*(?:₹|rs\.?|rupaye|rupees|ka|mein|में|का)\b', text)
        if gen_price:
            p_price = Decimal(gen_price.group(1))

    cleaned = raw_text
    remove_tokens = sale_kw + purchase_kw + delete_kw + add_kw + adjust_kw + [
        "packet", "packets", "pack", "packs", "piece", "pieces", "bottle", "bottles", "carton", "cartons",
        "kg", "kilo", "litre", "liter", "l", "gm", "gram", "pouch", "dabba", "dabbe",
        "किलोग्राम", "किलो", "लीटर", "पैकेट", "पीस", "ग्राम",
        "rupaye", "rupees", "rs", "₹", "ka", "ke", "ki", "k", "mein", "se", "hai", "karo", "kro",
        "का", "की", "के", "में", "से", "है", "करो", "कॉस्ट", "पर्चेज", "सेलिंग",
        "product", "item", "naam", "purchase", "selling", "price", "rate", "cost", "naya", "new",
        "bhi", "aur", "and", "to", "bhi", "पैकेट", "रुपये", "।"
    ]
    for tok in remove_tokens:
        cleaned = re.sub(re.escape(tok), ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b\d+(?:\.\d+)?\b', ' ', cleaned)
    p_name = " ".join(cleaned.split()).strip()

    if not p_name:
        p_name = "Item"

    if task_name == "record_sale" and qty is None:
        qty = Decimal("1")
    elif task_name == "record_purchase" and qty is None:
        qty = Decimal("1")
    elif task_name == "create_product":
        if p_price is None:
            p_price = Decimal("0")
        if s_price is None:
            s_price = Decimal("0")
        if qty is None:
            qty = None

    return ManagerTask(
        task=task_name,
        entities={
            "product_name": p_name,
            "quantity": qty,
            "actual_count": qty if task_name == "adjust_stock" else None,
            "unit": unit,
            "purchase_price": p_price,
            "selling_price": s_price,
        }
    )

def _understand(state: ManagerGraphState) -> dict:
    structured_llm = llm.with_structured_output(ManagerPlan, method="json_mode")
    context = state.get("context", "").strip()
    user_content = state["raw_input"]
    if context:
        user_content = (
            f"PREVIOUS PENDING TASKS/CONTEXT (DATA ONLY):\n{context}\n\n"
            f"LATEST USER SPOKEN ANSWER:\n{user_content}\n\n"
            "INSTRUCTIONS:\n"
            "- If the user is providing missing details (price, quantity) for the pending task, merge that info into the pending task.\n"
            "- But if the user speaks a NEW command or action (e.g. sale 'beche', purchase 'kharida', delete 'hata do', add 'add karo', or asking stock), DISCARD the previous pending task and create fresh tasks for the new utterance!"
        )

    try:
        plan = structured_llm.invoke(
            [
                ("system", MANAGER_SYSTEM_PROMPT + "\nReturn ONLY a valid JSON object matching the ManagerPlan schema."),
                ("human", user_content),
            ]
        )
    except Exception:
        fallback_llm = llm.with_structured_output(ManagerPlan)
        plan = fallback_llm.invoke(
            [
                ("system", MANAGER_SYSTEM_PROMPT),
                ("human", user_content),
            ]
        )

    return {"plan": plan.model_dump(mode="json")}

def _validate_and_route(state: ManagerGraphState) -> dict:
    plan = ManagerPlan.model_validate(state["plan"])
    missing_by_task: list[dict] = []
    routes: list[dict] = []

    raw_ctx = state.get("context", "").strip()
    context_tasks = []
    if raw_ctx:
        try:
            ctx_obj = json.loads(raw_ctx)
            context_tasks = ctx_obj.get("tasks", [])
        except Exception:
            pass

    raw_input_text = state.get("raw_input", "")
    
    sale_kw = ["beche", "becha", "becho", "bika", "bik gaya", "bik gaye", "bik gyi", "bik gayi", "sale", "sales", "sold"]
    purchase_kw = ["kharida", "kharide", "khareeda", "purchase", "purchased", "stock aaya", "maal aaya", "buy", "bought"]
    delete_kw = ["hata do", "hatao", "delete", "remove", "nikal do", "hata dena"]
    add_kw = ["add karo", "add kro", "naya product", "new product", "add product", "product add", "item add"]

    has_sale = any(re.search(r'\b' + re.escape(kw) + r'\b', raw_input_text.lower()) for kw in sale_kw)
    has_purchase = any(re.search(r'\b' + re.escape(kw) + r'\b', raw_input_text.lower()) for kw in purchase_kw)
    has_delete = any(re.search(r'\b' + re.escape(kw) + r'\b', raw_input_text.lower()) for kw in delete_kw)
    has_add = any(re.search(r'\b' + re.escape(kw) + r'\b', raw_input_text.lower()) for kw in add_kw)
    has_transaction_intent = has_sale or has_purchase or has_delete or has_add

    t_lower = raw_input_text.lower()
    _purchase_kw = [
        "purchase summary", "purchases", "purchase kitni", "kitni purchase", "kitna purchase",
        "kitna kharida", "kitne kharide", "kitna maal aaya", "kitna stock aaya",
        "total purchase", "aaj ki purchase", "purchase batao", "खरीद कितनी", "कितना खरीदा",
        "total khareed", "total purchase kitni", "purchase report"
    ]
    is_purchase_query = any(w in t_lower for w in _purchase_kw) and not any(w in t_lower for w in ["becha", "beche", "hata", "add"])
    is_sales_query = any(w in t_lower for w in ["sales", "सेल्स", "बिक्री", "bikri", "kamai", "कमाई", "kitna bika", "kitni biki"]) and not any(w in t_lower for w in ["becha", "beche", "kharida", "hata", "add"]) and not is_purchase_query
    is_profit_query = any(w in t_lower for w in ["profit", "प्रॉफिट", "munafa", "मुनाफा", "fayda", "फायदा"]) and not any(w in t_lower for w in ["kaise badhaun", "kya karun", "loss ho raha"])
    is_stock_val_query = any(w in t_lower for w in ["stock valuation", "valuation", "maal ki value", "inventory value", "total value", "स्टॉक वैल्यू", "वैल्यूएशन", "dukaan ka maal kitne ka"])
    is_low_stock_query = any(w in t_lower for w in ["low stock", "khatam hone", "खत्म होने", "kam stock", "कम स्टॉक", "kya khatam"])
    is_top_selling_query = any(w in t_lower for w in ["top selling", "sabse zyada bika", "सबसे ज्यादा", "top seller"])

    if is_purchase_query:
        has_purchase = False
        has_transaction_intent = has_sale or has_delete or has_add

    period = "today"
    if any(w in t_lower for w in ["kal", "कल", "yesterday"]):
        period = "yesterday"
    elif any(w in t_lower for w in ["hafta", "हफ्ते", "week"]):
        period = "this_week"
    elif any(w in t_lower for w in ["mahina", "महीने", "month"]):
        period = "this_month"

    if is_sales_query:
        plan.direct_reply = None
        plan.unsupported_request = False
        plan.tasks = [ManagerTask(task="sales_summary", entities={"period": period})]
    elif is_profit_query:
        plan.direct_reply = None
        plan.unsupported_request = False
        plan.tasks = [ManagerTask(task="profit_summary", entities={"period": period})]
    elif is_low_stock_query:
        plan.direct_reply = None
        plan.unsupported_request = False
        plan.tasks = [ManagerTask(task="low_stock", entities={})]
    elif is_top_selling_query:
        plan.direct_reply = None
        plan.unsupported_request = False
        plan.tasks = [ManagerTask(task="top_selling", entities={"period": period})]
    elif is_purchase_query:
        plan.direct_reply = None
        plan.unsupported_request = False
        plan.tasks = [ManagerTask(task="purchase_summary", entities={"period": period})]
    elif is_stock_val_query:
        plan.direct_reply = None
        plan.unsupported_request = False
        plan.tasks = [ManagerTask(task="stock_valuation", entities={})]

    _is_known_intent = (
        is_sales_query or is_purchase_query or is_profit_query or is_stock_val_query
        or is_low_stock_query or is_top_selling_query or has_transaction_intent
    )
    _has_devanagari = bool(re.search(r'[\u0900-\u097F]', raw_input_text))
    if _has_devanagari and not _is_known_intent and not plan.tasks:
        plan.tasks = []
        plan.direct_reply = (
            'Maafi chahta hoon, main ye samajh nahi paaya. '
            'Clearly bolein — jaise: Aaj ki sales batao, '
            'Amul Milk 5 packet beche, ya Low stock dikhao.'
        )
        plan.unsupported_request = False
    if has_transaction_intent:
        plan.direct_reply = None

    if not plan.tasks and has_transaction_intent:
        fallback_task = extract_transaction_fallback(raw_input_text)
        if fallback_task:
            plan.tasks = [fallback_task]

    if len(plan.tasks) == 1:
        single_t = plan.tasks[0]
        if has_sale and not has_purchase and not is_sales_query:
            single_t.task = "record_sale"
            single_t.entities.purchase_price = None
            single_t.entities.selling_price = None
            if single_t.entities.quantity is None:
                single_t.entities.quantity = Decimal("1")
        elif has_add and not has_sale and not has_purchase:
            single_t.task = "create_product"
        elif has_delete:
            single_t.task = "delete_product"
        elif has_purchase and not has_sale and not is_purchase_query:
            single_t.task = "record_purchase"
            if single_t.entities.quantity is None:
                single_t.entities.quantity = Decimal("1")

    if plan.tasks:
        plan.direct_reply = None

    create_tasks = [t for t in plan.tasks if t.task == "create_product"]
    os_tasks = [t for t in plan.tasks if t.task == "opening_stock"]
    if create_tasks and os_tasks:
        merged_plan_tasks = []
        for t in plan.tasks:
            if t.task == "opening_stock":
                match_cp = next(
                    (cp for cp in create_tasks if (cp.entities.product_name or "").strip().lower() == (t.entities.product_name or "").strip().lower() or not t.entities.product_name),
                    create_tasks[0]
                )
                if match_cp.entities.quantity is None and t.entities.quantity is not None:
                    match_cp.entities.quantity = t.entities.quantity
                if match_cp.entities.unit is None and t.entities.unit is not None:
                    match_cp.entities.unit = t.entities.unit
                if match_cp.entities.purchase_price is None and t.entities.purchase_price is not None:
                    match_cp.entities.purchase_price = t.entities.purchase_price
                if match_cp.entities.selling_price is None and t.entities.selling_price is not None:
                    match_cp.entities.selling_price = t.entities.selling_price
                continue
            merged_plan_tasks.append(t)
        plan.tasks = merged_plan_tasks

    HINDI_TO_ENG = {
        "शैंपू": "shampoo", "शैम्पू": "shampoo", "दूध": "milk", "दही": "curd",
        "मक्खन": "butter", "तेल": "oil", "साबुन": "soap", "चावल": "rice", "राइस": "rice",
        "आटा": "atta", "दाल": "dal", "चीनी": "sugar", "शक्कर": "sugar", "शुगर": "sugar",
        "चाय": "tea", "बिस्कुट": "biscuit", "बिस्किट": "biscuit", "ब्रेड": "bread",
        "नमक": "salt"
    }

    HINDI_UNIT_MAP = {
        "किलोग्राम": "kg", "किलो": "kg", "kilogram": "kg", "kgs": "kg",
        "लीटर": "liter", "लीटरों": "liter", "litres": "liter", "litre": "liter", "ltr": "liter",
        "पैकेट": "packet", "packets": "packet", "pkt": "packet",
        "पीस": "piece", "pieces": "piece", "pcs": "piece", "pc": "piece",
        "बोतल": "bottle", "bottles": "bottle",
        "दर्जन": "dozen", "dozens": "dozen",
        "ग्राम": "gram", "grams": "gram", "gm": "gram"
    }

    for index, task in enumerate(plan.tasks):
        if task.task == "adjust_stock":
            if task.entities.actual_count is not None and task.entities.quantity is None:
                task.entities.quantity = task.entities.actual_count
            elif task.entities.quantity is not None and task.entities.actual_count is None:
                task.entities.actual_count = task.entities.quantity

        p_name = (task.entities.product_name or "").strip().lower()
        if p_name in {"product", "प्रोडक्ट", "item", "saman", "सामान", "चीज़", "task"}:
            task.entities.product_name = None

        if task.task in INVENTORY_TASKS and not task.entities.product_name and raw_input_text:
            cleaned = raw_input_text
            for noise in ["प्रोडक्ट", "product", "item", "हटा दो", "हटाओ", "डिलीट करो", "delete karo", "निकाल दो", "remove karo", "delete", "remove", "add karo", "add kro", "naya", "new", "becha", "kharida"]:
                cleaned = re.sub(re.escape(noise), " ", cleaned, flags=re.IGNORECASE)
            extracted = cleaned.strip()
            if extracted:
                task.entities.product_name = extracted

        cur_name = (task.entities.product_name or "").strip()
        for h_word, eng_word in HINDI_TO_ENG.items():
            if h_word in cur_name:
                task.entities.product_name = eng_word
                break

        if task.entities.unit:
            u_clean = task.entities.unit.strip().lower()
            if u_clean in HINDI_UNIT_MAP:
                task.entities.unit = HINDI_UNIT_MAP[u_clean]
        elif raw_input_text:
            for u_word, u_norm in HINDI_UNIT_MAP.items():
                if re.search(r'\b' + re.escape(u_word) + r'\b', raw_input_text, re.IGNORECASE) or u_word in raw_input_text:
                    task.entities.unit = u_norm
                    break

        if index < len(context_tasks):
            prev_e = context_tasks[index].get("entities", {})
            if not task.entities.product_name:
                task.entities.product_name = prev_e.get("product_name") or prev_e.get("brand")
            if not task.entities.brand and prev_e.get("brand"):
                task.entities.brand = prev_e.get("brand")
            if not task.entities.variant and prev_e.get("variant"):
                task.entities.variant = prev_e.get("variant")
            if not task.entities.category and prev_e.get("category"):
                task.entities.category = prev_e.get("category")
            if task.entities.unit is None and prev_e.get("unit"):
                task.entities.unit = prev_e.get("unit")
            if task.entities.purchase_price is None and prev_e.get("purchase_price") is not None:
                task.entities.purchase_price = prev_e.get("purchase_price")
            if task.entities.selling_price is None and prev_e.get("selling_price") is not None:
                task.entities.selling_price = prev_e.get("selling_price")
            if task.task != "adjust_stock":
                if task.entities.quantity is None and prev_e.get("quantity") is not None:
                    task.entities.quantity = prev_e.get("quantity")
            else:
                if task.entities.actual_count is None and prev_e.get("actual_count") is not None:
                    task.entities.actual_count = prev_e.get("actual_count")
                    task.entities.quantity = prev_e.get("actual_count")

        if not task.entities.product_name and task.entities.brand:
            task.entities.product_name = task.entities.brand

        if task.task in {"record_purchase", "record_sale"} and task.entities.quantity is None and task.entities.purchase_price is not None:
            task.entities.quantity = 1

        missing_csv = validate_task_fields.invoke(
            {
                "task_name": task.task,
                "entities_json": task.entities.model_dump_json(),
            }
        )
        missing = [field for field in missing_csv.split(",") if field]
        if missing:
            missing_by_task.append(
                {"task_index": index, "task": task.task, "fields": missing}
            )

        specialist = route_task_to_specialist.invoke({"task_name": task.task})
        routes.append({"task_index": index, "task": task.task, "specialist": specialist})

    if getattr(plan, "direct_reply", None) and plan.direct_reply.strip():
        status = "done"
        reply = plan.direct_reply.strip()
    elif plan.unsupported_request:
        status = "unsupported"
        reply = plan.unsupported_reason or "Ye request abhi voice se supported nahi hai."
    elif not plan.tasks:
        status = "needs_clarification"
        reply = plan.clarification_question or "Aap kis product ya stock ke baare mein baat karna chahte hain?"
    elif missing_by_task:
        status = "needs_clarification"
        questions = []
        for item in missing_by_task:
            t_idx = item["task_index"]
            task_obj = plan.tasks[t_idx]
            brand_str = f" ({task_obj.entities.brand})" if task_obj.entities.brand else ""
            p_name = (task_obj.entities.product_name or "Product") + brand_str
            m_fields = item["fields"]

            if task_obj.task in {"create_product", "opening_stock"}:
                needed = []
                if "purchase_price" in m_fields:
                    needed.append("purchase price")
                if "selling_price" in m_fields:
                    needed.append("selling price")
                if "quantity" in m_fields:
                    needed.append("opening stock")
                if "unit" in m_fields:
                    needed.append("unit (jaise packet ya piece)")
                if len(needed) > 1:
                    needed_str = ", ".join(needed[:-1]) + " aur " + needed[-1]
                else:
                    needed_str = needed[0] if needed else "details"
                questions.append(f"{p_name} ka {needed_str} kitna hai?")
            elif "purchase_price" in m_fields and "selling_price" in m_fields:
                questions.append(f"{p_name} ka purchase price aur selling price kitna hai?")
            elif "selling_price" in m_fields:
                questions.append(f"{p_name} ka selling price per unit kya rakhein?")
            elif "purchase_price" in m_fields:
                questions.append(f"{p_name} ka purchase price per unit kya hai?")
            elif "quantity" in m_fields:
                questions.append(f"{p_name} ki quantity kitni hai?")
            elif "actual_count" in m_fields:
                questions.append(f"{p_name} ka physical count kitna hai?")
            elif "update_field" in m_fields:
                questions.append(f"{p_name} ka kya update karna hai? Jaise selling price ya purchase price?")
            else:
                questions.append(f"{p_name} ke missing details bataiye.")

        if questions:
            reply = " ".join(questions)
        elif plan.clarification_question and len(plan.clarification_question.strip()) > 8:
            reply = plan.clarification_question
        else:
            reply = "Kripya missing details bataiye taaki main aage badh sakoon." 
    else:
        status = "ready_to_route"
        reply = "Request understood and ready for the specialist agent."

    return {
        "plan": plan.model_dump(mode="json"),
        "missing_by_task": missing_by_task,
        "routes": routes,
        "status": status,
        "reply_text": reply,
        "spoken_text": reply,
    }

def build_manager_graph():
    """Build the manager graph. Safe to call once at application startup."""
    graph = StateGraph(ManagerGraphState)
    graph.add_node("understand", _understand)
    graph.add_node("validate_and_route", _validate_and_route)
    graph.add_edge(START, "understand")
    graph.add_edge("understand", "validate_and_route")
    graph.add_edge("validate_and_route", END)
    return graph.compile()

manager_graph = build_manager_graph()

def run_manager_agent(raw_input: str, context: str = "") -> ManagerGraphState:
    """Parse one user turn and return a validated, ordered routing plan."""
    normalized_input = normalize_number_words(raw_input)
    return manager_graph.invoke({"raw_input": normalized_input, "context": context})

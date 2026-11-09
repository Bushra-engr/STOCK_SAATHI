import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

Status = Literal[
    "understanding", "needs_clarification", "awaiting_confirmation",
    "executing", "done", "failed",
]

TaskName = Literal[
    "record_purchase", "record_sale", "record_damage", "adjust_stock",
    "create_product", "update_product", "delete_product", "opening_stock", "inventory_lookup",
    "sales_summary", "purchase_summary", "profit_summary", "stock_valuation",
    "low_stock", "top_selling", "slow_moving", "reorder_suggestions",
]

DraftKind = Literal["purchase", "sale", "damage", "adjustment", "create_product", "delete_product"]

Period = Literal["today", "yesterday", "this_week", "this_month", "last_month"]

UNSUPPORTED_MESSAGE = "Ye aap Inventory page par jaake khud kar sakte hain."

class Entities(BaseModel):
    product_name: str | None = Field(
        default=None,
        description="Name of the product or item (e.g. Amul Milk, Dove Shampoo, Bread, Parle-G). Never leave null if an item was mentioned."
    )
    brand: str | None = Field(
        default=None,
        description="Brand name if specified (e.g. Amul, Dove, Britannia, Tata)"
    )
    variant: str | None = Field(
        default=None,
        description="Variant, flavour, or size (e.g. 500ml, small, blue, 1kg)"
    )
    category: str | None = Field(
        default=None,
        description="Category (e.g. Dairy, Personal Care, Grocery, Snacks)"
    )
    unit: str | None = Field(
        default=None,
        description="Unit of measurement (e.g. packet, piece, bottle, kg, litre, box)"
    )
    quantity: Decimal | None = Field(
        default=None,
        ge=0,
        description="Quantity or number of units (e.g. 1, 5, 20). If user says singular item like 'shampoo purchase kiya 100 rs', default to 1."
    )
    purchase_price: Decimal | None = Field(
        default=None,
        ge=0,
        description="Cost/purchase price per unit in rupees"
    )
    selling_price: Decimal | None = Field(
        default=None,
        ge=0,
        description="Selling price per unit in rupees"
    )
    new_name: str | None = Field(
        default=None,
        description="New name if the user wants to rename the product"
    )
    reorder_level: Decimal | None = Field(
        default=None,
        ge=0,
        description="Reorder threshold level"
    )
    actual_count: Decimal | None = Field(
        default=None,
        ge=0,
        description="Actual counted physical quantity for stock adjustments"
    )
    period: Period | None = Field(
        default=None,
        description="Time period for BI queries: today, yesterday, this_week, this_month, last_month"
    )

    @model_validator(mode="after")
    def normalize_entities(self):
        if not self.product_name and self.brand:
            self.product_name = self.brand
        if self.product_name:
            self.product_name = self.product_name.strip()
        if self.brand:
            self.brand = self.brand.strip()
        if self.variant:
            self.variant = self.variant.strip()
        return self

REQUIRED_FIELDS: dict[str, list[str]] = {
    "record_purchase": ["product_name", "quantity"],
    "record_sale": ["product_name", "quantity"],
    "record_damage": ["product_name", "quantity"],
    "adjust_stock": ["product_name", "actual_count"],
    "create_product": ["product_name", "purchase_price", "selling_price", "quantity", "unit"],
    "update_product": ["product_name"],
    "delete_product": ["product_name"],
    "opening_stock": ["product_name", "quantity", "purchase_price", "selling_price"],
    "inventory_lookup": ["product_name"],
}

def find_missing_fields(task: str, entities: Entities) -> list[str]:
    required = REQUIRED_FIELDS.get(task, [])
    missing = []
    for name in required:
        val = getattr(entities, name, None)
        if val is None:
            if name == "quantity" and task in {"record_purchase", "record_sale"}:
                if task == "record_purchase" and entities.purchase_price is not None:
                    entities.quantity = Decimal("1")
                    continue
            missing.append(name)

    if task == "update_product" and not missing:
        has_update = any([
            entities.purchase_price is not None,
            entities.selling_price is not None,
            entities.new_name is not None,
            entities.brand is not None,
            entities.variant is not None,
            entities.unit is not None,
            entities.category is not None,
            entities.reorder_level is not None,
        ])
        if not has_update:
            missing.append("update_field")

    return missing

class Draft(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    kind: DraftKind
    payload: dict[str, Any]
    summary: str
    expires_at: datetime

    def is_expired(self) -> bool:
        return utcnow() >= self.expires_at

class ToolResult(BaseModel):
    tool: str
    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

class ConversationState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    user_id: str = Field(frozen=True)
    session_id: str = Field(frozen=True)

    raw_input: str = ""
    language: str | None = None

    intent: str | None = None
    entities: Entities = Field(default_factory=Entities)
    tasks: list[TaskName] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    clarification_question: str | None = None

    current_task_index: int = 0
    status: Status = "understanding"

    draft: Draft | None = None

    tool_results: list[ToolResult] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    reply_text: str = ""
    spoken_text: str = ""

    updated_at: datetime = Field(default_factory=utcnow)

    def touch(self) -> None:
        self.updated_at = utcnow()

    def set_draft(self, kind: DraftKind, payload: dict[str, Any], summary: str,
                  ttl_minutes: int = 5) -> Draft:
        self.draft = Draft(
            kind=kind,
            payload=payload,
            summary=summary,
            expires_at=utcnow() + timedelta(minutes=ttl_minutes),
        )
        self.status = "awaiting_confirmation"
        return self.draft

    def active_draft(self) -> Draft | None:
        if self.draft and self.draft.is_expired():
            self.draft = None
            self.status = "understanding"
            self.errors.append("draft_expired")
        return self.draft

    def consume_draft(self) -> Draft | None:
        draft = self.active_draft()
        self.draft = None
        return draft

    def add_result(self, tool: str, ok: bool,
                   data: dict[str, Any] | None = None, error: str | None = None) -> None:
        self.tool_results.append(ToolResult(tool=tool, ok=ok, data=data or {}, error=error))

    def reset_for_new_request(self) -> None:
        self.intent = None
        self.entities = Entities()
        self.tasks = []
        self.missing_fields = []
        self.clarification_question = None
        self.current_task_index = 0
        self.status = "understanding"
        self.draft = None
        self.tool_results = []
        self.errors = []
        self.reply_text = ""
        self.spoken_text = ""

class StateStore:
    def __init__(self, idle_minutes: int = 30):
        self._states: dict[tuple[str, str], ConversationState] = {}
        self._lock = threading.Lock()
        self._idle = timedelta(minutes=idle_minutes)

    def get_or_create(self, user_id: str, session_id: str) -> ConversationState:
        key = (user_id, session_id)
        with self._lock:
            self._purge_locked()
            state = self._states.get(key)
            if state is None:
                state = ConversationState(user_id=user_id, session_id=session_id)
                self._states[key] = state
            return state

    def save(self, state: ConversationState) -> None:
        with self._lock:
            state.touch()
            self._states[(state.user_id, state.session_id)] = state

    def clear(self, user_id: str, session_id: str) -> None:
        with self._lock:
            self._states.pop((user_id, session_id), None)

    def _purge_locked(self) -> None:
        cutoff = utcnow() - self._idle
        stale = [k for k, s in self._states.items() if s.updated_at < cutoff]
        for key in stale:
            del self._states[key]

state_store = StateStore()

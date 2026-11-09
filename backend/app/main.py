from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from database.base import Base
from database.connection import engine
from routes.inventory import router as inventory_router
from routes.products import router as products_router
from routes.users import router as user_router
from routes.dashboard import router as dashboard_router
from voice.router import router as voice_router
import models

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();"))
    except Exception as exc:
        logger.warning("Could not auto-create tables or run migrations on startup: %s", exc)
    yield

app = FastAPI(
    title="StockSaathi API",
    description="Voice-first AI Inventory Management System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(dashboard_router)
app.include_router(voice_router)

frontend_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"

@app.get("/", include_in_schema=False)
def home():
    if frontend_dir.is_dir():
        return FileResponse(frontend_dir / "index.html")
    return {"message": "StockSaathi API is running"}

@app.get("/health")
def health_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "connected"}

if frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

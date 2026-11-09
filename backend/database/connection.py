from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    url=DATABASE_URL,
    pool_size=15,
    max_overflow=10,
    pool_recycle=300,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

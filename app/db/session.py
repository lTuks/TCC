from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings
import os

class Base(DeclarativeBase):
    pass

url = settings.database_url or os.getenv("DATABASE_URL", "sqlite:///./app.db")

if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+psycopg://", 1)
elif url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {}
if url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    url,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

def init_db():
    from app.models import user, document, usage_log, tutor
    Base.metadata.create_all(bind=engine)

import app.models.tutor

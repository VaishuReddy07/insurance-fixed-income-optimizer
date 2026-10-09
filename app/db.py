from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import DB_URL

_engine_options = {"pool_pre_ping": True}
if DB_URL.startswith("sqlite"):
    _engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DB_URL, **_engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

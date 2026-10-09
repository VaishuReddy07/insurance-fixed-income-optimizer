from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class Instrument(Base):
    __tablename__ = "instruments"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    issuer: Mapped[str] = mapped_column(String, index=True)
    sector: Mapped[str] = mapped_column(String)
    rating: Mapped[str] = mapped_column(String, index=True)
    currency: Mapped[str] = mapped_column(String)
    maturity_years: Mapped[float] = mapped_column(Float)
    duration: Mapped[float] = mapped_column(Float)
    spread_duration: Mapped[float] = mapped_column(Float)
    yield_pct: Mapped[float] = mapped_column(Float)
    spread_bps: Mapped[float] = mapped_column(Float)
    liquidity_score: Mapped[float] = mapped_column(Float)
    esg_score: Mapped[float] = mapped_column(Float)
    capital_factor: Mapped[float] = mapped_column(Float)

class OptimizationRun(Base):
    __tablename__ = "optimization_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    objective: Mapped[float] = mapped_column(Float)
    expected_yield_pct: Mapped[float] = mapped_column(Float)
    duration: Mapped[float] = mapped_column(Float)
    weights: Mapped[dict] = mapped_column(JSON)
    constraints: Mapped[dict] = mapped_column(JSON)

class PricePoint(Base):
    __tablename__ = "price_points"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), index=True)
    date: Mapped[str] = mapped_column(String, index=True)
    total_return: Mapped[float] = mapped_column(Float)


from contextlib import asynccontextmanager
import hmac
import logging
import os
import time
import uuid
from fastapi import FastAPI, Depends, HTTPException
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import numpy as np
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .config import API_KEY, BASE_DIR, DASHBOARD_FILE
from .market_data import MarketDataUnavailable, get_ecb_reference_rate
from .db import Base, engine, get_db
from .models import Instrument, OptimizationRun, PricePoint
from .data import seed_market
from .schemas import OptimizeRequest
from .optimizer import optimize
from .analytics import risk_report, performance_report
from .ml import anomaly_model_report

@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("RUN_MIGRATIONS", "false").lower() in {"1", "true", "yes"}:
        from alembic import command
        from alembic.config import Config
        alembic_config = Config(str(BASE_DIR / "alembic.ini"))
        alembic_config.set_main_option("script_location", str(BASE_DIR / "migrations"))
        command.upgrade(alembic_config, "head")
    else:
        Base.metadata.create_all(bind=engine)
    from .db import SessionLocal
    with SessionLocal() as db:
        seed_market(db)
    yield

app = FastAPI(title="Insurance Fixed-Income Optimizer", version="1.0.0",
              description="Portfolio research dashboard using deterministic synthetic market data.", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(DASHBOARD_FILE.parent)), name="static")
logger = logging.getLogger("portfolio.api")
logger.setLevel(logging.INFO)

@app.middleware("http")
async def request_controls(request, call_next):
    request_id = uuid.uuid4().hex
    started = time.perf_counter()
    if API_KEY and request.url.path.startswith("/api/"):
        provided = request.headers.get("Authorization", "")
        expected = f"Bearer {API_KEY}"
        if not hmac.compare_digest(provided, expected):
            logger.warning("request_id=%s auth_rejected path=%s", request_id, request.url.path)
            response = JSONResponse(status_code=401, content={"detail": "Valid bearer API key required"},
                                    headers={"WWW-Authenticate": "Bearer"})
            response.headers["X-Request-ID"] = request_id
            return response
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info("request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
                request_id, request.method, request.url.path, response.status_code, elapsed_ms)
    return response

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http", "scheme": "bearer", "bearerFormat": "API key"
    }
    for path, operations in schema.get("paths", {}).items():
        if path.startswith("/api/"):
            for operation in operations.values():
                if isinstance(operation, dict) and "responses" in operation:
                    operation["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(DASHBOARD_FILE)

def load_returns(db: Session, fill_missing: bool = True) -> pd.DataFrame:
    rows = db.execute(select(PricePoint.instrument_id, PricePoint.date, PricePoint.total_return)
                      .order_by(PricePoint.date, PricePoint.instrument_id)).all()
    frame = pd.DataFrame(rows, columns=["instrument_id", "date", "total_return"])
    frame = frame.pivot(index="date", columns="instrument_id", values="total_return").sort_index()
    return frame.fillna(0) if fill_missing else frame

@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)):
    count = db.scalar(select(func.count()).select_from(Instrument)) or 0
    latest_observation = db.scalar(select(func.max(PricePoint.date)))
    return {"status": "ok", "instrument_count": count, "data_as_of": latest_observation,
            "data_type": "deterministic synthetic"}

@app.get("/api/v1/market-data/ecb-reference")
def ecb_reference_rate(force_refresh: bool = False):
    """Daily ECB euro-area AAA 10-year sovereign reference rate (not intraday bond pricing)."""
    try:
        return get_ecb_reference_rate(force_refresh=force_refresh)
    except MarketDataUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.get("/api/v1/universe")
def universe(db: Session = Depends(get_db)):
    return [vars_instrument(x) for x in db.scalars(select(Instrument).order_by(Instrument.id)).all()]

def vars_instrument(x):
    return {"id":x.id,"issuer":x.issuer,"sector":x.sector,"rating":x.rating,"currency":x.currency,
            "maturity_years":x.maturity_years,"duration":x.duration,"spread_duration":x.spread_duration,
            "yield_pct":x.yield_pct,"spread_bps":x.spread_bps,"liquidity_score":x.liquidity_score,
            "esg_score":x.esg_score,"capital_factor":x.capital_factor}

@app.post("/api/v1/optimize")
def run_optimization(request: OptimizeRequest, db: Session = Depends(get_db)):
    instruments = db.scalars(select(Instrument).order_by(Instrument.id)).all()
    returns = load_returns(db)
    try:
        result = optimize(instruments, returns, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    record = OptimizationRun(objective=result["objective"], expected_yield_pct=result["expected_yield_pct"],
                             duration=result["duration"], weights=result["weights"], constraints=request.model_dump())
    db.add(record); db.commit(); db.refresh(record)
    return {"run_id":record.id,"created_at":record.created_at.isoformat(),**result}

def current_run(db):
    return db.scalar(select(OptimizationRun).order_by(OptimizationRun.id.desc()).limit(1))

@app.get("/api/v1/portfolio/current")
def current_portfolio(db: Session = Depends(get_db)):
    run = current_run(db)
    if not run: raise HTTPException(status_code=404, detail="Run POST /api/v1/optimize first")
    assets = {x.id:x for x in db.scalars(select(Instrument)).all()}
    return {"run_id":run.id,"expected_yield_pct":run.expected_yield_pct,"duration":run.duration,
            "positions":[{**vars_instrument(assets[k]),"weight":v} for k,v in run.weights.items()]}

@app.get("/api/v1/analytics/risk")
def risk(db: Session = Depends(get_db)):
    run=current_run(db)
    if not run: raise HTTPException(status_code=404, detail="Run POST /api/v1/optimize first")
    instruments=db.scalars(select(Instrument)).all()
    return risk_report(instruments,run.weights,load_returns(db))

@app.get("/api/v1/analytics/capital")
def capital(db: Session = Depends(get_db)):
    run=current_run(db)
    if not run: raise HTTPException(status_code=404, detail="Run POST /api/v1/optimize first")
    assets={x.id:x for x in db.scalars(select(Instrument)).all()}
    rows=[{"instrument_id":i,"weight":w,"rating":assets[i].rating,"factor":assets[i].capital_factor,
           "contribution_pct_nav":round(w*assets[i].capital_factor*100,4)} for i,w in run.weights.items()]
    return {"methodology":"illustrative spread-risk proxy; not Solvency II standard formula",
            "capital_proxy_pct_nav":round(sum(x["contribution_pct_nav"] for x in rows),4),"positions":rows}

@app.get("/api/v1/analytics/performance")
def performance(db: Session = Depends(get_db)):
    run=current_run(db)
    if not run: raise HTTPException(status_code=404, detail="Run POST /api/v1/optimize first")
    return performance_report(load_returns(db),run.weights)

@app.get("/api/v1/analytics/ml-anomalies")
def ml_anomalies(db: Session = Depends(get_db)):
    """Exploratory Isolation Forest inference over synthetic return observations."""
    return anomaly_model_report(load_returns(db, fill_missing=False))

@app.get("/api/v1/analytics/quality")
def data_quality(db: Session = Depends(get_db)):
    """Reference data checks and robust synthetic-return outlier flags."""
    instruments=db.scalars(select(Instrument)).all()
    frame=load_returns(db, fill_missing=False)
    missing_values=int(frame.isna().sum().sum())
    frame=frame.fillna(0)
    issues=[]
    for asset in instruments:
        if not (0 <= asset.esg_score <= 100): issues.append({"instrument_id":asset.id,"field":"esg_score","issue":"out_of_range"})
        if asset.duration <= 0: issues.append({"instrument_id":asset.id,"field":"duration","issue":"non_positive"})
        if not asset.issuer or not asset.rating: issues.append({"instrument_id":asset.id,"field":"reference_data","issue":"missing"})
    flags=[]
    for asset_id in frame.columns:
        series=frame[asset_id]
        median=float(series.median())
        mad=float((series-median).abs().median())
        if mad == 0: continue
        for date, value in series.items():
            robust_z=0.6745*(float(value)-median)/mad
            if abs(robust_z) >= 3:
                flags.append({"instrument_id":asset_id,"date":date,"return":round(float(value),6),
                              "robust_z_score":round(robust_z,2)})
    return {"data_type":"synthetic","instrument_count":len(instruments),"observation_count":len(frame),
            "missing_values":missing_values,"reference_data_issues":issues,
            "return_outlier_flags":flags[:100],"outlier_method":"median absolute deviation; |robust z| >= 3"}




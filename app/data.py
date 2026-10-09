from datetime import date, timedelta
import numpy as np
from sqlalchemy import select
from .models import Instrument, PricePoint

RATINGS = ["AAA", "AA", "A", "BBB"]
RATING_FACTOR = {"AAA": 0.005, "AA": 0.007, "A": 0.010, "BBB": 0.016}
ISSUERS = ["Northstar Utilities", "Hexagon Telecom", "Alpine Bank", "Cobalt Energy", "Meridian Pharma",
           "Riviera Infrastructure", "Pioneer Consumer", "Atlas Technology", "Lumen Real Estate", "Orion Industrial"]
SECTORS = ["Utilities", "Telecom", "Financials", "Energy", "Healthcare", "Infrastructure", "Consumer", "Technology", "Real Estate", "Industrials"]

def seed_market(db):
    if db.scalar(select(Instrument.id).limit(1)):
        return
    rng = np.random.default_rng(20261009)
    for i in range(40):
        rating = RATINGS[i % len(RATINGS)]
        duration = float(rng.uniform(1.5, 11.0))
        issuer_idx = i % len(ISSUERS)
        instrument = Instrument(
            id=f"EU-CORP-{i+1:03d}", issuer=ISSUERS[issuer_idx], sector=SECTORS[issuer_idx],
            rating=rating, currency="EUR", maturity_years=round(duration + rng.uniform(0.5, 3.0), 2),
            duration=round(duration, 2), spread_duration=round(duration * rng.uniform(0.88, 1.0), 2),
            yield_pct=round(float(rng.uniform(2.0, 5.7)) + (3-RATINGS.index(rating))*0.18, 3),
            spread_bps=round(float(rng.uniform(35, 240)) + RATINGS.index(rating)*20, 1),
            liquidity_score=round(float(rng.uniform(0.35, 1.0)), 3),
            esg_score=round(float(rng.uniform(25, 95)), 1),
            capital_factor=round(RATING_FACTOR[rating] * min(duration / 5, 2.2), 5))
        db.add(instrument)
    db.flush()
    # Deterministic synthetic daily returns; never presented as observed market history.
    rng = np.random.default_rng(42)
    for i in range(40):
        for day in range(504):
            shock = rng.normal(0.00012, 0.0022 + (i % 4) * 0.0003)
            db.add(PricePoint(instrument_id=f"EU-CORP-{i+1:03d}",
                              date=(date(2024, 1, 2) + timedelta(days=day)).isoformat(),
                              total_return=float(shock)))
    db.commit()


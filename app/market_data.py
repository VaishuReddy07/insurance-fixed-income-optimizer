import csv
from datetime import datetime, timezone
from io import StringIO
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
from .config import ECB_CACHE_SECONDS, ECB_REFERENCE_ENABLED, ECB_TIMEOUT_SECONDS

SERIES_KEY = "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y"
SOURCE_URL = f"https://data-api.ecb.europa.eu/service/data/YC/{SERIES_KEY.split('.', 1)[1]}?format=csvdata&lastNObservations=30"
_cache = None

class MarketDataUnavailable(Exception):
    pass

def get_ecb_reference_rate(force_refresh=False):
    """Fetch the ECB's daily euro-area AAA 10Y sovereign spot rate (not intraday)."""
    global _cache
    if not ECB_REFERENCE_ENABLED:
        raise MarketDataUnavailable("ECB reference feed is disabled by configuration")
    now = time.monotonic()
    if not force_refresh and _cache and now - _cache["cached_at"] < ECB_CACHE_SECONDS:
        return {**_cache["payload"], "cache_status": "cached"}
    request = Request(SOURCE_URL, headers={"Accept": "text/csv", "User-Agent": "InsuranceFixedIncomePortfolioLab/1.0"})
    try:
        with urlopen(request, timeout=ECB_TIMEOUT_SECONDS) as response:
            content = response.read().decode("utf-8-sig")
        rows = csv.DictReader(StringIO(content))
        observations = [(row.get("TIME_PERIOD", ""), row.get("OBS_VALUE", "")) for row in rows]
        valid = [(date, float(value)) for date, value in observations if date and value]
        if not valid:
            raise MarketDataUnavailable("ECB response contained no valid yield observations")
        date, rate = max(valid, key=lambda item: item[0])
        payload = {
            "series_key": SERIES_KEY,
            "source": "European Central Bank Data Portal",
            "source_url": "https://data.ecb.europa.eu/data/datasets/YC",
            "instrument": "Euro area AAA sovereign 10-year spot yield curve",
            "frequency": "Daily TARGET business day; published around noon CET",
            "observation_date": date,
            "yield_pct": rate,
            "unit": "percent per annum",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "cache_status": "refreshed",
        }
        _cache = {"cached_at": now, "payload": payload}
        return payload
    except MarketDataUnavailable:
        raise
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        if _cache:
            return {**_cache["payload"], "cache_status": "stale", "warning": str(exc)}
        raise MarketDataUnavailable(f"ECB reference data is unavailable: {exc}") from exc

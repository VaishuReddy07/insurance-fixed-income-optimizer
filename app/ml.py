"""Small, reproducible Isolation Forest serving path for synthetic return data."""

from threading import Lock

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.utils import murmurhash3_32

_MODEL: IsolationForest | None = None
_MODEL_FINGERPRINT: int | None = None
_MODEL_LOCK = Lock()
CONTAMINATION = 0.01


def anomaly_model_report(frame: pd.DataFrame, limit: int = 100) -> dict:
    """Fit once per return dataset and score observations for review only."""
    global _MODEL, _MODEL_FINGERPRINT
    values = frame.to_numpy(dtype=float)
    valid_mask = np.isfinite(values)
    observations = values[valid_mask].reshape(-1, 1)
    if observations.shape[0] < 10:
        return {
            "model": "IsolationForest",
            "status": "insufficient_data",
            "training_observations": int(observations.shape[0]),
            "flags": [],
        }

    fingerprint = int(murmurhash3_32(pd.util.hash_pandas_object(frame, index=True).values.tobytes()))
    with _MODEL_LOCK:
        if _MODEL is None or _MODEL_FINGERPRINT != fingerprint:
            _MODEL = IsolationForest(
                n_estimators=100,
                contamination=CONTAMINATION,
                random_state=42,
                n_jobs=1,
            ).fit(observations)
            _MODEL_FINGERPRINT = fingerprint
        model = _MODEL

    predictions = model.predict(observations)
    anomaly_scores = -model.score_samples(observations)
    flagged = np.flatnonzero(predictions == -1)
    row_col = np.argwhere(valid_mask)
    order = flagged[np.argsort(anomaly_scores[flagged])[::-1]][:limit]
    flags = [
        {
            "date": str(frame.index[row]),
            "instrument_id": str(frame.columns[col]),
            "return": round(float(observations[idx, 0]), 6),
            "anomaly_score": round(float(anomaly_scores[idx]), 6),
        }
        for idx in order
        for row, col in [row_col[idx]]
    ]
    return {
        "model": "IsolationForest",
        "status": "ready",
        "model_version": "1",
        "training_observations": int(observations.shape[0]),
        "contamination_setting": CONTAMINATION,
        "flagged_observation_count": int(len(flagged)),
        "flags": flags,
        "intended_use": "Exploratory review of synthetic observations; not a trading, risk-limit, or regulatory decision.",
    }

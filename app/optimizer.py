import math
import numpy as np
from scipy.optimize import minimize
from .analytics import RATING_ORDER

def optimize(instruments, returns, request):
    eligible = [x for x in instruments
                if RATING_ORDER.get(x.rating, 99) <= RATING_ORDER.get(request.min_rating, 3)
                and x.liquidity_score >= request.min_liquidity
                and x.esg_score >= request.min_esg_score
                and not (request.exclude_energy and x.sector == "Energy")]
    if not eligible:
        raise ValueError("No assets satisfy the requested screens")
    n = len(eligible)
    asset_capacity = n * request.max_weight
    if asset_capacity < 1.0 - 1e-9:
        required_weight = math.ceil((1.0 / n) * 10000) / 10000
        raise ValueError(
            f"The {request.max_weight:.2%} maximum bond weight across {n} eligible bonds "
            f"allows at most {asset_capacity:.2%} invested. Raise the per-bond cap to at least "
            f"{required_weight:.2%} or broaden the eligible universe to reach 100% investment."
        )
    issuer_counts = {}
    for asset in eligible:
        issuer_counts[asset.issuer] = issuer_counts.get(asset.issuer, 0) + 1
    issuer_capacity = sum(
        min(request.max_issuer_weight, count * request.max_weight)
        for count in issuer_counts.values()
    )
    if issuer_capacity < 1.0 - 1e-9:
        raise ValueError(
            f"Issuer and bond caps together allow at most {issuer_capacity:.2%} invested. "
            "Increase a cap or broaden the eligible universe to reach 100% investment."
        )
    min_duration = min(asset.duration for asset in eligible)
    max_duration = max(asset.duration for asset in eligible)
    lower_duration = request.target_duration - request.duration_tolerance
    upper_duration = request.target_duration + request.duration_tolerance
    if max_duration < lower_duration or min_duration > upper_duration:
        raise ValueError(
            f"The requested duration band ({lower_duration:.2f}–{upper_duration:.2f} years) "
            f"does not overlap the eligible bond range ({min_duration:.2f}–{max_duration:.2f} years)."
        )
    ids = [x.id for x in eligible]
    cols = [returns[i].to_numpy() for i in ids]
    r = np.column_stack(cols)
    mu = np.array([x.yield_pct / 100 for x in eligible])
    cov = np.cov(r, rowvar=False) * 252
    cov = np.atleast_2d(cov) + np.eye(n) * 1e-8
    durations = np.array([x.duration for x in eligible])
    issuer_groups = {issuer: np.array([1.0 if x.issuer == issuer else 0.0 for x in eligible])
                     for issuer in {x.issuer for x in eligible}}
    def objective(w):
        return -(mu @ w - request.risk_aversion * float(w @ cov @ w))
    cons = [{"type": "eq", "fun": lambda w: np.sum(w)-1},
            {"type": "ineq", "fun": lambda w: durations @ w - (request.target_duration-request.duration_tolerance)},
            {"type": "ineq", "fun": lambda w: (request.target_duration+request.duration_tolerance) - durations @ w}]
    cons.extend({"type": "ineq", "fun": lambda w, g=g: request.max_issuer_weight - g @ w}
                for g in issuer_groups.values())
    result = minimize(objective, np.full(n, 1/n), method="SLSQP", bounds=[(0, request.max_weight)]*n,
                      constraints=cons, options={"maxiter": 1000, "ftol": 1e-10})
    if not result.success:
        raise ValueError(f"Optimization infeasible or did not converge: {result.message}")
    weights = {i: round(float(w), 8) for i, w in zip(ids, result.x) if w > 1e-5}
    return {"weights": weights, "objective": float(-result.fun),
            "expected_yield_pct": float(mu @ result.x * 100),
            "duration": float(durations @ result.x), "eligible_assets": n}






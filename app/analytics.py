import numpy as np

RATING_ORDER = {"AAA": 0, "AA": 1, "A": 2, "BBB": 3, "BB": 4}


def risk_report(instruments, weights, returns=None):
    ids = [x.id for x in instruments]
    w = np.array([weights.get(i, 0.0) for i in ids], dtype=float)
    duration = float(sum(x.duration * wi for x, wi in zip(instruments, w)))
    spread_duration = float(sum(x.spread_duration * wi for x, wi in zip(instruments, w)))
    concentration = {}
    for instrument, weight in zip(instruments, w):
        concentration[instrument.issuer] = concentration.get(instrument.issuer, 0.0) + float(weight)
    result = {
        "portfolio_duration": round(duration, 3),
        "spread_duration": round(spread_duration, 3),
        "issuer_concentration": {k: round(v, 4) for k, v in concentration.items() if v > 0.001},
    }
    if returns is not None and len(returns):
        available_ids = [i for i in ids if i in returns.columns]
        available_w = np.array([weights.get(i, 0.0) for i in available_ids], dtype=float)
        if available_w.sum() > 0:
            available_w /= available_w.sum()
            portfolio_daily = returns[available_ids].to_numpy() @ available_w
            result["annualized_volatility_pct"] = round(float(np.std(portfolio_daily, ddof=1) * np.sqrt(252) * 100), 3)
            result["historical_var_95_daily_pct"] = round(float(max(0.0, -np.quantile(portfolio_daily, 0.05) * 100)), 4)
            result["historical_var_99_daily_pct"] = round(float(max(0.0, -np.quantile(portfolio_daily, 0.01) * 100)), 4)
    return result


def _return_summary(daily):
    cumulative = np.cumprod(1 + daily)
    return {
        "cumulative_return_pct": round(float((cumulative[-1] - 1) * 100), 2),
        "annualized_return_pct": round(float((cumulative[-1] ** (252 / max(len(daily), 1)) - 1) * 100), 2),
        "max_drawdown_pct": round(float((cumulative / np.maximum.accumulate(cumulative) - 1).min() * 100), 2),
    }, cumulative


def performance_report(returns, weights):
    ids = [i for i in weights if i in returns.columns]
    w = np.array([weights[i] for i in ids], dtype=float)
    if not ids or w.sum() <= 0 or returns.empty:
        raise ValueError("No return history is available for the selected portfolio")
    w /= w.sum()
    portfolio_daily = returns[ids].to_numpy() @ w
    portfolio_summary, portfolio_index = _return_summary(portfolio_daily)
    benchmark_daily = returns.to_numpy().mean(axis=1)
    benchmark_summary, benchmark_index = _return_summary(benchmark_daily)
    dates = returns.index.astype(str).tolist()
    series = [
        {"date": date, "portfolio_index": round(float(p), 6), "benchmark_index": round(float(b), 6)}
        for date, p, b in zip(dates, portfolio_index, benchmark_index)
    ]
    return {
        "observations": int(len(portfolio_daily)),
        "portfolio": portfolio_summary,
        "benchmark": benchmark_summary,
        "benchmark_method": "equal-weighted synthetic universe; illustrative comparison only",
        "excess_cumulative_return_pct": round(portfolio_summary["cumulative_return_pct"] - benchmark_summary["cumulative_return_pct"], 2),
        "series": series,
    }


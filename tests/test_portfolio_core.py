"""Regression tests for the portfolio optimizer and analytics core."""

import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd
from pydantic import ValidationError

from app.analytics import performance_report, risk_report
from app.optimizer import optimize
from app.ml import anomaly_model_report
from app.main import load_returns
from app.schemas import OptimizeRequest


def make_universe():
    assets = []
    for i in range(8):
        assets.append(SimpleNamespace(
            id=f"BOND-{i}", issuer=f"ISSUER-{i // 2}",
            rating=("AAA", "AA", "A", "BBB")[i % 4],
            liquidity_score=0.7, esg_score=65.0,
            sector="Utilities" if i % 2 else "Energy",
            duration=4.0 + i * 0.25, spread_duration=3.8 + i * 0.25,
            yield_pct=3.0 + i * 0.2,
        ))
    rng = np.random.default_rng(17)
    returns = pd.DataFrame(
        rng.normal(0.0001, 0.002, size=(252, len(assets))),
        columns=[asset.id for asset in assets],
    )
    return assets, returns


class OptimizerTests(unittest.TestCase):
    def test_portfolio_obeys_investment_and_mandate_constraints(self):
        assets, returns = make_universe()
        request = OptimizeRequest(
            target_duration=5.0, duration_tolerance=1.0, min_rating="BBB",
            max_weight=0.25, max_issuer_weight=0.4,
        )
        result = optimize(assets, returns, request)
        self.assertAlmostEqual(sum(result["weights"].values()), 1.0, places=6)
        self.assertLessEqual(max(result["weights"].values()), request.max_weight + 1e-7)
        self.assertGreaterEqual(result["duration"], 4.0 - 1e-6)
        self.assertLessEqual(result["duration"], 6.0 + 1e-6)
        issuer_totals = {}
        by_id = {asset.id: asset for asset in assets}
        for instrument_id, weight in result["weights"].items():
            issuer = by_id[instrument_id].issuer
            issuer_totals[issuer] = issuer_totals.get(issuer, 0.0) + weight
        self.assertLessEqual(max(issuer_totals.values()), request.max_issuer_weight + 1e-7)

    def test_screens_remove_energy_and_low_esg_assets(self):
        assets, returns = make_universe()
        request = OptimizeRequest(
            target_duration=5.0, duration_tolerance=2.0, max_weight=0.25,
            max_issuer_weight=0.4, min_esg_score=60, exclude_energy=True,
        )
        result = optimize(assets, returns, request)
        eligible = {asset.id: asset for asset in assets if asset.sector != "Energy"}
        self.assertTrue(set(result["weights"]).issubset(eligible))
        self.assertEqual(result["eligible_assets"], len(eligible))

    def test_infeasible_weight_caps_return_a_clear_error(self):
        assets, returns = make_universe()
        request = OptimizeRequest(max_weight=0.05, max_issuer_weight=0.15)
        with self.assertRaisesRegex(ValueError, "invested|capacity|infeasible|converge"):
            optimize(assets, returns, request)

    def test_one_percent_bond_cap_explains_minimum_feasible_weight(self):
        assets, returns = make_universe()
        request = OptimizeRequest(max_weight=0.01, max_issuer_weight=0.15)
        with self.assertRaisesRegex(ValueError, "at least 12.50%"):
            optimize(assets, returns, request)
    def test_minimum_cap_is_rounded_up_not_down(self):
        assets, returns = make_universe()
        request = OptimizeRequest(min_rating="A", max_weight=0.01, max_issuer_weight=0.15)
        with self.assertRaisesRegex(ValueError, "at least 16.67%"):
            optimize(assets, returns, request)
    def test_invalid_request_limits_are_rejected(self):
        with self.assertRaises(ValidationError):
            OptimizeRequest(max_weight=0.5)


class AnalyticsTests(unittest.TestCase):
    def test_risk_and_performance_reports_are_finite(self):
        assets, returns = make_universe()
        request = OptimizeRequest(max_weight=0.25, max_issuer_weight=0.4)
        result = optimize(assets, returns, request)
        risk = risk_report(assets, result["weights"], returns)
        performance = performance_report(returns, result["weights"])
        self.assertGreaterEqual(risk["annualized_volatility_pct"], 0)
        self.assertGreaterEqual(risk["historical_var_95_daily_pct"], 0)
        self.assertGreaterEqual(risk["historical_var_99_daily_pct"], 0)
        self.assertEqual(performance["observations"], len(returns))
        self.assertEqual(len(performance["series"]), len(returns))
        self.assertTrue(np.isfinite(performance["portfolio"]["annualized_return_pct"]))
        self.assertIn("synthetic", performance["benchmark_method"])


class MlServingTests(unittest.TestCase):
    def test_isolation_forest_returns_reviewable_synthetic_flags(self):
        _, returns = make_universe()
        report = anomaly_model_report(returns)
        self.assertEqual(report["model"], "IsolationForest")
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["training_observations"], returns.size)
        self.assertGreater(report["flagged_observation_count"], 0)
        self.assertTrue(report["flags"])
        self.assertIn("synthetic", report["intended_use"])
class ReturnLoadingTests(unittest.TestCase):
    def test_quality_mode_preserves_missing_observations(self):
        class FakeResult:
            def all(self):
                return [("BOND-A", "2025-01-02", 0.01), ("BOND-B", "2025-01-03", 0.02)]
        class FakeDatabase:
            def execute(self, _statement):
                return FakeResult()

        observed = load_returns(FakeDatabase(), fill_missing=False)
        optimizer_input = load_returns(FakeDatabase(), fill_missing=True)
        self.assertEqual(int(observed.isna().sum().sum()), 2)
        self.assertEqual(int(optimizer_input.isna().sum().sum()), 0)
if __name__ == "__main__":
    unittest.main()








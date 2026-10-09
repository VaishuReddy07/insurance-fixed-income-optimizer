# Insurance Fixed-Income Portfolio Lab

A portfolio-construction and monitoring application for insurance fixed-income research. It provides a responsive dashboard, a constrained Python optimizer, SQL persistence, risk/performance analytics, data-quality monitoring, a deployed Isolation Forest anomaly-scoring endpoint, an ECB daily sovereign reference-rate feed, API-key protection, Alembic migrations, and Docker Compose deployment with PostgreSQL.

> **Important scope:** corporate bond instruments and return histories in this repository remain deterministic synthetic data. The ECB feed supplies a public daily euro-area AAA 10-year sovereign reference yield; it is not intraday data or a live corporate bond pricing feed. The capital proxy is illustrative, not an official Solvency II SCR calculation. This is a portfolio research/demo project, not an investment or regulatory reporting system.

## Run locally on Windows

Install Python 3.11 or newer, then run from this directory:

```powershell
.\run.ps1
```

It creates `.venv`, installs the requirements on first setup, and starts the service on localhost. Open:

- Dashboard: http://127.0.0.1:8000/
- Swagger API: http://127.0.0.1:8000/docs

Stop with Ctrl+C in the PowerShell window. SQLite is stored in `data/portfolio.db`.

## Run regression checks

From the project directory, run the optimizer and analytics checks with:

```powershell
python -m unittest discover -s tests -v
```

## Run with PostgreSQL and Docker

1. Copy `.env.example` to `.env`.
2. Replace both values with different random hexadecimal strings (at least 32 characters). Keep `.env` private and out of source control.
3. Run:

```powershell
docker compose up --build
```

The application waits for PostgreSQL health, applies the Alembic schema migration, and seeds the example universe. The database is persisted in a named Docker volume. The dashboard/API are bound to `127.0.0.1:8000`; enter the configured API key in the dashboard and select **Use key for this tab**. The same bearer key is available through the Swagger **Authorize** button. Follow logs with `docker compose logs -f app`; stop with `docker compose down` (do not add `-v` if you want to retain the database volume).

The Compose file is a secure local deployment baseline. For a publicly reachable service, place it behind an HTTPS reverse proxy, use managed secrets, restrict network ingress, and add the organization's identity provider and operational monitoring.

## Dashboard workflow

1. Set duration, rating floor, bond and issuer limits, liquidity/ESG screens, and risk aversion.
2. Select **Run portfolio optimization**.
3. Review holdings, exposure, risk, capital proxy, performance versus the equal-weight synthetic benchmark, and data-quality flags.
4. Download the holdings as CSV or change constraints and run another optimization.

## API endpoints

- `GET /api/v1/health` — database readiness and synthetic universe count
- `GET /api/v1/universe` — example bond universe
- `POST /api/v1/optimize` — create and persist a constrained portfolio
- `GET /api/v1/portfolio/current` — latest portfolio holdings
- `GET /api/v1/analytics/risk` — duration, spread duration, annualized volatility, historical VaR, issuer concentration
- `GET /api/v1/analytics/capital` — explicitly illustrative spread-risk proxy
- `GET /api/v1/analytics/performance` — portfolio/benchmark summaries and cumulative chart series
- `GET /api/v1/analytics/quality` — reference-data checks and robust MAD outlier flags
- `GET /api/v1/analytics/ml-anomalies` — cached Isolation Forest inference over synthetic return observations; flags require human review
- `GET /api/v1/market-data/ecb-reference` — latest ECB euro-area AAA 10-year spot yield observation (cached for 15 minutes)

## Data and model assumptions

The ECB observation is sourced from the ECB Data Portal series `YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y`. The series is published daily on TARGET business days, around noon CET, and represents the ECB's Svensson-model euro-area AAA government bond 10-year spot yield. It is shown separately as a reference rate; it does not replace synthetic corporate bond fields in the optimizer. The application caches responses in memory and returns the last cached observation marked stale if the source is temporarily unavailable. [ECB series catalogue](https://data.ecb.europa.eu/data/datasets/YC) · [ECB SDMX web services](https://data.ecb.europa.eu/help/getting-data-web-services-sdmx-0) · [ECB yield curve methodology](https://www.ecb.europa.eu/stats/financial_markets_and_interest_rates/euro_area_yield_curves/shared/pdf/technical_notes.pdf).

The optimizer maximizes expected yield less a variance penalty subject to full investment, per-asset and issuer limits, duration band, rating floor, liquidity floor, ESG screen, and optional energy exclusion. Security returns are synthetic. The performance benchmark is equal-weighted across the synthetic universe, not an investable index. VaR is historical simulation over the generated return series. Quality flags use median absolute deviation and require human review.

The Isolation Forest endpoint trains an in-process model from the deterministic synthetic return history and caches it until the input history changes. Its flags are exploratory review prompts; they are not a trading signal, risk limit, or validated model. The capital output is not a standard-formula implementation. EIOPA's spread sub-module depends on regulatory credit quality steps, modified duration, and applicable exposure rules; total SCR also requires other risk modules and aggregation. See [EIOPA Delegated Regulation 2015/35, Article 176](https://www.eiopa.europa.eu/rulebook/solvency-ii-single-rulebook/article-5796_en) and [Article 175](https://www.eiopa.europa.eu/rulebook/solvency-ii-single-rulebook/article-5795_en). The proxy must not be used for regulatory decisions or described as validated capital.

## Remaining prerequisites for an employer-grade production system

The app is now packaged and can run with PostgreSQL, migrations, and API-key protection, but real deployment still requires employer/vendor access and governance:

- Licensed intraday bond prices, ratings, identifier mapping, reference data, entitlements, and a vendor-specific adapter (Bloomberg or approved alternative).
- Risk-team specification and independent validation of Solvency II credit-quality mapping, stresses, exclusions, concentration, aggregation, matching-adjustment treatment, and reporting controls.
- Organization SSO/roles, TLS termination, managed secrets, network policy, backups/recovery, monitoring/alerting, CI/CD, vulnerability management, and operations ownership.
- Model approval, data lineage/retention, and client-specific mandate governance.

These are integration and approval dependencies, not features that can responsibly be fabricated from public synthetic data.

## Resume description

**Built a Python/FastAPI and PostgreSQL-backed insurance fixed-income portfolio research application with constrained optimization, duration/spread risk, VaR, ESG/liquidity screens, Isolation Forest anomaly scoring, data-quality alerts, an ECB reference yield feed, API-key protection, schema migrations, Docker deployment, and a responsive dashboard.**

State clearly that the corporate universe and returns are synthetic, the ECB series is daily, and the capital output is illustrative.




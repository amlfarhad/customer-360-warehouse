# Customer 360 Warehouse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone analytics engineering portfolio project that transforms messy SaaS CRM, billing, product usage, support, and marketing data into tested Customer 360, churn risk, revenue retention, and product adoption marts with executive reports and dashboard output.

**Architecture:** The project is a local warehouse platform. `src/generate_data.py` creates deterministic raw CSVs, `src/build_warehouse.py` loads raw data into DuckDB and executes SQL models, `src/run_quality_checks.py` validates source and mart quality, `src/write_readout.py` produces business-facing artifacts, and `src/cli.py` exposes repeatable commands.

**Tech Stack:** Python, Pandas, DuckDB, SQL, Plotly, Pytest, Markdown, static HTML dashboard.

---

## File Structure

- `requirements.txt`: runtime and test dependencies.
- `README.md`: clone/run story, architecture, metrics, and portfolio bullet.
- `src/generate_data.py`: synthetic SaaS source systems.
- `src/build_warehouse.py`: raw table loading and SQL model runner.
- `src/run_quality_checks.py`: reusable quality checks and audit serialization.
- `src/write_readout.py`: Markdown, JSON, and HTML dashboard artifacts.
- `src/cli.py`: `generate-data`, `build-warehouse`, `quality-audit`, `write-readout`, and `demo` commands.
- `models/staging/*.sql`: cleaned source tables.
- `models/dimensions/*.sql`: customer, account, date, and plan dimensions.
- `models/facts/*.sql`: usage, revenue, support, and pipeline facts.
- `models/marts/*.sql`: customer health, churn risk, revenue retention, product adoption, and account summary marts.
- `tests/`: TDD coverage for every platform layer.
- `docs/`: architecture, data model, quality rules, metrics, and portfolio positioning.

## Execution Tasks

1. Initialize a git repository and Python project skeleton.
2. Write failing tests for source generation, warehouse build, quality audit, readout/dashboard output, and CLI demo.
3. Implement deterministic synthetic data generation for CRM, billing, product, support, and marketing sources.
4. Implement DuckDB warehouse builder with staging, dimensions, facts, and marts.
5. Implement quality audit checks and structured output.
6. Implement readout/dashboard/reporting layer.
7. Implement CLI workflow.
8. Generate sample artifacts.
9. Write README and docs.
10. Run full tests and commit.

## Acceptance Criteria

- `python -m src.cli demo --workspace . --seed 42 --accounts 500` runs end to end.
- Raw CSVs exist under `data/raw/`.
- DuckDB warehouse builds under `data/warehouse/customer360.duckdb`.
- Marts exist: `mart_customer_health`, `mart_churn_risk`, `mart_revenue_retention`, `mart_product_adoption`, `mart_account_summary`.
- Quality audit writes JSON and Markdown.
- Readout writes `reports/customer_health_readout.md`.
- Dashboard writes `reports/dashboard.html`.
- Tests pass with `pytest -q`.
- README makes the project legible as an analytics engineering portfolio artifact.

## Self-Review

Spec coverage:

- Synthetic messy source systems are covered.
- Warehouse layers and marts are covered.
- Data quality rules are covered.
- Dashboard and readout outputs are covered.
- Portfolio positioning is covered.

Plan hygiene scan:

- No undefined implementation gaps are present.

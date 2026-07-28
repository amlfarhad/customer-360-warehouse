# Customer Analytics Warehouse

End-to-end analytics engineering project for SaaS customer health, churn risk, revenue retention, and product adoption.

This project turns messy CRM, billing, product usage, support, and marketing data into a trusted local DuckDB warehouse with dimensions, facts, marts, data quality checks, executive readouts, and an interactive dashboard.

## Platform Capabilities

Customer 360 is a familiar business problem across SaaS, fintech, healthcare, marketplaces, and B2B operations. It proves the core analytics engineering workflow:

- ingest messy operational data
- clean raw sources into staging models
- model dimensions and facts
- build business marts
- test data quality
- produce stakeholder-ready outputs

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m src.cli demo --workspace . --accounts 500 --seed 42
```

The demo writes:

- `data/raw/*.csv`
- `data/warehouse/customer360.duckdb`
- `reports/data_quality_audit.json`
- `reports/data_quality_audit.md`
- `reports/customer_health_readout.md`
- `reports/dashboard.html`

## CLI

```bash
python3 -m src.cli generate-data --workspace .
python3 -m src.cli build-warehouse --workspace .
python3 -m src.cli quality-audit --workspace .
python3 -m src.cli write-readout --workspace .
python3 -m src.cli demo --workspace .
```

## Warehouse Marts

- `mart_customer_health`
- `mart_churn_risk`
- `mart_revenue_retention`
- `mart_product_adoption`
- `mart_account_summary`

## Quality Checks

- duplicate CRM accounts
- missing company size
- invalid lifecycle values
- negative invoice amounts
- subscription date errors
- null product event names
- health/churn score bounds
- revenue-account relationship integrity

## Reports

Sample outputs:

- [`reports/customer_health_readout.md`](reports/customer_health_readout.md)
- [`reports/data_quality_audit.md`](reports/data_quality_audit.md)
- `reports/dashboard.html`

## Tests

```bash
python3 -m pytest tests -q
```

## Portfolio Summary

Built a Customer 360 analytics warehouse using Python, SQL, and DuckDB, integrating CRM, billing, product usage, support, and marketing data into tested revenue retention, churn risk, product adoption, and customer health marts with an executive dashboard and data quality audit.

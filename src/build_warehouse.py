"""Build the Customer 360 DuckDB warehouse."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb


RAW_TABLES = {
    "crm_accounts": "crm_accounts.csv",
    "crm_contacts": "crm_contacts.csv",
    "crm_opportunities": "crm_opportunities.csv",
    "billing_subscriptions": "billing_subscriptions.csv",
    "billing_invoices": "billing_invoices.csv",
    "product_events": "product_events.csv",
    "support_tickets": "support_tickets.csv",
    "marketing_leads": "marketing_leads.csv",
}

MODEL_ORDER = [
    "staging/stg_crm_accounts.sql",
    "staging/stg_crm_contacts.sql",
    "staging/stg_crm_opportunities.sql",
    "staging/stg_billing_subscriptions.sql",
    "staging/stg_billing_invoices.sql",
    "staging/stg_product_events.sql",
    "staging/stg_support_tickets.sql",
    "staging/stg_marketing_leads.sql",
    "dimensions/dim_accounts.sql",
    "dimensions/dim_customers.sql",
    "dimensions/dim_plans.sql",
    "dimensions/dim_date.sql",
    "facts/fct_product_usage_daily.sql",
    "facts/fct_subscription_revenue.sql",
    "facts/fct_support_tickets.sql",
    "facts/fct_pipeline_opportunities.sql",
    "marts/mart_account_summary.sql",
    "marts/mart_customer_health.sql",
    "marts/mart_churn_risk.sql",
    "marts/mart_revenue_retention.sql",
    "marts/mart_product_adoption.sql",
]


@dataclass(frozen=True)
class WarehouseBuildResult:
    """Warehouse build result."""

    db_path: Path
    raw_tables: list[str]
    tables_built: list[str]


def _model_root() -> Path:
    return Path(__file__).resolve().parents[1] / "models"


def build_warehouse(raw_dir: str | Path, db_path: str | Path) -> WarehouseBuildResult:
    """Load raw CSVs and execute warehouse SQL models."""

    raw_path = Path(raw_dir)
    database_path = Path(db_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    raw_tables = []
    tables_built = []

    with duckdb.connect(str(database_path)) as con:
        for table_name, filename in RAW_TABLES.items():
            csv_path = raw_path / filename
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing raw source file: {csv_path}")
            con.execute(
                f"create or replace table {table_name} as select * from read_csv_auto(?, header=true)",
                [str(csv_path)],
            )
            raw_tables.append(table_name)

        for model in MODEL_ORDER:
            sql_path = _model_root() / model
            con.execute(sql_path.read_text())
            tables_built.append(sql_path.stem)

    return WarehouseBuildResult(db_path=database_path, raw_tables=raw_tables, tables_built=tables_built)


def list_tables(db_path: str | Path) -> list[str]:
    """List DuckDB tables."""

    with duckdb.connect(str(db_path), read_only=True) as con:
        rows = con.execute("show tables").fetchall()
    return sorted(row[0] for row in rows)

"""Export a decision-workspace payload from the verified DuckDB marts.

The static UI intentionally consumes this generated JSON rather than carrying
business numbers in JavaScript. Re-running the existing demo pipeline and this
exporter reproduces the sample workspace.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.run_quality_checks import QualityAudit


METRIC_DICTIONARY: list[dict[str, str]] = [
    {
        "name": "Customer health",
        "field": "health_score",
        "classification": "heuristic",
        "definition": "A 0–100 rule-based score built from product events, recognized revenue, support burden, failed invoices, and lifecycle stage.",
        "source": "mart_customer_health",
        "caveat": "This is not an ML model or a validated churn probability.",
    },
    {
        "name": "Churn risk",
        "field": "churn_risk_score",
        "classification": "heuristic",
        "definition": "A 0–100 rule-based risk score derived from the health score with billing, high-priority support, and churned-lifecycle adjustments.",
        "source": "mart_churn_risk",
        "caveat": "The repository contains no model-derived churn signal.",
    },
    {
        "name": "Recognized revenue",
        "field": "recognized_revenue",
        "classification": "observed",
        "definition": "Invoice amount counted only when invoice status is paid and amount is positive.",
        "source": "fct_subscription_revenue",
        "caveat": "The source generator intentionally includes negative invoice amounts and failed invoices.",
    },
    {
        "name": "Failed invoice amount",
        "field": "failed_invoice_amount",
        "classification": "observed",
        "definition": "Invoice amount attached to records whose billing status is failed.",
        "source": "fct_subscription_revenue",
        "caveat": "Review the quality audit before using this for automated collections decisions.",
    },
    {
        "name": "Feature variety",
        "field": "avg_daily_features",
        "classification": "observed",
        "definition": "Average number of distinct non-null event names used by an account per active usage day.",
        "source": "fct_product_usage_daily",
        "caveat": "Null event names are retained in the audit and excluded from distinct feature counts.",
    },
    {
        "name": "Adoption rate",
        "field": "adoption_rate",
        "classification": "observed",
        "definition": "Accounts with at least one event for a feature divided by modeled accounts in the segment.",
        "source": "mart_product_adoption",
        "caveat": "Event presence is a usage proxy, not proof of business value.",
    },
    {
        "name": "Gross revenue retention",
        "field": "gross_revenue_retention",
        "classification": "observed",
        "definition": "One minus churned recognized revenue divided by recognized revenue, grouped by segment and plan.",
        "source": "mart_revenue_retention",
        "caveat": "This demo does not model expansion, contraction, or renewal cohorts.",
    },
]


LINEAGE: list[dict[str, str]] = [
    {
        "signal": "Account identity and lifecycle",
        "source": "crm_accounts.csv → stg_crm_accounts → dim_accounts",
        "logic": "Duplicate account IDs are reduced to the latest created_at record in staging.",
    },
    {
        "signal": "Recognized revenue and billing pressure",
        "source": "billing_invoices.csv → stg_billing_invoices → fct_subscription_revenue",
        "logic": "Paid positive invoices contribute recognized_revenue; failed invoices contribute failed_invoice_amount.",
    },
    {
        "signal": "Product activity and feature variety",
        "source": "product_events.csv → stg_product_events → fct_product_usage_daily",
        "logic": "Events are grouped by account and usage date; null event names remain visible to quality checks.",
    },
    {
        "signal": "Support burden",
        "source": "support_tickets.csv → stg_support_tickets → fct_support_tickets",
        "logic": "High and urgent tickets are marked as high priority and summarized by account.",
    },
    {
        "signal": "Customer health",
        "source": "mart_account_summary → mart_customer_health",
        "logic": "The existing 0–100 formula combines observed account, usage, revenue, support, billing, and lifecycle inputs.",
    },
    {
        "signal": "Churn risk",
        "source": "mart_customer_health → mart_churn_risk",
        "logic": "The existing 0–100 formula adds deterministic billing, high-priority support, and churned-lifecycle adjustments.",
    },
]


def _key(value: Any) -> str:
    """Return a stable JSON object key for account IDs."""

    cleaned = _clean(value)
    if isinstance(cleaned, float) and cleaned.is_integer():
        return str(int(cleaned))
    return str(cleaned)


def _clean(value: Any) -> Any:
    """Convert pandas/numpy/date values into JSON-safe primitives."""

    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to clean JSON records."""

    return [_clean(row) for row in frame.to_dict(orient="records")]


def _group_records(
    frame: pd.DataFrame,
    key_column: str = "account_id",
    date_column: str | None = None,
    limit: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Group source records by account ID, optionally keeping recent rows."""

    if frame.empty:
        return {}
    ordered = frame.copy()
    sort_columns = [key_column]
    ascending = [True]
    if date_column and date_column in ordered.columns:
        sort_columns.append(date_column)
        ascending.append(False)
    secondary_columns = [column for column in ordered.columns if column not in sort_columns]
    if not date_column and "events" in secondary_columns:
        sort_columns.append("events")
        ascending.append(False)
        secondary_columns.remove("events")
    sort_columns.extend(sorted(secondary_columns))
    ascending.extend([True] * len(secondary_columns))
    ordered = ordered.sort_values(sort_columns, ascending=ascending, na_position="last", kind="mergesort")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for account_id, group in ordered.groupby(key_column, dropna=False, sort=False):
        selected = group.head(limit) if limit else group
        grouped[_key(account_id)] = _records(selected)
    return grouped


def _query(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    """Run a read-only query and return a DataFrame."""

    return con.execute(sql).fetchdf()


def _attention_reasons(row: pd.Series) -> list[dict[str, str]]:
    """Explain an account's queue position using observed facts and heuristics."""

    reasons: list[dict[str, str]] = []
    lifecycle = str(row.get("lifecycle_stage") or "")
    failed_amount = float(row.get("failed_invoice_amount") or 0)
    high_priority = int(row.get("high_priority_tickets") or 0)
    features = float(row.get("avg_daily_features") or 0)
    segment_median = float(row.get("segment_median_features") or 0)
    health = float(row.get("health_score") or 0)

    if lifecycle == "churned":
        reasons.append(
            {
                "label": "Lifecycle is churned",
                "type": "observed",
                "source": "CRM lifecycle_stage",
                "detail": "The CRM record is marked churned; treat this as a recovery or closed-loop review, not a prediction.",
            }
        )
    if failed_amount > 0:
        reasons.append(
            {
                "label": "Billing needs review",
                "type": "observed",
                "source": "fct_subscription_revenue",
                "detail": f"${failed_amount:,.0f} is attached to failed invoice records.",
            }
        )
    if high_priority > 0:
        reasons.append(
            {
                "label": "High-priority support load",
                "type": "observed",
                "source": "fct_support_tickets",
                "detail": f"{high_priority} high or urgent ticket(s) are recorded.",
            }
        )
    if features < segment_median:
        reasons.append(
            {
                "label": "Below segment feature variety",
                "type": "heuristic",
                "source": "fct_product_usage_daily",
                "detail": f"{features:.1f} average daily features versus a {segment_median:.1f} segment median.",
            }
        )
    if not reasons and health < 50:
        reasons.append(
            {
                "label": "Low composite health",
                "type": "heuristic",
                "source": "mart_customer_health",
                "detail": "The existing rule-based health score is below 50 on a 0–100 scale.",
            }
        )
    if not reasons:
        reasons.append(
            {
                "label": "Monitor",
                "type": "heuristic",
                "source": "mart_customer_health",
                "detail": "No specific observed exception is present in the current source records.",
            }
        )
    return reasons[:4]


def _source_coverage(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Return row counts and observed date ranges for the raw source tables."""

    specs = [
        ("CRM accounts", "crm_accounts", "created_at"),
        ("CRM contacts", "crm_contacts", "created_at"),
        ("CRM opportunities", "crm_opportunities", "created_at"),
        ("Billing subscriptions", "billing_subscriptions", "started_at"),
        ("Billing invoices", "billing_invoices", "invoice_date"),
        ("Product events", "product_events", "event_at"),
        ("Support tickets", "support_tickets", "created_at"),
        ("Marketing leads", "marketing_leads", "created_at"),
    ]
    coverage: list[dict[str, Any]] = []
    for label, table, date_column in specs:
        row = con.execute(
            f"select count(*) as row_count, min(cast({date_column} as timestamp)) as coverage_start, "
            f"max(cast({date_column} as timestamp)) as coverage_end from {table}"
        ).fetchone()
        coverage.append(
            {
                "source": label,
                "table": table,
                "row_count": int(row[0] or 0),
                "coverage_start": _clean(row[1]),
                "coverage_end": _clean(row[2]),
            }
        )
    return coverage


def build_workspace_payload(db_path: str | Path, audit: QualityAudit, seed: int = 42) -> dict[str, Any]:
    """Build the complete static payload from existing warehouse tables."""

    with duckdb.connect(str(db_path), read_only=True) as con:
        queue = _query(
            con,
            """
            select
                h.account_id,
                h.account_name,
                h.industry,
                h.region,
                h.segment,
                h.lifecycle_stage,
                h.company_size,
                h.plan,
                h.subscription_status,
                h.total_events,
                h.avg_daily_features,
                h.recognized_revenue,
                h.failed_invoice_amount,
                h.support_tickets,
                h.high_priority_tickets,
                h.avg_resolved_hours,
                h.health_score,
                c.churn_risk_score,
                c.churn_risk_band
            from mart_customer_health h
            join mart_churn_risk c using (account_id)
            """,
        )
        queue["segment_median_features"] = queue.groupby("segment")["avg_daily_features"].transform("median")
        queue["attention_reasons"] = queue.apply(_attention_reasons, axis=1)
        queue["primary_reason"] = queue["attention_reasons"].apply(lambda values: values[0]["label"])
        queue["signal_classification"] = "heuristic"
        queue = queue.sort_values(["churn_risk_score", "recognized_revenue"], ascending=[False, False])

        kpis = _query(
            con,
            """
            select
                count(*) as accounts,
                avg(h.health_score) as average_health,
                avg(c.churn_risk_score) as average_churn_risk,
                sum(h.recognized_revenue) as recognized_revenue,
                sum(case when c.churn_risk_band in ('high', 'already_churned') then 1 else 0 end) as attention_accounts,
                sum(case when h.lifecycle_stage = 'customer' then 1 else 0 end) as active_customers
            from mart_customer_health h
            join mart_churn_risk c using (account_id)
            """,
        )
        segments = _query(
            con,
            """
            select
                h.segment,
                count(*) as accounts,
                avg(h.health_score) as average_health,
                avg(c.churn_risk_score) as average_churn_risk,
                sum(h.recognized_revenue) as recognized_revenue,
                sum(case when c.churn_risk_band in ('high', 'already_churned') then 1 else 0 end) as attention_accounts
            from mart_customer_health h
            join mart_churn_risk c using (account_id)
            group by h.segment
            order by recognized_revenue desc
            """,
        )
        lifecycle = _query(
            con,
            """
            select lifecycle_stage, count(*) as accounts, avg(health_score) as average_health
            from mart_customer_health
            group by lifecycle_stage
            order by accounts desc
            """,
        )
        adoption = _query(con, "select * from mart_product_adoption order by segment, adoption_rate desc nulls last")
        retention = _query(con, "select * from mart_revenue_retention order by recognized_revenue desc")

        crm_records = _group_records(_query(con, "select * from dim_accounts"), limit=1)
        customer_records = _group_records(_query(con, "select * from dim_customers"), limit=1)
        invoice_records = _group_records(
            _query(con, "select * from fct_subscription_revenue order by invoice_date desc"),
            date_column="invoice_date",
            limit=8,
        )
        support_records = _group_records(
            _query(con, "select * from fct_support_tickets order by ticket_date desc"),
            date_column="ticket_date",
            limit=8,
        )
        product_records = _group_records(
            _query(con, "select * from stg_product_events order by event_at desc"),
            date_column="event_at",
            limit=8,
        )
        opportunity_records = _group_records(
            _query(con, "select * from fct_pipeline_opportunities order by created_at desc"),
            date_column="created_at",
            limit=6,
        )
        usage_trend = _group_records(
            _query(
                con,
                """
                select
                    account_id,
                    strftime(usage_date, '%Y-%m') as month,
                    sum(events) as events,
                    avg(distinct_features_used) as average_features,
                    sum(integration_syncs) as integration_syncs,
                    sum(report_exports) as report_exports
                from fct_product_usage_daily
                group by account_id, month
                order by month desc
                """,
            ),
            date_column="month",
        )
        revenue_trend = _group_records(
            _query(
                con,
                """
                select
                    account_id,
                    strftime(invoice_date, '%Y-%m') as month,
                    sum(recognized_revenue) as recognized_revenue,
                    sum(failed_invoice_amount) as failed_invoice_amount,
                    count(*) as invoice_count
                from fct_subscription_revenue
                group by account_id, month
                order by month desc
                """,
            ),
            date_column="month",
        )
        support_trend = _group_records(
            _query(
                con,
                """
                select
                    account_id,
                    strftime(ticket_date, '%Y-%m') as month,
                    count(*) as tickets,
                    sum(is_high_priority) as high_priority_tickets,
                    avg(resolved_hours) as average_resolved_hours
                from fct_support_tickets
                group by account_id, month
                order by month desc
                """,
            ),
            date_column="month",
        )
        adoption_by_account = _group_records(
            _query(
                con,
                """
                select account_id, event_name, count(*) as events,
                       min(event_at) as first_seen, max(event_at) as last_seen
                from stg_product_events
                where event_name is not null
                group by account_id, event_name
                order by events desc
                """,
            ),
            limit=12,
        )
        source_coverage = _source_coverage(con)

    queue_records = _records(queue.drop(columns=["segment_median_features"]))
    queue_by_id = {_key(row["account_id"]): row for row in queue_records}
    account_details: dict[str, Any] = {}
    for account_id, account in queue_by_id.items():
        account_details[account_id] = {
            "account": account,
            "records": {
                "crm": crm_records.get(account_id, []),
                "customer": customer_records.get(account_id, []),
                "invoices": invoice_records.get(account_id, []),
                "support": support_records.get(account_id, []),
                "product": product_records.get(account_id, []),
                "opportunities": opportunity_records.get(account_id, []),
            },
            "trends": {
                "usage": usage_trend.get(account_id, []),
                "revenue": revenue_trend.get(account_id, []),
                "support": support_trend.get(account_id, []),
            },
            "adoption": adoption_by_account.get(account_id, []),
        }

    kpi_row = _records(kpis)[0]
    meta = {
        "schema_version": 1,
        "synthetic": True,
        "seed": seed,
        "accounts": int(kpi_row["accounts"]),
        "generated_from": [
            "src/generate_data.py",
            "src/build_warehouse.py",
            "models/marts/*.sql",
            "src/run_quality_checks.py",
        ],
        "source_note": "Synthetic deterministic demo data. No production usage, customer outcomes, revenue impact, or model validation is claimed.",
        "model_note": "No ML model is present in this repository. Health and churn risk are deterministic heuristic scores from the existing SQL marts.",
        "action_note": "Saved next actions are local to this browser. Exported briefs are generated from the same sample payload.",
        "repository_url": "https://github.com/amlfarhad/customer-analytics-warehouse",
    }

    return {
        "meta": meta,
        "kpis": kpi_row,
        "queue": queue_records,
        "segments": _records(segments),
        "lifecycle": _records(lifecycle),
        "adoption": _records(adoption),
        "retention": _records(retention),
        "accounts": account_details,
        "quality": audit.to_dict(),
        "source_coverage": source_coverage,
        "metric_dictionary": METRIC_DICTIONARY,
        "lineage": LINEAGE,
    }


def write_decision_workspace(
    db_path: str | Path,
    audit: QualityAudit,
    output_path: str | Path,
    seed: int = 42,
) -> Path:
    """Write a reproducible static decision-workspace JSON payload."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_workspace_payload(db_path=db_path, audit=audit, seed=seed)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path

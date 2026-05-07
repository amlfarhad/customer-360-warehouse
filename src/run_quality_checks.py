"""Data quality checks for the Customer 360 warehouse."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb
import pandas as pd


@dataclass(frozen=True)
class QualityCheck:
    """A single quality check result."""

    name: str
    status: str
    severity: str
    observed: float
    threshold: float
    detail: str


@dataclass(frozen=True)
class QualitySummary:
    """Quality audit summary."""

    total_checks: int
    passed: int
    warnings: int
    failed: int
    status: str


@dataclass(frozen=True)
class QualityAudit:
    """Structured quality audit."""

    summary: QualitySummary
    checks: list[QualityCheck]

    def to_dict(self) -> dict[str, object]:
        return {"summary": asdict(self.summary), "checks": [asdict(check) for check in self.checks]}


def _check(name: str, fail: bool, observed: float, threshold: float, detail: str, severity: str = "critical") -> QualityCheck:
    status = "fail" if fail and severity == "critical" else "warn" if fail else "pass"
    return QualityCheck(name=name, status=status, severity=severity, observed=observed, threshold=threshold, detail=detail)


def run_quality_audit(raw_dir: str | Path, db_path: str | Path) -> QualityAudit:
    """Run source and mart data quality checks."""

    raw_path = Path(raw_dir)
    accounts = pd.read_csv(raw_path / "crm_accounts.csv")
    invoices = pd.read_csv(raw_path / "billing_invoices.csv")
    subscriptions = pd.read_csv(raw_path / "billing_subscriptions.csv")
    events = pd.read_csv(raw_path / "product_events.csv")

    checks: list[QualityCheck] = []

    duplicate_accounts = int(accounts["account_id"].duplicated().sum())
    checks.append(
        _check(
            "duplicate_crm_accounts",
            duplicate_accounts > 0,
            duplicate_accounts,
            0,
            f"{duplicate_accounts} duplicate account_id values found in CRM accounts.",
        )
    )

    missing_company_size = int(accounts["company_size"].isna().sum())
    checks.append(
        _check(
            "missing_company_size",
            missing_company_size > 0,
            missing_company_size,
            0,
            f"{missing_company_size} CRM accounts are missing company_size.",
            severity="warning",
        )
    )

    invalid_lifecycle = int((~accounts["lifecycle_stage"].isin(["lead", "trial", "customer", "churned"])).sum())
    checks.append(
        _check(
            "accepted_lifecycle_values",
            invalid_lifecycle > 0,
            invalid_lifecycle,
            0,
            f"{invalid_lifecycle} accounts have invalid lifecycle_stage values.",
        )
    )

    negative_invoice_amount = int((invoices["amount"] < 0).sum())
    checks.append(
        _check(
            "negative_invoice_amount",
            negative_invoice_amount > 0,
            negative_invoice_amount,
            0,
            f"{negative_invoice_amount} invoices have negative amount values.",
        )
    )

    subscription_dates = subscriptions.copy()
    subscription_dates["started_at"] = pd.to_datetime(subscription_dates["started_at"], errors="coerce")
    subscription_dates["ended_at"] = pd.to_datetime(subscription_dates["ended_at"], errors="coerce")
    end_before_start = int((subscription_dates["ended_at"] < subscription_dates["started_at"]).sum())
    checks.append(
        _check(
            "subscription_end_before_start",
            end_before_start > 0,
            end_before_start,
            0,
            f"{end_before_start} subscriptions end before they start.",
        )
    )

    null_event_names = int(events["event_name"].isna().sum())
    checks.append(
        _check(
            "null_product_event_names",
            null_event_names > 0,
            null_event_names,
            0,
            f"{null_event_names} product events have null event_name.",
            severity="warning",
        )
    )

    with duckdb.connect(str(db_path), read_only=True) as con:
        health_rows = int(con.execute("select count(*) from mart_customer_health").fetchone()[0])
        churn_bounds = int(
            con.execute(
                "select count(*) from mart_churn_risk where churn_risk_score < 0 or churn_risk_score > 100"
            ).fetchone()[0]
        )
        health_bounds = int(
            con.execute("select count(*) from mart_customer_health where health_score < 0 or health_score > 100").fetchone()[0]
        )
        orphan_revenue = int(
            con.execute(
                """
                select count(*)
                from fct_subscription_revenue r
                left join dim_accounts a on r.account_id = a.account_id
                where a.account_id is null
                """
            ).fetchone()[0]
        )

    checks.append(_check("mart_customer_health_rows", health_rows == 0, health_rows, 1, f"{health_rows} customer health rows built."))
    checks.append(_check("churn_score_bounds", churn_bounds > 0, churn_bounds, 0, f"{churn_bounds} churn scores outside 0-100."))
    checks.append(_check("health_score_bounds", health_bounds > 0, health_bounds, 0, f"{health_bounds} health scores outside 0-100."))
    checks.append(_check("revenue_account_relationship", orphan_revenue > 0, orphan_revenue, 0, f"{orphan_revenue} revenue rows lack a valid account."))

    failed = sum(1 for check in checks if check.status == "fail")
    warnings = sum(1 for check in checks if check.status == "warn")
    status = "fail" if failed else "warn" if warnings else "pass"
    summary = QualitySummary(
        total_checks=len(checks),
        passed=sum(1 for check in checks if check.status == "pass"),
        warnings=warnings,
        failed=failed,
        status=status,
    )
    return QualityAudit(summary=summary, checks=checks)

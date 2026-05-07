# Data Quality Audit

Overall status: **FAIL**

| Check | Status | Severity | Observed | Threshold | Detail |
|---|---:|---:|---:|---:|---|
| duplicate_crm_accounts | FAIL | critical | 5 | 0 | 5 duplicate account_id values found in CRM accounts. |
| missing_company_size | WARN | warning | 32 | 0 | 32 CRM accounts are missing company_size. |
| accepted_lifecycle_values | PASS | critical | 0 | 0 | 0 accounts have invalid lifecycle_stage values. |
| negative_invoice_amount | FAIL | critical | 22 | 0 | 22 invoices have negative amount values. |
| subscription_end_before_start | FAIL | critical | 1 | 0 | 1 subscriptions end before they start. |
| null_product_event_names | WARN | warning | 69 | 0 | 69 product events have null event_name. |
| mart_customer_health_rows | PASS | critical | 500 | 1 | 500 customer health rows built. |
| churn_score_bounds | PASS | critical | 0 | 0 | 0 churn scores outside 0-100. |
| health_score_bounds | PASS | critical | 0 | 0 | 0 health scores outside 0-100. |
| revenue_account_relationship | PASS | critical | 0 | 0 | 0 revenue rows lack a valid account. |

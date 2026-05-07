# Quality Rules

The project intentionally generates messy source data so the audit layer can demonstrate realistic checks.

## Source Checks

- Duplicate CRM account IDs
- Missing company size
- Accepted lifecycle values
- Negative invoice amounts
- Subscription end date before start date
- Null product event names

## Mart Checks

- Customer health mart row count
- Churn score bounds between 0 and 100
- Health score bounds between 0 and 100
- Revenue rows must map to valid accounts

## Severity

- `critical`: should block automated decisioning.
- `warning`: should be reviewed before stakeholder reporting.

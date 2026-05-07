# Data Model

## Source Systems

- `crm_accounts`
- `crm_contacts`
- `crm_opportunities`
- `billing_subscriptions`
- `billing_invoices`
- `product_events`
- `support_tickets`
- `marketing_leads`

## Dimensions

- `dim_accounts`: account firmographics and lifecycle.
- `dim_customers`: account plus subscription context.
- `dim_plans`: plan metadata.
- `dim_date`: calendar spine.

## Facts

- `fct_product_usage_daily`: daily account-level product activity.
- `fct_subscription_revenue`: invoice-level revenue and failed billing.
- `fct_support_tickets`: support burden and urgency.
- `fct_pipeline_opportunities`: sales pipeline and closed revenue.

## Marts

- `mart_account_summary`: wide customer/account metric base.
- `mart_customer_health`: 0-100 customer health score.
- `mart_churn_risk`: 0-100 churn risk score and risk band.
- `mart_revenue_retention`: gross revenue retention by segment and plan.
- `mart_product_adoption`: feature adoption by segment.

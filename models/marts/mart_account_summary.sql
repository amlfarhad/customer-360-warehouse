create or replace table mart_account_summary as
with usage as (
    select account_id, sum(events) as total_events, avg(distinct_features_used) as avg_daily_features
    from fct_product_usage_daily
    group by 1
),
revenue as (
    select account_id, sum(recognized_revenue) as recognized_revenue, sum(failed_invoice_amount) as failed_invoice_amount
    from fct_subscription_revenue
    group by 1
),
support as (
    select account_id, count(*) as support_tickets, sum(is_high_priority) as high_priority_tickets, avg(resolved_hours) as avg_resolved_hours
    from fct_support_tickets
    group by 1
)
select
    a.account_id,
    a.account_name,
    a.industry,
    a.region,
    a.segment,
    a.lifecycle_stage,
    a.company_size,
    c.plan,
    c.subscription_status,
    coalesce(u.total_events, 0) as total_events,
    coalesce(u.avg_daily_features, 0) as avg_daily_features,
    coalesce(r.recognized_revenue, 0) as recognized_revenue,
    coalesce(r.failed_invoice_amount, 0) as failed_invoice_amount,
    coalesce(s.support_tickets, 0) as support_tickets,
    coalesce(s.high_priority_tickets, 0) as high_priority_tickets,
    coalesce(s.avg_resolved_hours, 0) as avg_resolved_hours
from dim_accounts a
left join dim_customers c on a.account_id = c.account_id
left join usage u on a.account_id = u.account_id
left join revenue r on a.account_id = r.account_id
left join support s on a.account_id = s.account_id;

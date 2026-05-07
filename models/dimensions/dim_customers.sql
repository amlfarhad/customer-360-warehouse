create or replace table dim_customers as
select
    a.account_id as customer_id,
    a.account_id,
    a.account_name,
    a.industry,
    a.region,
    a.segment,
    a.lifecycle_stage,
    a.company_size,
    s.plan,
    s.status as subscription_status,
    s.started_at as customer_since
from dim_accounts a
left join stg_billing_subscriptions s
    on a.account_id = s.account_id
qualify row_number() over (partition by a.account_id order by s.started_at desc nulls last) = 1;

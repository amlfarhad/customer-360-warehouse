create or replace table mart_revenue_retention as
select
    segment,
    plan,
    count(*) as accounts,
    sum(recognized_revenue) as recognized_revenue,
    sum(case when lifecycle_stage = 'churned' then recognized_revenue else 0 end) as churned_revenue,
    case when sum(recognized_revenue) > 0
         then 1 - sum(case when lifecycle_stage = 'churned' then recognized_revenue else 0 end) / sum(recognized_revenue)
         else null end as gross_revenue_retention
from mart_customer_health
group by 1, 2;

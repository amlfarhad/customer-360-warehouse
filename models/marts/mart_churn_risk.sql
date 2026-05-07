create or replace table mart_churn_risk as
select
    account_id,
    account_name,
    segment,
    region,
    lifecycle_stage,
    plan,
    health_score,
    least(100, greatest(0,
        100 - health_score
        + case when failed_invoice_amount > 0 then 12 else 0 end
        + least(high_priority_tickets * 5, 20)
        + case when lifecycle_stage = 'churned' then 40 else 0 end
    )) as churn_risk_score,
    case
        when lifecycle_stage = 'churned' then 'already_churned'
        when 100 - health_score >= 55 then 'high'
        when 100 - health_score >= 35 then 'medium'
        else 'low'
    end as churn_risk_band
from mart_customer_health;

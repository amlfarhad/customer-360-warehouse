create or replace table mart_customer_health as
select
    *,
    least(100, greatest(0,
        45
        + least(total_events / 25, 25)
        + least(recognized_revenue / 25000, 15)
        - least(support_tickets * 4, 20)
        - least(high_priority_tickets * 8, 20)
        - case when failed_invoice_amount > 0 then 12 else 0 end
        - case when lifecycle_stage = 'churned' then 35 else 0 end
    )) as health_score
from mart_account_summary;

create or replace table fct_support_tickets as
select
    ticket_id,
    account_id,
    cast(created_at as date) as ticket_date,
    category,
    priority,
    resolved_hours,
    case when priority in ('high', 'urgent') then 1 else 0 end as is_high_priority
from stg_support_tickets;

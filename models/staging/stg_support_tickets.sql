create or replace table stg_support_tickets as
select
    cast(ticket_id as integer) as ticket_id,
    cast(account_id as integer) as account_id,
    cast(created_at as timestamp) as created_at,
    category,
    priority,
    cast(resolved_hours as double) as resolved_hours
from support_tickets;

create or replace table stg_billing_invoices as
select
    cast(invoice_id as integer) as invoice_id,
    cast(subscription_id as integer) as subscription_id,
    cast(account_id as integer) as account_id,
    cast(invoice_date as date) as invoice_date,
    cast(amount as double) as amount,
    status
from billing_invoices;

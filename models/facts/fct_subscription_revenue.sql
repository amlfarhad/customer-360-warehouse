create or replace table fct_subscription_revenue as
select
    invoice_id,
    subscription_id,
    account_id,
    invoice_date,
    amount,
    status,
    case when status = 'paid' and amount > 0 then amount else 0 end as recognized_revenue,
    case when status = 'failed' then amount else 0 end as failed_invoice_amount
from stg_billing_invoices;

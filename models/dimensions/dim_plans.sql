create or replace table dim_plans as
select * from (
    values
        ('starter', 900, 'SMB self-serve plan'),
        ('growth', 3500, 'Mid-market growth plan'),
        ('enterprise', 12500, 'Enterprise contract plan')
) as plans(plan, base_mrr, description);

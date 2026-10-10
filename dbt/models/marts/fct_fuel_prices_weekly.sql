-- Gold: weekly prices with week-on-week change and a 4-week moving average
with prices as (
    select * from {{ ref('stg_fuelprice') }}
)
select
    price_date,
    ron95,
    ron95_budi95,
    ron97,
    diesel,
    ron97  - lag(ron97)  over (order by price_date) as ron97_change,
    diesel - lag(diesel) over (order by price_date) as diesel_change,
    round(avg(ron97) over (order by price_date rows between 3 preceding and current row), 2)
        as ron97_4wk_avg
from prices
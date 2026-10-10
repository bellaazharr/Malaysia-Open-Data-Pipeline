-- Silver: one clean row per week, actual prices only (drops the weekly-change rows)
select
    record_date                                   as price_date,
    (payload->>'ron95')::numeric(6,2)             as ron95,
    (payload->>'ron95_budi95')::numeric(6,2)      as ron95_budi95,
    (payload->>'ron97')::numeric(6,2)             as ron97,
    (payload->>'diesel')::numeric(6,2)            as diesel,
    (payload->>'diesel_eastmsia')::numeric(6,2)   as diesel_east_malaysia,
    loaded_at
from {{ source('raw', 'fuelprice') }}
where series_type = 'level'
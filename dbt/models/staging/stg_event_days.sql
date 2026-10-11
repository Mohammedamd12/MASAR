select
    gov_request_number,
    city_code,
    cast(event_date as date) as event_date,
    relevance
from {{ source('masar_raw', 'event_days') }}
where gov_request_number is not null
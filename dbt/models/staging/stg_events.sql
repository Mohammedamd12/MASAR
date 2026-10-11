select
    gov_request_number,
    event_name,
    event_type,
    venue_type,
    event_city,
    start_date,
    end_date,
    duration_days,
    attendance,
    relevance,
    region_code,
    industrial_city_codes
from {{ source('masar_raw', 'events_clean') }}
where event_name is not null
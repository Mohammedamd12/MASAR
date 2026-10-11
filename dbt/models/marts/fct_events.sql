{{ config(materialized='table') }}

with events_data as (
    select * from {{ ref('stg_events') }}
)

select
    gov_request_number,
    event_name,
    event_type,
    venue_type,
    event_city,
    start_date,
    end_date,
    attendance,
    relevance
from events_data

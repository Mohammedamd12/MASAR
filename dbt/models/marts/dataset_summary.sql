select
    dataset_type,
    count(*) as file_count
from {{ ref('stg_source_files') }}
group by dataset_type


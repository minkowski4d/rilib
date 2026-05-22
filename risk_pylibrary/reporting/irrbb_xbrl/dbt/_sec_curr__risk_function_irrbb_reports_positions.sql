{{ config(
    tags=["risk_function_generic_sources", "risk_function_sources_irrbb_reports_positions"]
) }}

with latest_data as (
    SELECT
        report::varchar as report,
        report_date::date as report_date,
        idx::varchar as idx,
        group_0::varchar as group_0,
        group_1::varchar as group_1,
        fmt::varchar as fmt,
        value::double as value,
        ROW_NUMBER() OVER (
            PARTITION BY report::varchar, report_date::date, idx::varchar, group_0::varchar, group_1::varchar
            ORDER BY report_date::date DESC
        ) as rn
    FROM
        {{ source('ext__risk_function_data_irrbb', 'src_curr__risk_function_irrbb_reports_positions') }}
)

SELECT
    report,
    report_date,
    idx,
    group_0,
    group_1,
    fmt,
    value,
    concat(
        'irrbb-position-',
        to_char(report),
        '-',
        to_char(report_date),
        '-',
        to_char(idx),
        '-',
        to_char(group_0),
        '-',
        to_char(group_1)
    ) AS surrogate_key
FROM latest_data
WHERE rn = 1



SELECT
    instrument_type,
    SUM(IFF(report_date = '2025-06-30', ABS(mkt_mid_eur), 0))  AS "2025-06-30",
    SUM(IFF(report_date = '2025-09-30', ABS(mkt_mid_eur), 0))  AS "2025-09-30",
    SUM(IFF(report_date = '2025-12-31', ABS(mkt_mid_eur), 0))  AS "2025-12-31",
    SUM(IFF(report_date = '2026-03-31', ABS(mkt_mid_eur), 0))  AS "2026-03-31"
FROM TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_trading_valuation
WHERE report_date IN ('2025-06-30', '2025-09-30', '2025-12-31', '2026-03-31')
GROUP BY 1
ORDER BY "2026-03-31" DESC;


SELECT
    sec_acc_no,
    SUM(IFF(mkt_mid_eur > 0,  mkt_mid_eur, 0))  AS long_eur,
    SUM(IFF(mkt_mid_eur < 0,  mkt_mid_eur, 0))  AS short_eur,
    SUM(mkt_mid_eur)                              AS net_eur,
    SUM(ABS(mkt_mid_eur))                         AS gross_eur,
    COUNT(IFF(mkt_mid_eur > 0, 1, NULL))          AS long_count,
    COUNT(IFF(mkt_mid_eur < 0, 1, NULL))          AS short_count
FROM TEAMS_PRD.RISK_FUNCTION_PUBLISH.pbl__risk_function_mrm_book_trading_valuation
WHERE report_date = '2026-05-08'
GROUP BY 1
ORDER BY gross_eur DESC;



SELECT
MAX(TRADE_TS)
FROM
TEAMS_PRD.INVESTING_PUBLISH.pbl__execution_quality_euronext
;w
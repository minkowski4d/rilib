/*********************************/
 
-- ============================================================
-- LSI-ST 2026 — MARKET RISK STRESS TEST — COMPLETE FINAL QUERY
-- Trade Republic Bank GmbH | Reference date: 30.09.2025
-- ============================================================
-- FUND APPROACH: No Durchschau.
-- All funds → ZNr42 sonstige nicht zuordenbare Positionen
-- (einschließlich Positionen ohne Durchschau), shock -50.6%.
-- All funds → SNr3_over_5Y (no maturity data).
-- ============================================================
 
WITH params AS (
    SELECT
        '2025-09-30'::DATE AS report_date,
        556000000          AS cet1_eur,
        0.0003             AS fx_threshold_pct
),
 
-- ============================================================
-- UPnL SOURCE
-- ============================================================
pnl_source AS (
    SELECT
        instrument_id,
        SUM(upnl) AS upnl_eur
    FROM TEAMS_PRD.RISK_FUNCTION_SOURCE.src_curr__risk_function__mrm_trading_book_pnl
    WHERE report_date::DATE = '2025-09-30'
      AND NOT (data_src_primary IN ('share_booking','inquisitor')
               AND sec_acc_no = '9800001601')
      AND NOT (data_src_primary IN ('share_booking')
               AND sec_acc_no = '9800003601')
      AND instrument_id != ''
    GROUP BY instrument_id
),
 
-- ============================================================
-- STEP 1: BASE
-- ============================================================
base AS (
    SELECT
        t.instrument_type,
        t.asset_type,
        t.fund_underlying_index,
        t.years_to_maturity,
        t.rating_class,
        t.currency,
        t.quantity,
        COALESCE(t.duration_mod, t.years_to_maturity, 1.0) AS duration_mod,
        -- years_to_maturity: fallback to duration_mod, then 1.0 (conservative: SNr1_under_1Y)
        COALESCE(t.years_to_maturity, t.duration_mod, 1.0) AS years_to_maturity,
        t.mkt_mid_eur,
        t.close_mid_price_dirty,
        t.fx_rate_eur,
 
        -- Market value
        -- Bonds: dirty price * qty * fx; null-price bonds (55 pos, 108 TEUR net)
        -- excluded — mkt_mid_eur not used as fallback since it includes shorts
        -- whose ABS would inflate the gross position incorrectly
        CASE
            WHEN t.instrument_type = 'BOND'
            THEN t.close_mid_price_dirty * t.quantity * t.fx_rate_eur
            ELSE t.mkt_mid_eur
        END AS market_value_eur,
 
        -- Buchwert = Marktwert - UPnL
        CASE
            WHEN t.instrument_type = 'BOND'
            THEN (t.close_mid_price_dirty * t.quantity * t.fx_rate_eur)
                 - COALESCE(p.upnl_eur, 0)
            ELSE t.mkt_mid_eur - COALESCE(p.upnl_eur, 0)
        END AS buchwert_eur,
 
        GREATEST(COALESCE(p.upnl_eur, 0), 0)  AS kursreserve_eur,
        GREATEST(-COALESCE(p.upnl_eur, 0), 0) AS stille_last_eur,
 
        -- Maturity bucket: all FUNDs → SNr3_over_5Y (no maturity data)
        -- Bonds with both fields null default to 1.0 → SNr1_under_1Y (conservative)
        CASE
            WHEN t.instrument_type = 'FUND'                                   THEN 'SNr3_over_5Y'
            WHEN COALESCE(t.years_to_maturity, t.duration_mod, 1.0) <  1.0   THEN 'SNr1_under_1Y'
            WHEN COALESCE(t.years_to_maturity, t.duration_mod, 1.0) <= 5.0   THEN 'SNr2_1Y_to_5Y'
            ELSE                                                                    'SNr3_over_5Y'
        END AS snr_maturity_bucket,
 
        -- Position flag
        CASE
            WHEN t.instrument_type = 'DERIVATIVE' AND t.asset_type = 'STOCK'
                THEN 'OK'
            WHEN t.quantity < 0 AND t.instrument_type = 'STOCK'  THEN 'CHECK_SHORT_EQUITY'
            WHEN t.quantity < 0 AND t.instrument_type = 'BOND'   THEN 'CHECK_SHORT_BOND'
            WHEN t.quantity < 0 AND t.instrument_type = 'FUND'   THEN 'CHECK_SHORT_FUND'
            WHEN t.quantity < 0                                   THEN 'CHECK_OTHER_NEGATIVE'
            ELSE 'OK'
        END AS position_flag,
 
        -- ZNr mapping
        CASE
            -- BONDS
            WHEN t.instrument_type = 'BOND' AND t.asset_type = 'BOND_GOVERNMENT'
            THEN CASE t.rating_class
                WHEN 'AAA' THEN 'ZNr02_Staat_AAA'
                WHEN 'AA'  THEN 'ZNr03_Staat_AA'
                WHEN 'A'   THEN 'ZNr04_Staat_A'
                WHEN 'BBB' THEN 'ZNr05_Staat_BBB'
                WHEN 'BB'  THEN 'ZNr06_Staat_BB'
                WHEN 'B'   THEN 'ZNr07_Staat_B'
                WHEN 'CCC' THEN 'ZNr08_Staat_CCC'
                ELSE            'ZNr09_Staat_NoRating'
            END
            WHEN t.instrument_type = 'BOND'
                 AND (t.asset_type = 'BOND_CORPORATE' OR t.asset_type IS NULL)
            THEN CASE t.rating_class
                WHEN 'AAA' THEN 'ZNr10_Corp_AAA'
                WHEN 'AA'  THEN 'ZNr11_Corp_AA'
                WHEN 'A'   THEN 'ZNr12_Corp_A'
                WHEN 'BBB' THEN 'ZNr13_Corp_BBB'
                WHEN 'BB'  THEN 'ZNr14_Corp_BB'
                WHEN 'B'   THEN 'ZNr15_Corp_B'
                WHEN 'CCC' THEN 'ZNr16_Corp_CCC'
                ELSE            'ZNr17_Corp_NoRating'
            END
            -- EQUITY
            WHEN t.instrument_type IN ('STOCK','SYNTHETIC')
                 AND t.asset_type IN ('EQUITY','STOCK')            THEN 'ZNr18_Equity'
            -- FX
            WHEN t.instrument_type = 'FX'
                 AND t.asset_type = 'FX_SPOT'                     THEN 'ZNr24_FX_Direct'
            -- FUNDS: no Durchschau → all sonstige nicht zuordenbare Positionen
            WHEN t.instrument_type = 'FUND'                        THEN 'ZNr42_Fund_Sonstige'
            -- OTHER
            WHEN t.instrument_type = 'DERIVATIVE'
                 AND t.asset_type = 'STOCK'                       THEN 'ZNr18_Equity'
            WHEN t.instrument_type = 'CRYPTO'                     THEN 'OUT_OF_SCOPE'
            ELSE 'ZNr29_Other'
        END AS znr,
 
        -- IR shock (bonds only) — uses COALESCE(years_to_maturity, duration_mod, 1.0)
        CASE
            WHEN COALESCE(t.years_to_maturity, t.duration_mod, 1.0) <= 0.083 THEN 148.0
            WHEN COALESCE(t.years_to_maturity, t.duration_mod, 1.0) <= 0.25
                THEN 148.0+(111.0-148.0)*(COALESCE(t.years_to_maturity, t.duration_mod, 1.0)-0.083)/(0.25-0.083)
            WHEN COALESCE(t.years_to_maturity, t.duration_mod, 1.0) <= 1.0   THEN 111.0
            WHEN COALESCE(t.years_to_maturity, t.duration_mod, 1.0) <= 2.0
                THEN 111.0+(108.0-111.0)*(COALESCE(t.years_to_maturity, t.duration_mod, 1.0)-1.0)/(2.0-1.0)
            WHEN COALESCE(t.years_to_maturity, t.duration_mod, 1.0) <= 3.0
                THEN 108.0+(105.0-108.0)*(COALESCE(t.years_to_maturity, t.duration_mod, 1.0)-2.0)/(3.0-2.0)
            WHEN COALESCE(t.years_to_maturity, t.duration_mod, 1.0) <= 5.0
                THEN 105.0+(95.0-105.0)*(COALESCE(t.years_to_maturity, t.duration_mod, 1.0)-3.0)/(5.0-3.0)
            WHEN COALESCE(t.years_to_maturity, t.duration_mod, 1.0) <= 7.0
                THEN 95.0+(77.0-95.0)*(COALESCE(t.years_to_maturity, t.duration_mod, 1.0)-5.0)/(7.0-5.0)
            WHEN COALESCE(t.years_to_maturity, t.duration_mod, 1.0) <= 10.0
                THEN 77.0+(78.0-77.0)*(COALESCE(t.years_to_maturity, t.duration_mod, 1.0)-7.0)/(10.0-7.0)
            WHEN COALESCE(t.years_to_maturity, t.duration_mod, 1.0) <= 20.0
                THEN 78.0+(57.0-78.0)*(COALESCE(t.years_to_maturity, t.duration_mod, 1.0)-10.0)/(20.0-10.0)
            WHEN COALESCE(t.years_to_maturity, t.duration_mod, 1.0) <= 30.0
                THEN 57.0+(34.0-57.0)*(COALESCE(t.years_to_maturity, t.duration_mod, 1.0)-20.0)/(30.0-20.0)
            ELSE 34.0
        END AS ir_shock_bps,
 
        -- CS shock (bonds only)
        CASE
            WHEN t.instrument_type = 'BOND' AND t.asset_type = 'BOND_GOVERNMENT'
            THEN CASE t.rating_class
                WHEN 'AAA' THEN 37  WHEN 'AA' THEN 42
                WHEN 'A'   THEN 110 WHEN 'BBB' THEN 164
                ELSE 204 END
            WHEN t.instrument_type = 'BOND'
            THEN CASE t.rating_class
                WHEN 'AAA' THEN 85  WHEN 'AA'  THEN 125
                WHEN 'A'   THEN 164 WHEN 'BBB' THEN 204
                WHEN 'BB'  THEN 243 WHEN 'B'   THEN 282
                ELSE 282 END
            ELSE 0
        END AS cs_shock_bps
 
    FROM teams_prd.risk_function_publish.pbl__risk_function_mrm_book_trading_valuation t
    LEFT JOIN pnl_source p ON t.instrument_id = p.instrument_id
    WHERE t.report_date      = '2025-09-30'
      AND t.instrument_type IS NOT NULL
),
 
-- ============================================================
-- STEP 2: SHOCKED
-- ============================================================
shocked AS (
    SELECT
        b.*,
 
        -- mv_change_primary
        CASE
            WHEN b.instrument_type = 'BOND'
            THEN -1.0 * b.duration_mod * b.market_value_eur
                 * (b.ir_shock_bps + b.cs_shock_bps) / 10000.0
            WHEN b.instrument_type IN ('STOCK','SYNTHETIC')
                 AND b.asset_type IN ('EQUITY','STOCK')
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.506
            WHEN b.instrument_type = 'DERIVATIVE' AND b.asset_type = 'STOCK'
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.506
            -- FUND: all sonstige → -50.6%
            WHEN b.instrument_type = 'FUND'
            THEN -1.0 * b.market_value_eur * 0.506
            WHEN b.instrument_type = 'FX' AND b.asset_type = 'FX_SPOT'
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.044
            WHEN b.instrument_type = 'CRYPTO' THEN 0.0
            ELSE -1.0 * b.market_value_eur * 0.506
        END AS mv_change_primary,
 
        -- mv_change_cs_only (SNr 11 input — bonds only)
        CASE WHEN b.instrument_type = 'BOND'
        THEN -1.0 * b.duration_mod * b.market_value_eur
             * b.cs_shock_bps / 10000.0
        ELSE 0.0 END AS mv_change_cs_only,
 
        -- mv_change_ir_only (SNr 11 — bonds only)
        CASE WHEN b.instrument_type = 'BOND'
        THEN -1.0 * b.duration_mod * b.market_value_eur
             * b.ir_shock_bps / 10000.0
        ELSE 0.0 END AS mv_change_ir_only,
 
        -- mv_change_combined (primary + FX addon for non-EUR bonds)
        CASE
            WHEN b.instrument_type = 'BOND' AND b.currency != 'EUR'
            THEN
                (-1.0 * b.duration_mod * b.market_value_eur
                 * (b.ir_shock_bps + b.cs_shock_bps) / 10000.0)
                + (SIGN(b.quantity) * (-1.0)
                   * (b.market_value_eur
                      + (-1.0 * b.duration_mod * b.market_value_eur
                         * (b.ir_shock_bps + b.cs_shock_bps) / 10000.0))
                   * 0.044)
            WHEN b.instrument_type = 'BOND' AND b.currency = 'EUR'
            THEN -1.0 * b.duration_mod * b.market_value_eur
                 * (b.ir_shock_bps + b.cs_shock_bps) / 10000.0
            WHEN b.instrument_type IN ('STOCK','SYNTHETIC')
                 AND b.asset_type IN ('EQUITY','STOCK')
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.506
            WHEN b.instrument_type = 'DERIVATIVE' AND b.asset_type = 'STOCK'
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.506
            -- FUND: all sonstige → -50.6%
            WHEN b.instrument_type = 'FUND'
            THEN -1.0 * b.market_value_eur * 0.506
            WHEN b.instrument_type = 'FX' AND b.asset_type = 'FX_SPOT'
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.044
            WHEN b.instrument_type = 'CRYPTO' THEN 0.0
            ELSE -1.0 * b.market_value_eur * 0.506
        END AS mv_change_combined
 
    FROM base b
),
 
-- ============================================================
-- BOND METRICS: SNr 6 + SNr 7
-- ============================================================
bond_metrics AS (
    SELECT
        CASE
            WHEN asset_type = 'BOND_GOVERNMENT'
            THEN CASE rating_class
                WHEN 'AAA' THEN 'ZNr02_Staat_AAA' WHEN 'AA'  THEN 'ZNr03_Staat_AA'
                WHEN 'A'   THEN 'ZNr04_Staat_A'   WHEN 'BBB' THEN 'ZNr05_Staat_BBB'
                WHEN 'BB'  THEN 'ZNr06_Staat_BB'  WHEN 'B'   THEN 'ZNr07_Staat_B'
                WHEN 'CCC' THEN 'ZNr08_Staat_CCC' ELSE            'ZNr09_Staat_NoRating'
            END
            ELSE CASE rating_class
                WHEN 'AAA' THEN 'ZNr10_Corp_AAA'  WHEN 'AA'  THEN 'ZNr11_Corp_AA'
                WHEN 'A'   THEN 'ZNr12_Corp_A'    WHEN 'BBB' THEN 'ZNr13_Corp_BBB'
                WHEN 'BB'  THEN 'ZNr14_Corp_BB'   WHEN 'B'   THEN 'ZNr15_Corp_B'
                WHEN 'CCC' THEN 'ZNr16_Corp_CCC'  ELSE            'ZNr17_Corp_NoRating'
            END
        END AS znr,
        ROUND(
            SUM(ABS(close_mid_price_dirty * quantity * fx_rate_eur)
                * COALESCE(years_to_maturity, duration_mod, 1.0))
            / NULLIF(SUM(ABS(close_mid_price_dirty * quantity * fx_rate_eur)), 0)
        , 2) AS snr6_avg_restlaufzeit,
        ROUND(
            SUM(-1.0 * COALESCE(duration_mod, years_to_maturity, 1.0)
                * (close_mid_price_dirty * quantity * fx_rate_eur)
                * 0.01)
            / 1000.0
        , 2) AS snr7_zinssensitivitaet_teur
    FROM teams_prd.risk_function_publish.pbl__risk_function_mrm_book_trading_valuation
    WHERE report_date     = '2025-09-30'
      AND instrument_type = 'BOND'
    GROUP BY znr
),
 
-- ============================================================
-- SECTION A: Main positions ZNr 2-43
-- ============================================================
section_a AS (
    SELECT
        'A_MAIN'                                        AS section,
        s.znr,
        NULL::VARCHAR                                   AS currency,
        LISTAGG(DISTINCT s.position_flag, ' | ')
            WITHIN GROUP (ORDER BY s.position_flag)     AS position_flag,
        COUNT(*)                                        AS position_count,
        ROUND(SUM(CASE WHEN s.snr_maturity_bucket = 'SNr1_under_1Y'
            THEN CASE WHEN s.znr = 'ZNr18_Equity'
                 OR s.znr = 'ZNr42_Fund_Sonstige'
                 THEN s.market_value_eur ELSE ABS(s.market_value_eur) END
            ELSE 0 END) / 1000.0, 2)                    AS snr1_mv_under_1y_teur,
        ROUND(SUM(CASE WHEN s.snr_maturity_bucket = 'SNr2_1Y_to_5Y'
            THEN CASE WHEN s.znr = 'ZNr18_Equity'
                 OR s.znr = 'ZNr42_Fund_Sonstige'
                 THEN s.market_value_eur ELSE ABS(s.market_value_eur) END
            ELSE 0 END) / 1000.0, 2)                    AS snr2_mv_1y_to_5y_teur,
        ROUND(SUM(CASE WHEN s.snr_maturity_bucket = 'SNr3_over_5Y'
            THEN CASE WHEN s.znr = 'ZNr18_Equity'
                 OR s.znr = 'ZNr42_Fund_Sonstige'
                 THEN s.market_value_eur ELSE ABS(s.market_value_eur) END
            ELSE 0 END) / 1000.0, 2)                    AS snr3_mv_over_5y_teur,
        0.0                                             AS snr4_floater_share_teur,
        ROUND(SUM(CASE WHEN s.znr IN ('ZNr18_Equity','ZNr42_Fund_Sonstige')
            THEN s.buchwert_eur ELSE ABS(s.buchwert_eur) END
        ) / 1000.0, 2)                                  AS snr5_buchwert_teur,
        bm.snr6_avg_restlaufzeit                        AS snr6_avg_restlaufzeit_years,
        bm.snr7_zinssensitivitaet_teur                  AS snr7_zinssensitivitaet_teur,
        ROUND(SUM(CASE WHEN s.snr_maturity_bucket = 'SNr1_under_1Y'
            THEN s.mv_change_combined ELSE 0 END) / 1000.0, 2)
                                                        AS snr8_shock_under_1y_teur,
        ROUND(SUM(CASE WHEN s.snr_maturity_bucket = 'SNr2_1Y_to_5Y'
            THEN s.mv_change_combined ELSE 0 END) / 1000.0, 2)
                                                        AS snr9_shock_1y_to_5y_teur,
        ROUND(SUM(CASE WHEN s.snr_maturity_bucket = 'SNr3_over_5Y'
            THEN s.mv_change_combined ELSE 0 END) / 1000.0, 2)
                                                        AS snr10_shock_over_5y_teur,
        ROUND(SUM(s.mv_change_ir_only) / 1000.0, 2)    AS snr11_ir_only_teur,
        ROUND(SUM(s.kursreserve_eur) / 1000.0, 2)      AS snr12_kursreserven_teur,
        ROUND(SUM(
            LEAST(
                GREATEST(
                    s.mv_change_combined + s.kursreserve_eur,
                    s.mv_change_combined
                ),
                0.0  -- Kursreserven can reduce loss but never create a gain
            )
        ) / 1000.0, 2)                                  AS snr13_pl_effective_teur,
        0.0                                             AS snr14_hedge_ratio_ir_pct,
        0.0                                             AS snr15_hedge_ratio_cs_pct,
        ROUND(SUM(s.stille_last_eur) / 1000.0, 2)      AS stille_lasten_teur,
        NULL::FLOAT                                     AS fx_snr1_post_shock_teur,
        NULL::FLOAT                                     AS fx_snr8_shock_teur,
        NULL::FLOAT                                     AS fx_snr14_gross_teur,
        NULL::VARCHAR                                   AS fx_status
    FROM shocked s
    LEFT JOIN bond_metrics bm ON s.znr = bm.znr
    WHERE s.znr NOT IN ('OUT_OF_SCOPE','OUT_OF_SCOPE_REVIEW','ZNr24_FX_Direct')
    GROUP BY s.znr, bm.snr6_avg_restlaufzeit, bm.snr7_zinssensitivitaet_teur
),
 
-- ============================================================
-- SECTION B: ZNr 24 — non-EUR direct positions
-- ============================================================
znr24_base AS (
    SELECT
        s.currency,
        SUM(s.market_value_eur + s.mv_change_primary)  AS snr1_post_shock,
        SUM(CASE WHEN s.market_value_eur > 0
                 THEN s.market_value_eur ELSE 0 END)    AS snr14_gross,
        SUM(s.market_value_eur)                         AS mv_before,
        -- threshold checked on pre-shock net open position per regulation
        SUM(s.market_value_eur)                         AS open_position_eur,
        -- buchwert = market_value - upnl per instrument, summed by currency
        SUM(s.buchwert_eur)                             AS buchwert_eur,
        SUM(s.kursreserve_eur)                          AS kursreserve_eur,
        SUM(s.stille_last_eur)                          AS stille_last_eur,
        COUNT(*)                                        AS n_pos
    FROM shocked s
    WHERE s.currency      != 'EUR'
      AND s.instrument_type != 'FUND'
      AND s.znr NOT IN ('OUT_OF_SCOPE','OUT_OF_SCOPE_REVIEW')
    GROUP BY s.currency
),
 
section_b AS (
    SELECT
        'B_ZNr24_FX_DIRECT'                            AS section,
        'ZNr24_FX_Open_Position'::VARCHAR               AS znr,
        z.currency,
        CASE
            WHEN z.open_position_eur > p.cet1_eur * p.fx_threshold_pct THEN '✅ REPORTABLE'
            WHEN z.open_position_eur <= 0                               THEN '⛔ NET SHORT'
            ELSE '⚪ BELOW THRESHOLD'
        END                                             AS position_flag,
        z.n_pos                                         AS position_count,
        NULL::FLOAT                                     AS snr1_mv_under_1y_teur,
        NULL::FLOAT                                     AS snr2_mv_1y_to_5y_teur,
        ROUND(z.open_position_eur / 1000.0, 2)         AS snr3_mv_over_5y_teur,
        0.0                                             AS snr4_floater_share_teur,
        ROUND(z.buchwert_eur / 1000.0, 2)              AS snr5_buchwert_teur,
        NULL::FLOAT                                     AS snr6_avg_restlaufzeit_years,
        NULL::FLOAT                                     AS snr7_zinssensitivitaet_teur,
        NULL::FLOAT                                     AS snr8_shock_under_1y_teur,
        NULL::FLOAT                                     AS snr9_shock_1y_to_5y_teur,
        ROUND(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) / 1000.0
             ELSE 0 END, 2)                             AS snr10_shock_over_5y_teur,
        NULL::FLOAT                                     AS snr11_ir_only_teur,
        ROUND(z.kursreserve_eur / 1000.0, 2)           AS snr12_kursreserven_teur,
        ROUND(LEAST(GREATEST(
            CASE WHEN z.snr1_post_shock > 0
                 THEN z.snr1_post_shock * (-0.044) ELSE 0 END
            + z.kursreserve_eur,
            CASE WHEN z.snr1_post_shock > 0
                 THEN z.snr1_post_shock * (-0.044) ELSE 0 END
        ), 0.0) / 1000.0, 2)                            AS snr13_pl_effective_teur,
        NULL::FLOAT                                     AS snr14_hedge_ratio_ir_pct,
        NULL::FLOAT                                     AS snr15_hedge_ratio_cs_pct,
        ROUND(z.stille_last_eur / 1000.0, 2)           AS stille_lasten_teur,
        ROUND(z.snr1_post_shock / 1000.0, 2)           AS fx_snr1_post_shock_teur,
        ROUND(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) / 1000.0
             ELSE 0 END, 2)                             AS fx_snr8_shock_teur,
        ROUND(z.snr14_gross / 1000.0, 2)               AS fx_snr14_gross_teur,
        CASE
            WHEN z.open_position_eur > p.cet1_eur * p.fx_threshold_pct THEN '✅ REPORTABLE'
            WHEN z.open_position_eur <= 0                               THEN '⛔ NET SHORT'
            ELSE '⚪ BELOW THRESHOLD'
        END                                             AS fx_status
    FROM znr24_base z
    CROSS JOIN params p
    WHERE z.open_position_eur > 0
),
 
section_b_total AS (
    SELECT
        'B_ZNr24_FX_DIRECT'                            AS section,
        'ZNr24_TOTAL_REPORTABLE'::VARCHAR               AS znr,
        'ALL_REPORTABLE_CURRENCIES'::VARCHAR            AS currency,
        '✅ TOTAL'                                      AS position_flag,
        SUM(z.n_pos)                                    AS position_count,
        NULL::FLOAT                                     AS snr1_mv_under_1y_teur,
        NULL::FLOAT                                     AS snr2_mv_1y_to_5y_teur,
        ROUND(SUM(z.open_position_eur) / 1000.0, 2)    AS snr3_mv_over_5y_teur,
        0.0                                             AS snr4_floater_share_teur,
        ROUND(SUM(z.buchwert_eur) / 1000.0, 2)         AS snr5_buchwert_teur,
        NULL::FLOAT                                     AS snr6_avg_restlaufzeit_years,
        NULL::FLOAT                                     AS snr7_zinssensitivitaet_teur,
        NULL::FLOAT                                     AS snr8_shock_under_1y_teur,
        NULL::FLOAT                                     AS snr9_shock_1y_to_5y_teur,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) ELSE 0 END) / 1000.0, 2)
                                                        AS snr10_shock_over_5y_teur,
        NULL::FLOAT                                     AS snr11_ir_only_teur,
        ROUND(SUM(z.kursreserve_eur) / 1000.0, 2)     AS snr12_kursreserven_teur,
        ROUND(SUM(LEAST(GREATEST(
            CASE WHEN z.snr1_post_shock > 0
                 THEN z.snr1_post_shock * (-0.044) ELSE 0 END
            + z.kursreserve_eur,
            CASE WHEN z.snr1_post_shock > 0
                 THEN z.snr1_post_shock * (-0.044) ELSE 0 END
        ), 0.0)) / 1000.0, 2)                           AS snr13_pl_effective_teur,
        NULL::FLOAT                                     AS snr14_hedge_ratio_ir_pct,
        NULL::FLOAT                                     AS snr15_hedge_ratio_cs_pct,
        ROUND(SUM(z.stille_last_eur) / 1000.0, 2)     AS stille_lasten_teur,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock ELSE 0 END) / 1000.0, 2)
                                                        AS fx_snr1_post_shock_teur,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) ELSE 0 END) / 1000.0, 2)
                                                        AS fx_snr8_shock_teur,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr14_gross ELSE 0 END) / 1000.0, 2)
                                                        AS fx_snr14_gross_teur,
        '✅ TOTAL'                                      AS fx_status
    FROM znr24_base z
    CROSS JOIN params p
    WHERE z.open_position_eur > p.cet1_eur * p.fx_threshold_pct
),
 
znr25_base AS (
    SELECT
        s.currency,
        SUM(s.market_value_eur + s.mv_change_primary)  AS snr1_post_shock,
        SUM(s.market_value_eur)                         AS mv_before,
        -- threshold checked on pre-shock net open position per regulation
        SUM(s.market_value_eur)                         AS open_position_eur,
        -- buchwert = market_value - upnl per instrument, summed by currency
        SUM(s.buchwert_eur)                             AS buchwert_eur,
        SUM(s.kursreserve_eur)                          AS kursreserve_eur,
        SUM(s.stille_last_eur)                          AS stille_last_eur,
        COUNT(*)                                        AS n_pos
    FROM shocked s
    WHERE s.currency      != 'EUR'
      AND s.instrument_type = 'FUND'
    GROUP BY s.currency
),
 
section_c AS (
    SELECT
        'C_ZNr25_FX_FUNDS'                             AS section,
        'ZNr25_FX_Fund_Position'::VARCHAR               AS znr,
        z.currency,
        CASE
            WHEN z.open_position_eur > p.cet1_eur * p.fx_threshold_pct THEN '✅ REPORTABLE'
            WHEN z.open_position_eur <= 0                               THEN '⛔ NET SHORT'
            ELSE '⚪ BELOW THRESHOLD'
        END                                             AS position_flag,
        z.n_pos                                         AS position_count,
        NULL::FLOAT                                     AS snr1_mv_under_1y_teur,
        NULL::FLOAT                                     AS snr2_mv_1y_to_5y_teur,
        ROUND(z.open_position_eur / 1000.0, 2)         AS snr3_mv_over_5y_teur,
        0.0                                             AS snr4_floater_share_teur,
        ROUND(z.buchwert_eur / 1000.0, 2)              AS snr5_buchwert_teur,
        NULL::FLOAT                                     AS snr6_avg_restlaufzeit_years,
        NULL::FLOAT                                     AS snr7_zinssensitivitaet_teur,
        NULL::FLOAT                                     AS snr8_shock_under_1y_teur,
        NULL::FLOAT                                     AS snr9_shock_1y_to_5y_teur,
        ROUND(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) / 1000.0
             ELSE 0 END, 2)                             AS snr10_shock_over_5y_teur,
        NULL::FLOAT                                     AS snr11_ir_only_teur,
        ROUND(z.kursreserve_eur / 1000.0, 2)           AS snr12_kursreserven_teur,
        ROUND(LEAST(GREATEST(
            CASE WHEN z.snr1_post_shock > 0
                 THEN z.snr1_post_shock * (-0.044) ELSE 0 END
            + z.kursreserve_eur,
            CASE WHEN z.snr1_post_shock > 0
                 THEN z.snr1_post_shock * (-0.044) ELSE 0 END
        ), 0.0) / 1000.0, 2)                            AS snr13_pl_effective_teur,
        NULL::FLOAT                                     AS snr14_hedge_ratio_ir_pct,
        NULL::FLOAT                                     AS snr15_hedge_ratio_cs_pct,
        ROUND(z.stille_last_eur / 1000.0, 2)           AS stille_lasten_teur,
        ROUND(z.snr1_post_shock / 1000.0, 2)           AS fx_snr1_post_shock_teur,
        ROUND(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) / 1000.0
             ELSE 0 END, 2)                             AS fx_snr8_shock_teur,
        NULL::FLOAT                                     AS fx_snr14_gross_teur,
        CASE
            WHEN z.open_position_eur > p.cet1_eur * p.fx_threshold_pct THEN '✅ REPORTABLE'
            WHEN z.open_position_eur <= 0                               THEN '⛔ NET SHORT'
            ELSE '⚪ BELOW THRESHOLD'
        END                                             AS fx_status
    FROM znr25_base z
    CROSS JOIN params p
    WHERE z.open_position_eur > 0
),
 
section_c_total AS (
    SELECT
        'C_ZNr25_FX_FUNDS'                             AS section,
        'ZNr25_TOTAL_REPORTABLE'::VARCHAR               AS znr,
        'ALL_REPORTABLE_CURRENCIES'::VARCHAR            AS currency,
        '✅ TOTAL'                                      AS position_flag,
        SUM(z.n_pos)                                    AS position_count,
        NULL::FLOAT                                     AS snr1_mv_under_1y_teur,
        NULL::FLOAT                                     AS snr2_mv_1y_to_5y_teur,
        ROUND(SUM(z.open_position_eur) / 1000.0, 2)    AS snr3_mv_over_5y_teur,
        0.0                                             AS snr4_floater_share_teur,
        ROUND(SUM(z.buchwert_eur) / 1000.0, 2)         AS snr5_buchwert_teur,
        NULL::FLOAT                                     AS snr6_avg_restlaufzeit_years,
        NULL::FLOAT                                     AS snr7_zinssensitivitaet_teur,
        NULL::FLOAT                                     AS snr8_shock_under_1y_teur,
        NULL::FLOAT                                     AS snr9_shock_1y_to_5y_teur,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) ELSE 0 END) / 1000.0, 2)
                                                        AS snr10_shock_over_5y_teur,
        NULL::FLOAT                                     AS snr11_ir_only_teur,
        ROUND(SUM(z.kursreserve_eur) / 1000.0, 2)     AS snr12_kursreserven_teur,
        ROUND(SUM(LEAST(GREATEST(
            CASE WHEN z.snr1_post_shock > 0
                 THEN z.snr1_post_shock * (-0.044) ELSE 0 END
            + z.kursreserve_eur,
            CASE WHEN z.snr1_post_shock > 0
                 THEN z.snr1_post_shock * (-0.044) ELSE 0 END
        ), 0.0)) / 1000.0, 2)                           AS snr13_pl_effective_teur,
        NULL::FLOAT                                     AS snr14_hedge_ratio_ir_pct,
        NULL::FLOAT                                     AS snr15_hedge_ratio_cs_pct,
        ROUND(SUM(z.stille_last_eur) / 1000.0, 2)     AS stille_lasten_teur,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock ELSE 0 END) / 1000.0, 2)
                                                        AS fx_snr1_post_shock_teur,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) ELSE 0 END) / 1000.0, 2)
                                                        AS fx_snr8_shock_teur,
        NULL::FLOAT                                     AS fx_snr14_gross_teur,
        '✅ TOTAL'                                      AS fx_status
    FROM znr25_base z
    CROSS JOIN params p
    WHERE z.open_position_eur > p.cet1_eur * p.fx_threshold_pct
)
 
 
-- ============================================================
-- FINAL OUTPUT
-- ============================================================
SELECT * FROM section_a
UNION ALL
SELECT * FROM section_b
UNION ALL
SELECT * FROM section_b_total
UNION ALL
SELECT * FROM section_c
UNION ALL
SELECT * FROM section_c_total
ORDER BY section, znr, position_flag;

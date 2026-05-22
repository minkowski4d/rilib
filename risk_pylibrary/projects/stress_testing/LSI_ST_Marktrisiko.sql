-- ============================================================
-- LSI-ST 2026 — MARKET RISK STRESS TEST — COMPLETE FINAL QUERY
-- Trade Republic Bank GmbH | Reference date: 30.09.2025
-- Version: Final — all fixes applied
-- ============================================================

WITH params AS (
    SELECT
        '2025-09-30'::DATE AS report_date,
        556000000          AS cet1_eur,
        0.0003             AS fx_threshold_pct
),

-- ============================================================
-- STEP 1: BASE — enrich every position with derived fields
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
        t.duration_mod,
        t.mkt_mid_eur,
        t.close_mid_price_dirty,
        t.fx_rate_eur,

        -- Market value: bond uses dirty price × qty × FX, rest uses MKT_MID_EUR
        CASE
            WHEN t.instrument_type = 'BOND'
            THEN t.close_mid_price_dirty * t.quantity * t.fx_rate_eur
            ELSE t.mkt_mid_eur
        END AS market_value_eur,

        -- Template maturity bucket (3 buckets matching template SNr 1/2/3)
        CASE
            WHEN t.years_to_maturity <  1.0 THEN 'SNr1_under_1Y'
            WHEN t.years_to_maturity <= 5.0 THEN 'SNr2_1Y_to_5Y'
            ELSE                                 'SNr3_over_5Y'
        END AS snr_maturity_bucket,

        -- Position flag for manual review
        CASE
            WHEN t.instrument_type = 'DERIVATIVE' AND t.asset_type = 'STOCK'
                THEN 'CHECK_DERIVATIVE_SCOPE'
            WHEN t.quantity < 0 AND t.instrument_type = 'STOCK'  THEN 'CHECK_SHORT_EQUITY'
            WHEN t.quantity < 0 AND t.instrument_type = 'BOND'   THEN 'CHECK_SHORT_BOND'
            WHEN t.quantity < 0 AND t.instrument_type = 'FUND'   THEN 'CHECK_SHORT_FUND'
            WHEN t.quantity < 0                                   THEN 'CHECK_OTHER_NEGATIVE'
            ELSE 'OK'
        END AS position_flag,

        -- ZNr mapping
        -- Non-EUR bonds stay in ZNr 2-17 — FX handled separately in ZNr 24/25
        CASE
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
            WHEN t.instrument_type IN ('STOCK','SYNTHETIC')
                 AND t.asset_type IN ('EQUITY','STOCK')            THEN 'ZNr18_Equity'
            WHEN t.instrument_type = 'FUND' AND t.asset_type = 'FUND_OTHER'
                 AND (   t.fund_underlying_index LIKE '%Gold%'
                      OR t.fund_underlying_index LIKE '%Silver%'
                      OR t.fund_underlying_index LIKE '%Platinum%'
                      OR t.fund_underlying_index LIKE '%Palladium%'
                      OR t.fund_underlying_index LIKE '%Precious Metal%'
                      OR t.fund_underlying_index LIKE '%Crude%'
                      OR t.fund_underlying_index LIKE '%Brent%'
                      OR t.fund_underlying_index LIKE '%WTI%'
                      OR t.fund_underlying_index LIKE '%Natural Gas%'
                      OR t.fund_underlying_index LIKE '%Energy%'
                      OR t.fund_underlying_index LIKE '%Petroleum%'
                      OR t.fund_underlying_index LIKE '%Commodity%'
                      OR t.fund_underlying_index LIKE '%Metal%'
                      OR t.fund_underlying_index LIKE '%Copper%'
                      OR t.fund_underlying_index LIKE '%Nickel%'
                      OR t.fund_underlying_index LIKE '%Alumin%'
                      OR t.fund_underlying_index LIKE '%Bloomberg%'
                      OR t.fund_underlying_index LIKE '%Optimis%Roll%')
                                                                   THEN 'ZNr19_Commodity'
            WHEN t.instrument_type = 'FUND' AND t.asset_type = 'FUND_OTHER'
                 AND (   t.fund_underlying_index LIKE '%EPRA%'
                      OR t.fund_underlying_index LIKE '%REIT%'
                      OR t.fund_underlying_index LIKE '%Real Estate%')
                                                                   THEN 'ZNr22_RealEstate'
            WHEN t.instrument_type = 'FX'
                 AND t.asset_type = 'FX_SPOT'                     THEN 'ZNr24_FX_Direct'
            WHEN t.instrument_type = 'FUND'
                 AND t.asset_type IN ('FUND_BONDS','FUND_FIXED_INCOME')
                                                                   THEN 'ZNr33_Fund_Bonds'
            WHEN t.instrument_type = 'FUND'
                 AND t.asset_type = 'FUND_EQUITY'                 THEN 'ZNr35_Fund_Equity'
            WHEN t.instrument_type = 'FUND'
                 AND t.asset_type IN ('FUND_MULTI_ASSET','FUND_OTHER','FUND_ARIS')
                                                                   THEN 'ZNr42_Fund_Other'
            WHEN t.instrument_type = 'FUND'
                 AND t.asset_type = 'FUND_MONEY_MARKET'           THEN 'ZNr43_Fund_Cash'
            WHEN t.instrument_type = 'DERIVATIVE'
                 AND t.asset_type = 'STOCK'                       THEN 'OUT_OF_SCOPE_REVIEW'
            WHEN t.instrument_type = 'CRYPTO'                     THEN 'OUT_OF_SCOPE'
            ELSE 'ZNr29_Other'
        END AS znr,

        -- IR shock (linear interpolation, 2028 stress scenario nodes)
        CASE
            WHEN t.years_to_maturity <= 0.083 THEN 148.0
            WHEN t.years_to_maturity <= 0.25
                THEN 148.0+(111.0-148.0)*(t.years_to_maturity-0.083)/(0.25-0.083)
            WHEN t.years_to_maturity <= 1.0   THEN 111.0
            WHEN t.years_to_maturity <= 2.0
                THEN 111.0+(108.0-111.0)*(t.years_to_maturity-1.0)/(2.0-1.0)
            WHEN t.years_to_maturity <= 3.0
                THEN 108.0+(105.0-108.0)*(t.years_to_maturity-2.0)/(3.0-2.0)
            WHEN t.years_to_maturity <= 5.0
                THEN 105.0+(95.0-105.0)*(t.years_to_maturity-3.0)/(5.0-3.0)
            WHEN t.years_to_maturity <= 7.0
                THEN 95.0+(77.0-95.0)*(t.years_to_maturity-5.0)/(7.0-5.0)
            WHEN t.years_to_maturity <= 10.0
                THEN 77.0+(78.0-77.0)*(t.years_to_maturity-7.0)/(10.0-7.0)
            WHEN t.years_to_maturity <= 20.0
                THEN 78.0+(57.0-78.0)*(t.years_to_maturity-10.0)/(20.0-10.0)
            WHEN t.years_to_maturity <= 30.0
                THEN 57.0+(34.0-57.0)*(t.years_to_maturity-20.0)/(30.0-20.0)
            ELSE 34.0
        END AS ir_shock_bps,

        -- CS shock (by issuer type and rating)
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
        END AS cs_shock_bps,

        -- FUND_ARIS: leverage factor
        CASE WHEN t.instrument_type = 'FUND' AND t.asset_type = 'FUND_ARIS'
        THEN CASE
            WHEN t.fund_underlying_index LIKE '%x7%'
              OR t.fund_underlying_index LIKE '% 7x%'             THEN 7.0
            WHEN t.fund_underlying_index LIKE '%5X%'
              OR t.fund_underlying_index LIKE '%x5%'              THEN 5.0
            WHEN t.fund_underlying_index LIKE '%x3%'
              OR t.fund_underlying_index LIKE '%3x%'
              OR t.fund_underlying_index LIKE '%Triple%'
              OR t.fund_underlying_index LIKE '%Super Lever%'
              OR t.fund_underlying_index LIKE '%Super Short%'     THEN 3.0
            WHEN t.fund_underlying_index LIKE '%x2%'
              OR t.fund_underlying_index LIKE '%2x%'
              OR t.fund_underlying_index LIKE '%2X%'
              OR t.fund_underlying_index LIKE '%Double%'
              OR t.fund_underlying_index LIKE '%(-2x)%'
              OR t.fund_underlying_index LIKE '%Leveraged%'
              OR t.fund_underlying_index LIKE '%Lev%'             THEN 2.0
            ELSE 1.0 END
        ELSE NULL END AS aris_leverage,

        -- FUND_ARIS: direction (short/inverse = -1, long = +1)
        CASE WHEN t.instrument_type = 'FUND' AND t.asset_type = 'FUND_ARIS'
        THEN CASE
            WHEN t.fund_underlying_index LIKE '%Inverse%'
              OR t.fund_underlying_index LIKE '%(-2x)%'
              OR t.fund_underlying_index LIKE '%Short%'           THEN -1.0
            ELSE 1.0 END
        ELSE NULL END AS aris_direction,

        -- FUND_ARIS: underlying asset class
        CASE WHEN t.instrument_type = 'FUND' AND t.asset_type = 'FUND_ARIS'
        THEN CASE
            WHEN t.fund_underlying_index LIKE '%Bund%'
              OR t.fund_underlying_index LIKE '%BTP%'
              OR t.fund_underlying_index LIKE '%Treasury%'
              OR t.fund_underlying_index LIKE '%Gilt%'
              OR t.fund_underlying_index LIKE '%iBoxx%'           THEN 'BOND'
            WHEN t.fund_underlying_index LIKE '%MSFXSM%'
              OR t.fund_underlying_index LIKE '%Dollar%'
              OR t.fund_underlying_index LIKE '%Yen%'
              OR t.fund_underlying_index LIKE '% GBP%'
              OR t.fund_underlying_index LIKE '%Franc%'
              OR t.fund_underlying_index LIKE '%Krone%'
              OR t.fund_underlying_index LIKE '%Renminbi%'
              OR t.fund_underlying_index LIKE '%Currency%'        THEN 'FX'
            WHEN t.fund_underlying_index LIKE '%Crude%'
              OR t.fund_underlying_index LIKE '%Brent%'
              OR t.fund_underlying_index LIKE '%WTI%'
              OR t.fund_underlying_index LIKE '%Natural Gas%'
              OR t.fund_underlying_index LIKE '%Gold%'
              OR t.fund_underlying_index LIKE '%Silver%'
              OR t.fund_underlying_index LIKE '%Nickel%'
              OR t.fund_underlying_index LIKE '%Palladium%'
              OR t.fund_underlying_index LIKE '%Copper%'
              OR t.fund_underlying_index LIKE '%Petroleum%'       THEN 'COMMODITY'
            ELSE 'EQUITY' END
        ELSE NULL END AS aris_underlying

    FROM teams_prd.risk_function_publish.pbl__risk_function_mrm_book_trading_valuation t
    WHERE t.report_date      = '2025-09-30'
      AND t.instrument_type IS NOT NULL
),

-- ============================================================
-- STEP 2: SHOCKED — all shock components at row level
-- ============================================================
shocked AS (
    SELECT
        b.*,

        -- Primary shock (row level, directional)
        CASE
            WHEN b.instrument_type = 'BOND'
            THEN -1.0 * b.duration_mod * b.market_value_eur
                 * (b.ir_shock_bps + b.cs_shock_bps) / 10000.0
            WHEN b.instrument_type IN ('STOCK','SYNTHETIC')
                 AND b.asset_type IN ('EQUITY','STOCK')
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.506
            WHEN b.instrument_type = 'DERIVATIVE' AND b.asset_type = 'STOCK'
            THEN 0.0
            WHEN b.instrument_type = 'FUND' AND b.asset_type = 'FUND_EQUITY'
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.506
            WHEN b.instrument_type = 'FUND'
                 AND b.asset_type IN ('FUND_BONDS','FUND_FIXED_INCOME')
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.506
            WHEN b.instrument_type = 'FUND' AND b.asset_type = 'FUND_MULTI_ASSET'
            THEN -1.0 * b.market_value_eur * 0.506
            WHEN b.instrument_type = 'FUND' AND b.asset_type = 'FUND_MONEY_MARKET'
            THEN 0.0
            WHEN b.instrument_type = 'FUND' AND b.asset_type = 'FUND_OTHER'
            THEN CASE
                WHEN b.fund_underlying_index LIKE '%Gold%'
                  OR b.fund_underlying_index LIKE '%Silver%'
                  OR b.fund_underlying_index LIKE '%Platinum%'
                  OR b.fund_underlying_index LIKE '%Palladium%'
                  OR b.fund_underlying_index LIKE '%Precious Metal%'
                  OR b.fund_underlying_index LIKE '%Crude%'
                  OR b.fund_underlying_index LIKE '%Brent%'
                  OR b.fund_underlying_index LIKE '%WTI%'
                  OR b.fund_underlying_index LIKE '%Natural Gas%'
                  OR b.fund_underlying_index LIKE '%Energy%'
                  OR b.fund_underlying_index LIKE '%Petroleum%'
                  OR b.fund_underlying_index LIKE '%Commodity%'
                  OR b.fund_underlying_index LIKE '%Metal%'
                  OR b.fund_underlying_index LIKE '%Copper%'
                  OR b.fund_underlying_index LIKE '%Nickel%'
                  OR b.fund_underlying_index LIKE '%Alumin%'
                  OR b.fund_underlying_index LIKE '%Bloomberg%'
                  OR b.fund_underlying_index LIKE '%Optimis%Roll%'
                THEN -1.0 * b.market_value_eur * 0.434
                WHEN b.fund_underlying_index LIKE '%EPRA%'
                  OR b.fund_underlying_index LIKE '%REIT%'
                  OR b.fund_underlying_index LIKE '%Real Estate%'
                THEN -1.0 * b.market_value_eur * 0.220
                ELSE -1.0 * b.market_value_eur * 0.506
            END
            WHEN b.instrument_type = 'FUND' AND b.asset_type = 'FUND_ARIS'
            THEN b.aris_direction * b.aris_leverage * (-1.0) * b.market_value_eur *
                 CASE b.aris_underlying
                     WHEN 'EQUITY'    THEN 0.506
                     WHEN 'BOND'      THEN 0.506
                     WHEN 'FX'        THEN 0.044
                     WHEN 'COMMODITY' THEN 0.434
                     ELSE                  0.506
                 END
            WHEN b.instrument_type = 'FX' AND b.asset_type = 'FX_SPOT'
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.044
            WHEN b.instrument_type = 'CRYPTO' THEN 0.0
            ELSE -1.0 * b.market_value_eur * 0.506
        END AS mv_change_primary,

        -- CS-only component (SNr 9 / SNr 11 split — bonds only)
        CASE WHEN b.instrument_type = 'BOND'
        THEN -1.0 * b.duration_mod * b.market_value_eur
             * b.cs_shock_bps / 10000.0
        ELSE 0.0 END AS mv_change_cs_only,

        -- IR-only component (SNr 11 — bonds only)
        CASE WHEN b.instrument_type = 'BOND'
        THEN -1.0 * b.duration_mod * b.market_value_eur
             * b.ir_shock_bps / 10000.0
        ELSE 0.0 END AS mv_change_ir_only,

        -- Combined shock = primary + FX shock for non-EUR bonds
        -- Per Para. 93(vi): non-EUR bonds get both shocks
        -- For all other instruments: combined = primary only
        CASE
            WHEN b.instrument_type = 'BOND' AND b.currency != 'EUR'
            THEN
                -- Primary (IR + CS) shock
                (-1.0 * b.duration_mod * b.market_value_eur
                 * (b.ir_shock_bps + b.cs_shock_bps) / 10000.0)
                +
                -- Additional FX shock on post-primary-shock MV
                (SIGN(b.quantity) * (-1.0)
                 * (b.market_value_eur +
                    (-1.0 * b.duration_mod * b.market_value_eur
                     * (b.ir_shock_bps + b.cs_shock_bps) / 10000.0))
                 * 0.044)
            WHEN b.instrument_type = 'BOND' AND b.currency = 'EUR'
            THEN -1.0 * b.duration_mod * b.market_value_eur
                 * (b.ir_shock_bps + b.cs_shock_bps) / 10000.0
            WHEN b.instrument_type IN ('STOCK','SYNTHETIC')
                 AND b.asset_type IN ('EQUITY','STOCK')
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.506
            WHEN b.instrument_type = 'DERIVATIVE' AND b.asset_type = 'STOCK'
            THEN 0.0
            WHEN b.instrument_type = 'FUND' AND b.asset_type = 'FUND_EQUITY'
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.506
            WHEN b.instrument_type = 'FUND'
                 AND b.asset_type IN ('FUND_BONDS','FUND_FIXED_INCOME')
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.506
            WHEN b.instrument_type = 'FUND' AND b.asset_type = 'FUND_MULTI_ASSET'
            THEN -1.0 * b.market_value_eur * 0.506
            WHEN b.instrument_type = 'FUND' AND b.asset_type = 'FUND_MONEY_MARKET'
            THEN 0.0
            WHEN b.instrument_type = 'FUND' AND b.asset_type = 'FUND_OTHER'
            THEN CASE
                WHEN b.fund_underlying_index LIKE '%Gold%'
                  OR b.fund_underlying_index LIKE '%Silver%'
                  OR b.fund_underlying_index LIKE '%Platinum%'
                  OR b.fund_underlying_index LIKE '%Palladium%'
                  OR b.fund_underlying_index LIKE '%Precious Metal%'
                  OR b.fund_underlying_index LIKE '%Crude%'
                  OR b.fund_underlying_index LIKE '%Brent%'
                  OR b.fund_underlying_index LIKE '%WTI%'
                  OR b.fund_underlying_index LIKE '%Natural Gas%'
                  OR b.fund_underlying_index LIKE '%Energy%'
                  OR b.fund_underlying_index LIKE '%Petroleum%'
                  OR b.fund_underlying_index LIKE '%Commodity%'
                  OR b.fund_underlying_index LIKE '%Metal%'
                  OR b.fund_underlying_index LIKE '%Copper%'
                  OR b.fund_underlying_index LIKE '%Nickel%'
                  OR b.fund_underlying_index LIKE '%Alumin%'
                  OR b.fund_underlying_index LIKE '%Bloomberg%'
                  OR b.fund_underlying_index LIKE '%Optimis%Roll%'
                THEN -1.0 * b.market_value_eur * 0.434
                WHEN b.fund_underlying_index LIKE '%EPRA%'
                  OR b.fund_underlying_index LIKE '%REIT%'
                  OR b.fund_underlying_index LIKE '%Real Estate%'
                THEN -1.0 * b.market_value_eur * 0.220
                ELSE -1.0 * b.market_value_eur * 0.506
            END
            WHEN b.instrument_type = 'FUND' AND b.asset_type = 'FUND_ARIS'
            THEN b.aris_direction * b.aris_leverage * (-1.0) * b.market_value_eur *
                 CASE b.aris_underlying
                     WHEN 'EQUITY'    THEN 0.506
                     WHEN 'BOND'      THEN 0.506
                     WHEN 'FX'        THEN 0.044
                     WHEN 'COMMODITY' THEN 0.434
                     ELSE                  0.506
                 END
            WHEN b.instrument_type = 'FX' AND b.asset_type = 'FX_SPOT'
            THEN SIGN(b.quantity) * (-1.0) * b.market_value_eur * 0.044
            WHEN b.instrument_type = 'CRYPTO' THEN 0.0
            ELSE -1.0 * b.market_value_eur * 0.506
        END AS mv_change_combined

    FROM base b
),

-- ============================================================
-- BOND METRICS: SNr 6 + SNr 7
-- Computed on raw positions, joined into section_a on znr
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

        -- SNr 6: volume-weighted average residual maturity (years)
        ROUND(
            SUM(ABS(close_mid_price_dirty * quantity * fx_rate_eur) * years_to_maturity)
            / NULLIF(SUM(ABS(close_mid_price_dirty * quantity * fx_rate_eur)), 0)
        , 2) AS snr6_avg_restlaufzeit,

        -- SNr 7: Zinssensitivität — EUR change for +100 bps parallel shift
        ROUND(
            SUM(-1.0 * duration_mod
                * (close_mid_price_dirty * quantity * fx_rate_eur)
                * 0.01)
        , 2) AS snr7_zinssensitivitaet

    FROM teams_prd.risk_function_publish.pbl__risk_function_mrm_book_trading_valuation
    WHERE report_date     = '2025-09-30'
      AND instrument_type = 'BOND'
    GROUP BY znr
),

-- ============================================================
-- SECTION A: Main positions ZNr 2-43
-- GROUP BY znr only — shorts merged via ABS(), flags via LISTAGG
-- Bond metrics joined in via LEFT JOIN
-- ============================================================
section_a AS (
    SELECT
        'A_MAIN'                                        AS section,
        s.znr,
        NULL::VARCHAR                                   AS currency,

        -- All position flags present in this ZNr (e.g. "CHECK_SHORT_BOND | OK")
        LISTAGG(DISTINCT s.position_flag, ' | ')
            WITHIN GROUP (ORDER BY s.position_flag)     AS position_flag,

        COUNT(*)                                        AS position_count,

        -- SNr 1/2/3: GROSS MV before shock
        -- ABS for bonds/funds (gross reporting per guidelines)
        -- NET (signed) for equities (guidelines: "Long- und Short-Positionen saldieren")
        SUM(CASE WHEN s.snr_maturity_bucket = 'SNr1_under_1Y'
            THEN CASE WHEN s.znr = 'ZNr18_Equity'
                 THEN s.market_value_eur
                 ELSE ABS(s.market_value_eur) END
            ELSE 0 END)                                 AS snr1_mv_under_1y,

        SUM(CASE WHEN s.snr_maturity_bucket = 'SNr2_1Y_to_5Y'
            THEN CASE WHEN s.znr = 'ZNr18_Equity'
                 THEN s.market_value_eur
                 ELSE ABS(s.market_value_eur) END
            ELSE 0 END)                                 AS snr2_mv_1y_to_5y,

        SUM(CASE WHEN s.snr_maturity_bucket = 'SNr3_over_5Y'
            THEN CASE WHEN s.znr = 'ZNr18_Equity'
                 THEN s.market_value_eur
                 ELSE ABS(s.market_value_eur) END
            ELSE 0 END)                                 AS snr3_mv_over_5y,

        -- SNr 4: Floater share = 0 (TR has no floating rate bonds)
        0.0                                             AS snr4_floater_share,

        -- SNr 5: Book value = NULL (to be populated from accounting system)
        NULL::FLOAT                                     AS snr5_book_value,

        -- SNr 6: Avg residual maturity — from bond_metrics JOIN (NULL for non-bonds)
        bm.snr6_avg_restlaufzeit                        AS snr6_avg_restlaufzeit,

        -- SNr 7: Zinssensitivität — from bond_metrics JOIN (NULL for non-bonds)
        bm.snr7_zinssensitivitaet                       AS snr7_zinssensitivitaet,

        -- SNr 8/9/10: MV change split by maturity bucket
        -- Uses COMBINED shock (primary + FX for non-EUR bonds)
        SUM(CASE WHEN s.snr_maturity_bucket = 'SNr1_under_1Y'
            THEN s.mv_change_combined ELSE 0 END)       AS snr8_shock_under_1y,

        SUM(CASE WHEN s.snr_maturity_bucket = 'SNr2_1Y_to_5Y'
            THEN s.mv_change_combined ELSE 0 END)       AS snr9_shock_1y_to_5y,

        SUM(CASE WHEN s.snr_maturity_bucket = 'SNr3_over_5Y'
            THEN s.mv_change_combined ELSE 0 END)       AS snr10_shock_over_5y,

        -- SNr 11: IR-only MV change (bonds only — feeds ZNr 46 BFA3 calculation)
        SUM(s.mv_change_ir_only)                        AS snr11_ir_only,

        -- SNr 12: Kursreserven = NULL (requires book value — not available in this table)
        NULL::FLOAT                                     AS snr12_kursreserven,

        -- SNr 13: P&L effective MV change = combined shock total
        -- No Kursreserven reduction (SNr 12 = NULL)
        -- No hedge reduction (SNr 14/15 = 0%)
        SUM(s.mv_change_combined)                       AS snr13_pl_effective,

        -- SNr 14/15: Besicherungsquoten = 0% (no §254 HGB hedges at TR)
        0.0                                             AS snr14_hedge_ratio_ir,
        0.0                                             AS snr15_hedge_ratio_cs,

        -- FX columns: not applicable for section A
        NULL::FLOAT                                     AS fx_snr1_post_shock,
        NULL::FLOAT                                     AS fx_snr8_shock,
        NULL::FLOAT                                     AS fx_snr14_gross,
        NULL::VARCHAR                                   AS fx_status

    FROM shocked s
    LEFT JOIN bond_metrics bm ON s.znr = bm.znr
    WHERE s.znr NOT IN ('OUT_OF_SCOPE','OUT_OF_SCOPE_REVIEW','ZNr24_FX_Direct')
    GROUP BY s.znr, bm.snr6_avg_restlaufzeit, bm.snr7_zinssensitivitaet
),

-- ============================================================
-- SECTION B: ZNr 24 — ALL non-EUR positions outside funds
-- Regulation: Para. 93(vi) — "außerhalb des Investmentvermögens"
-- Post-primary-shock MV per Para. 93(vi), then -4.4% FX shock
-- Materiality threshold: 0.03% × CET1 556M = 166,800 EUR
-- ============================================================
znr24_base AS (
    SELECT
        s.currency,
        SUM(s.market_value_eur + s.mv_change_primary)  AS snr1_post_shock,
        SUM(CASE WHEN s.market_value_eur > 0
                 THEN s.market_value_eur ELSE 0 END)    AS snr14_gross,
        SUM(s.market_value_eur)                         AS mv_before,
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
            WHEN z.snr1_post_shock > p.cet1_eur * p.fx_threshold_pct THEN '✅ REPORTABLE'
            WHEN z.snr1_post_shock <= 0                               THEN '⛔ NET SHORT'
            ELSE '⚪ BELOW THRESHOLD'
        END                                             AS position_flag,
        z.n_pos                                         AS position_count,
        NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        0.0, NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        NULL::FLOAT                                     AS snr11_ir_only,
        NULL::FLOAT                                     AS snr12_kursreserven,
        ROUND(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) ELSE 0 END, 2)
                                                        AS snr13_pl_effective,
        NULL::FLOAT, NULL::FLOAT,
        ROUND(z.snr1_post_shock, 2)                     AS fx_snr1_post_shock,
        ROUND(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) ELSE 0 END, 2)
                                                        AS fx_snr8_shock,
        ROUND(z.snr14_gross, 2)                         AS fx_snr14_gross,
        CASE
            WHEN z.snr1_post_shock > p.cet1_eur * p.fx_threshold_pct THEN '✅ REPORTABLE'
            WHEN z.snr1_post_shock <= 0                               THEN '⛔ NET SHORT'
            ELSE '⚪ BELOW THRESHOLD'
        END                                             AS fx_status
    FROM znr24_base z
    CROSS JOIN params p
    WHERE z.snr1_post_shock > 0
),

section_b_total AS (
    SELECT
        'B_ZNr24_FX_DIRECT'                            AS section,
        'ZNr24_TOTAL_REPORTABLE'::VARCHAR               AS znr,
        'ALL_REPORTABLE_CURRENCIES'::VARCHAR            AS currency,
        '✅ TOTAL'                                      AS position_flag,
        SUM(z.n_pos)                                    AS position_count,
        NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        0.0, NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        NULL::FLOAT, NULL::FLOAT,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) ELSE 0 END), 2)
                                                        AS snr13_pl_effective,
        NULL::FLOAT, NULL::FLOAT,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock ELSE 0 END), 2)    AS fx_snr1_post_shock,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) ELSE 0 END), 2)
                                                        AS fx_snr8_shock,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr14_gross ELSE 0 END), 2)        AS fx_snr14_gross,
        '✅ TOTAL'                                      AS fx_status
    FROM znr24_base z
    CROSS JOIN params p
    WHERE z.snr1_post_shock > p.cet1_eur * p.fx_threshold_pct
),

-- ============================================================
-- SECTION C: ZNr 25 — ALL non-EUR fund positions
-- Regulation: Para. 93(vi) — "innerhalb des Investmentvermögens"
-- Post-primary-shock MV, then -4.4% FX shock
-- ============================================================
znr25_base AS (
    SELECT
        s.currency,
        SUM(s.market_value_eur + s.mv_change_primary)  AS snr1_post_shock,
        SUM(s.market_value_eur)                         AS mv_before,
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
            WHEN z.snr1_post_shock > p.cet1_eur * p.fx_threshold_pct THEN '✅ REPORTABLE'
            WHEN z.snr1_post_shock <= 0                               THEN '⛔ NET SHORT'
            ELSE '⚪ BELOW THRESHOLD'
        END                                             AS position_flag,
        z.n_pos                                         AS position_count,
        NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        0.0, NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        NULL::FLOAT, NULL::FLOAT,
        ROUND(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) ELSE 0 END, 2)
                                                        AS snr13_pl_effective,
        NULL::FLOAT, NULL::FLOAT,
        ROUND(z.snr1_post_shock, 2)                     AS fx_snr1_post_shock,
        ROUND(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) ELSE 0 END, 2)
                                                        AS fx_snr8_shock,
        NULL::FLOAT                                     AS fx_snr14_gross,
        CASE
            WHEN z.snr1_post_shock > p.cet1_eur * p.fx_threshold_pct THEN '✅ REPORTABLE'
            WHEN z.snr1_post_shock <= 0                               THEN '⛔ NET SHORT'
            ELSE '⚪ BELOW THRESHOLD'
        END                                             AS fx_status
    FROM znr25_base z
    CROSS JOIN params p
    WHERE z.snr1_post_shock > 0
),

section_c_total AS (
    SELECT
        'C_ZNr25_FX_FUNDS'                             AS section,
        'ZNr25_TOTAL_REPORTABLE'::VARCHAR               AS znr,
        'ALL_REPORTABLE_CURRENCIES'::VARCHAR            AS currency,
        '✅ TOTAL'                                      AS position_flag,
        SUM(z.n_pos)                                    AS position_count,
        NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        0.0, NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        NULL::FLOAT, NULL::FLOAT,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) ELSE 0 END), 2)
                                                        AS snr13_pl_effective,
        NULL::FLOAT, NULL::FLOAT,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock ELSE 0 END), 2)    AS fx_snr1_post_shock,
        ROUND(SUM(CASE WHEN z.snr1_post_shock > 0
             THEN z.snr1_post_shock * (-0.044) ELSE 0 END), 2)
                                                        AS fx_snr8_shock,
        NULL::FLOAT                                     AS fx_snr14_gross,
        '✅ TOTAL'                                      AS fx_status
    FROM znr25_base z
    CROSS JOIN params p
    WHERE z.snr1_post_shock > p.cet1_eur * p.fx_threshold_pct
)

-- ============================================================
-- FINAL OUTPUT
-- Section A: Main positions ZNr 2-43 (one row per ZNr)
-- Section B: ZNr 24 FX direct (one row per currency + total)
-- Section C: ZNr 25 FX funds (one row per currency + total)
-- Single ORDER BY at end — no ORDER BY in individual branches
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
ORDER BY section, znr, position_flag
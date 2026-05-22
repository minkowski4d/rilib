# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Financial Model Validation Framework for German banking institutions. Provides structured methodology and templates for validating Market Risk and Liquidity Risk models in compliance with BaFin, MaRisk, and EBA requirements.

**Location:** `/projects/validation/` within the `risk_pylibrary` repository

**Development Phases:**
- **Phase 1 (Current):** Conceptual framework and documentation
- **Phase 2 (Future):** Python automation framework integrating with existing risk_pylibrary models

## Integration with risk_pylibrary

This validation framework is integrated into the main risk modeling repository and validates models across multiple modules:

### Models to Validate

**Market Risk Models** (in `risk_models/` and `projects/`):
- `risk_models/mc_stress_testing.py` - Monte Carlo stress testing models
- `risk_models/garch_models.py` - GARCH volatility models
- `risk_models/econometrics.py` - Econometric models for risk forecasting
- `projects/stress_testing/mr_stress_test.py` - Market risk stress testing framework

**Liquidity Risk Models** (in `projects/liquidity_risk/`):
- `liquidity_risk/maturity_ladder.py` - Maturity ladder calculations
- `liquidity_risk/predict_reg_data.py` - Regulatory data forecasting
- `liquidity_risk/lqr_support_data.py` - Liquidity risk support functions

**P&L Models** (in `risk_models/` and `projects/pnl/`):
- `risk_models/pnl_fifo.py` - FIFO P&L attribution (43KB, complex)
- `risk_models/pnl_support.py` - P&L support calculations (94KB)
- `projects/pnl/pnl_tr.py` - Transaction-based P&L
- `projects/pnl/pnl_bt.py` - Backtesting P&L

**Other Risk Models**:
- `projects/irrbb/` - Interest Rate Risk in Banking Book
- `projects/risk_factor_mapping/` - Risk factor mapping
- `projects/econometrics/` - Econometric model implementations

### Existing Validation Infrastructure

The repository already contains validation tools in `risk_analytics/model_validation.py`:
- Monte Carlo convergence tests (`mc_os_convergence_test`)
- VaR backtesting functionality
- Integration with `risk_models/mc_models.py` and `risk_models/econometrics.py`

The new validation framework will **extend and standardize** these existing capabilities with regulatory reporting and comprehensive validation methodology.

## Project Architecture

### High-Level Structure
```
projects/validation/
├── docs/
│   ├── concepts/          # Regulatory and methodological framework documents
│   └── templates/         # Standardized validation report templates
├── src/validation/        # Python framework (Phase 2 - not yet implemented)
└── tests/                 # Test suite (Phase 2 - not yet implemented)
```

### Integration Points with risk_pylibrary
```python
# Example: Validation framework can directly import and test models
from risk_pylibrary.risk_models import mc_stress_testing, econometrics, garch_models
from risk_pylibrary.projects.liquidity_risk import maturity_ladder
from risk_pylibrary.risk_analytics import model_validation  # Existing validation tools
import pandas as pd

# Validation code will extend existing capabilities
from validation.src.validation.backtesting import validate_var_model
from validation.src.validation.reporting import generate_validation_report
```

### Key Conceptual Components

**Validation Framework** (`docs/concepts/validation_framework_concept.md`):
- Defines 5 core validation areas: Conceptual Soundness, Data Quality, Implementation, Ongoing Monitoring, Outcomes Analysis
- Establishes 4-tier rating system: Satisfactory, Satisfactory with Reservations, Unsatisfactory, Not Validated
- Finding severity: Critical (immediate), Major (3 months), Minor (6 months), Observation
- Regulatory mapping to MaRisk AT 4.3.2, EBA guidelines, CRR/CRD IV

**Validation Report Template** (`docs/templates/validation_report_template.md`):
- 9 main sections + appendices (follows regulatory structure)
- Executive summary with overall rating
- Document control and approval workflow
- Bilingual consideration (German/English for BaFin submissions)

## Domain-Specific Context

### Regulatory Environment
- **BaFin (Bundesanstalt für Finanzdienstleistungsaufsicht):** German financial regulator
- **MaRisk AT 4.3.2:** Requires independent validation of material models
- **EBA/GL/2019/01:** Internal governance guidelines
- **Validation frequency:** Minimum annually for material models

### Model Types in Scope

**Models Currently in risk_pylibrary:**

1. **Market Risk Models:**
   - **VaR Models:** Historical simulation and Monte Carlo approaches (in `risk_models/econometrics.py`, `mc_models.py`)
   - **GARCH Models:** Volatility forecasting (`risk_models/garch_models.py`)
   - **Stress Testing:** Monte Carlo stress testing framework (`risk_models/mc_stress_testing.py`, `projects/stress_testing/mr_stress_test.py`)
   - **Risk Engines:** Core risk calculation engines (`risk_analytics/risk_engines.py`)

2. **Liquidity Risk Models:**
   - **Maturity Ladder:** Cash flow bucketing and gap analysis (`projects/liquidity_risk/maturity_ladder.py`)
   - **Regulatory Forecasting:** LCR/NSFR component predictions (`projects/liquidity_risk/predict_reg_data.py`)
   - **Behavioral Models:** Deposit and credit line modeling (in liquidity_risk support modules)

3. **P&L Attribution Models:**
   - **FIFO P&L Engine:** Complex P&L attribution using FIFO methodology (`risk_models/pnl_fifo.py`)
   - **Transaction P&L:** Trade-level P&L calculation (`projects/pnl/pnl_tr.py`)
   - **Backtesting P&L:** Historical P&L validation (`projects/pnl/pnl_bt.py`)

4. **Forecasting Models:**
   - **OLS Models:** Ordinary Least Squares predictions (`risk_models/ols_predict_models.py`)
   - **SARIMA Models:** Seasonal time series forecasting (`risk_models/sarima_models.py`)
   - **Theta Models:** Theta method forecasting (`risk_models/theta_models.py`)

5. **Other Risk Models:**
   - **IRRBB:** Interest Rate Risk in Banking Book (`projects/irrbb/`)
   - **Risk Factor Mapping:** Mapping of instruments to risk factors (`projects/risk_factor_mapping/`)

**Validation Coverage:**
- All Tier 1 models (material impact on risk metrics and capital)
- Annual validation for market and liquidity risk models
- Post-implementation validation for new models
- Change-triggered re-validation for material model changes

### Critical Validation Principles
- **Independence:** Validation team must be independent from model development
- **Documentation:** Comprehensive audit trail required for BaFin inspections
- **Conservative approach:** German regulatory culture emphasizes prudence
- **Limitation identification:** Models must clearly document assumptions and limitations

## Future Development Guidelines (Phase 2)

### When Implementing Python Framework

**Architecture Pattern:**
- Modular design: separate modules for each validation area
- Data ingestion layer: standardized interfaces for different data sources
- Analysis engine: statistical tests, backtesting, sensitivity analysis
- Report generation: automated markdown/PDF generation from templates
- Finding tracker: database for managing findings and remediation

**Technology Stack Considerations:**
- **Data manipulation:** pandas, numpy
- **Statistics:** scipy, statsmodels
- **Visualization:** matplotlib, plotly
- **Testing:** pytest
- **Documentation:** sphinx
- **German language support:** Consider i18n for BaFin reporting

**Code Organization Pattern:**
```python
projects/validation/src/validation/
├── core/                      # Core validation engine
│   ├── model_inventory.py     # Model register and classification
│   ├── validation_workflow.py # Orchestration of validation steps
│   └── rating_engine.py       # Rating calculation logic
├── data/                      # Data quality checks
│   ├── completeness.py        # Missing data detection
│   ├── accuracy.py            # Data accuracy verification
│   └── consistency.py         # Cross-system reconciliation
├── backtesting/               # Market risk backtesting
│   ├── var_backtest.py        # VaR exception counting and traffic light
│   ├── es_backtest.py         # Expected Shortfall validation
│   ├── garch_validation.py    # GARCH model stability tests
│   └── convergence_tests.py   # MC convergence (extends risk_analytics/model_validation.py)
├── liquidity/                 # Liquidity-specific analyses
│   ├── lcr_validation.py      # LCR component validation
│   ├── maturity_validation.py # Maturity ladder verification
│   └── behavioral_tests.py    # Behavioral assumption testing
├── pnl/                       # P&L model validation
│   ├── fifo_validation.py     # Validate pnl_fifo.py calculations
│   └── attribution_tests.py   # P&L attribution accuracy
├── reporting/                 # Report generation
│   ├── template_engine.py     # Populate markdown templates
│   ├── chart_generator.py     # Validation charts (extends risk_analytics/ra_charting.py)
│   └── pdf_exporter.py        # Export to PDF
├── integrations/              # Integration with existing risk_pylibrary modules
│   ├── model_loaders.py       # Load and instantiate risk_models
│   ├── data_connectors.py     # Reuse existing data pipelines
│   └── shared_utils.py        # Bridge to risk_pylibrary.tools
└── utils/                     # Shared utilities
    ├── german_i18n.py         # German translation support
    └── bafin_helpers.py       # BaFin-specific utilities
```

**Key Functionality to Implement:**

1. **Model Inventory Management**
   - Register all models from `risk_models/` and `projects/`
   - Classify by materiality and regulatory impact
   - Track model versions and change history
   - Link to model owners and documentation

2. **Extended Backtesting (building on `risk_analytics/model_validation.py`)**
   - Wrap existing `mc_os_convergence_test` with regulatory reporting
   - Add traffic light approach for VaR (Basel green/yellow/red zones)
   - GARCH model parameter stability over time
   - Stress test scenario validation

3. **Data Quality Automation**
   - Validate data inputs to `econometrics.py`, `mc_stress_testing.py`
   - Check completeness of time series data
   - Verify data transformations in `pnl_support.py`
   - Reconciliation across data sources

4. **Model-Specific Validation Modules**
   - **VaR/ES Validation:** Test models in `risk_models/econometrics.py`, `mc_models.py`
   - **GARCH Validation:** Parameter stability and forecast accuracy for `garch_models.py`
   - **Liquidity Validation:** Component verification for `liquidity_risk/maturity_ladder.py`
   - **P&L Validation:** FIFO logic verification for `pnl_fifo.py` (43KB complex code)
   - **Forecasting Validation:** Accuracy metrics for `ols_predict_models.py`, `sarima_models.py`, `theta_models.py`

5. **Report Generator**
   - Populate `docs/templates/validation_report_template.md`
   - Auto-generate charts using `risk_analytics/ra_charting.py`
   - Bilingual support (German/English)
   - Export to PDF for BaFin submissions

6. **Finding Tracker**
   - Database of validation findings
   - Severity classification (Critical/Major/Minor/Observation)
   - Remediation status tracking
   - Integration with model change management

7. **Dashboard and Monitoring**
   - Validation program metrics (coverage, timeliness)
   - Model performance KPIs (backtesting results, stability)
   - Finding status overview
   - Regulatory reporting preparation

### Integration Patterns with risk_pylibrary

**Example 1: Validating VaR Models**
```python
# Import existing risk models
from risk_pylibrary.risk_models import econometrics as ec
from risk_pylibrary.risk_models import mc_models
from risk_pylibrary.risk_analytics.model_validation import mc_os_convergence_test

# Import validation framework
from validation.src.validation.backtesting import var_backtest
from validation.src.validation.reporting import generate_validation_report

# Run existing convergence test
convergence_results = mc_os_convergence_test(rets, wgts, qtl=0.99, ...)

# Extend with regulatory backtesting
backtest_results = var_backtest.traffic_light_test(convergence_results, ...)

# Generate regulatory report
report = generate_validation_report(
    model_name="VaR Historical Simulation",
    model_code="risk_models.econometrics.sim2VaR",
    backtest_results=backtest_results,
    template="docs/templates/validation_report_template.md"
)
```

**Example 2: Validating Liquidity Models**
```python
# Import liquidity risk model
from risk_pylibrary.projects.liquidity_risk import maturity_ladder, predict_reg_data

# Import validation framework
from validation.src.validation.liquidity import maturity_validation, lcr_validation

# Validate maturity ladder calculations
ml_validation = maturity_validation.validate_bucketing(
    maturity_ladder_output=...,
    input_data=...,
    expected_results=...
)

# Validate LCR component predictions
lcr_validation_results = lcr_validation.validate_components(
    predict_reg_data_output=...,
    actual_regulatory_data=...
)
```

**Example 3: Validating P&L Models**
```python
# Import complex P&L model (43KB FIFO logic)
from risk_pylibrary.risk_models.pnl_fifo import *
from risk_pylibrary.risk_models.pnl_support import *

# Import validation framework
from validation.src.validation.pnl import fifo_validation, attribution_tests

# Validate FIFO calculation logic
fifo_test_results = fifo_validation.test_fifo_logic(
    sample_trades=...,
    expected_pnl=...,
    tolerance=0.01
)

# Validate P&L attribution accuracy
attribution_results = attribution_tests.compare_with_actuals(
    model_pnl=...,
    actual_pnl=...,
    breakdown_by=['instrument', 'desk', 'risk_factor']
)
```

**Reusing Existing Infrastructure:**
- **Data handling:** Use `risk_pylibrary.tools.pandas_patched` (already standardized)
- **Charting:** Extend `risk_analytics/ra_charting.py` for validation visuals
- **Risk calculations:** Leverage existing functions in `risk_models/econometrics.py`
- **Monte Carlo:** Build on `risk_models/mc_models.py` and `mc_stress_testing.py`

### Design Principles
- **Auditability:** All calculations must be traceable and reproducible
- **Flexibility:** Support multiple model types and methodologies across risk_pylibrary
- **Scalability:** Handle model inventory of 100+ models from all risk_models/ and projects/
- **Non-invasive:** Validation code imports and tests existing models without modifying them
- **Documentation:** Inline comments in German/English where regulatory terms used
- **Version control:** Track model versions and validation results over time

## Terminology Notes

### German-English Regulatory Terms
- **MaRisk:** Mindestanforderungen an das Risikomanagement (Minimum Requirements for Risk Management)
- **ICAAP:** Internal Capital Adequacy Assessment Process
- **ILAAP:** Internal Liquidity Adequacy Assessment Process
- **VaR:** Value-at-Risk (Risikowert)
- **LCR:** Liquidity Coverage Ratio (Liquiditätsdeckungsquote)
- **NSFR:** Net Stable Funding Ratio (strukturelle Liquiditätsquote)

### Validation-Specific Terms
- **Conceptual Soundness:** Theoretical validity of model methodology
- **Backtesting:** Historical comparison of model predictions vs. actual outcomes
- **Traffic Light Approach:** Regulatory framework for assessing VaR model exceptions (Green/Yellow/Red zones)
- **Model Tier Classification:** Risk-based categorization (Tier 1: highest risk/materiality)

## risk_pylibrary Specific Considerations

### Repository Structure
- **Location:** `/projects/validation/` alongside other risk projects
- **Python version:** 3.10 < Python <= 3.12 (per repo README)
- **Dependency management:** Uses `pyproject.toml` with uv
- **Environment:** Virtual environment in `venv/`

### Dependencies Already Available
- `pandas` (via `risk_pylibrary.tools.pandas_patched`)
- `numpy`, `scipy` (used throughout risk_models)
- Charting tools (`risk_pylibrary.tools.charting`, `risk_analytics.ra_charting`)
- Statistical libraries (already imported in econometrics.py)

### Integration with Existing Modules
- **DO:** Import and test existing models without modification
- **DO:** Extend `risk_analytics/model_validation.py` rather than duplicate
- **DO:** Reuse `risk_pylibrary.tools` utilities
- **DON'T:** Modify existing model code during validation
- **DON'T:** Duplicate functionality already in risk_analytics or tools

### Key Models to Prioritize for Validation
1. **Most Complex (highest risk):**
   - `risk_models/pnl_fifo.py` (43KB, complex FIFO logic)
   - `risk_models/pnl_support.py` (94KB, extensive P&L support)
   - `risk_models/mc_stress_testing.py` (Monte Carlo stress testing)

2. **Regulatory Critical:**
   - VaR models in `risk_models/econometrics.py`
   - Liquidity models in `projects/liquidity_risk/`
   - Stress tests in `projects/stress_testing/`

3. **Already Has Some Validation:**
   - Extend existing tests in `risk_analytics/model_validation.py`

## Working in This Repository

### Adding New Validation Templates
- Place in `projects/validation/docs/templates/`
- Follow structure of existing template
- Include all 9 core sections
- Add model-specific sections (e.g., "FIFO Logic Verification" for P&L models, "Behavioral Assumption Testing" for liquidity models)

### Extending Conceptual Framework
- Update `projects/validation/docs/concepts/validation_framework_concept.md`
- Reference specific risk_pylibrary models when providing examples
- Cross-reference to specific MaRisk or EBA guideline sections
- Consider BaFin supervisory expectations

### Adding Validation Code (Phase 2)
- Place in `projects/validation/src/validation/`
- Import from `risk_pylibrary` using full paths: `from risk_pylibrary.risk_models import ...`
- Write unit tests in `projects/validation/tests/`
- Follow existing code style from risk_models/ and risk_analytics/

### Starting Phase 2 Implementation

**Recommended Implementation Order:**

1. **Model Inventory Setup**
   - Create registry of all models in `risk_models/` and `projects/`
   - Document: `mc_stress_testing.py`, `garch_models.py`, `pnl_fifo.py`, etc.
   - Classify by materiality: Tier 1 (VaR, stress testing, LCR) vs Tier 2/3
   - Link to existing documentation and model owners

2. **Extend Existing Validation Tools** (Highest ROI)
   - Start with `risk_analytics/model_validation.py` as foundation
   - Add regulatory reporting wrapper around `mc_os_convergence_test`
   - Implement traffic light approach for VaR backtesting
   - This provides immediate value by formalizing existing work

3. **Data Quality Module**
   - Build data quality checks for model inputs
   - Focus on time series data used by `econometrics.py`, `mc_models.py`
   - Validate data feeds to `pnl_fifo.py` (complex 43KB file needs robust data)
   - Automated alerts for data issues

4. **Model-Specific Validation Modules**
   - **Priority 1:** VaR/ES backtesting (most critical for BaFin)
   - **Priority 2:** Liquidity models (`maturity_ladder.py`, `predict_reg_data.py`)
   - **Priority 3:** P&L validation (FIFO logic verification)
   - **Priority 4:** GARCH and forecasting models

5. **Report Generation**
   - Auto-populate `docs/templates/validation_report_template.md`
   - Integrate with `risk_analytics/ra_charting.py` for charts
   - PDF export for BaFin submissions
   - Bilingual support (German/English)

6. **Finding Tracker and Workflow**
   - Database for tracking validation findings
   - Remediation status monitoring
   - Integration with model change management

7. **Dashboard** (Last - once core functionality proven)
   - Validation program metrics
   - Model performance monitoring
   - Regulatory reporting preparation

### Code Quality Standards for Phase 2
- Type hints for all functions (aid auditability)
- Comprehensive docstrings (regulatory scrutiny)
- Unit tests for all calculations (verification requirement)
- Integration tests for end-to-end validation workflows
- Version all model inputs and outputs (audit trail)

## Important Considerations

### BaFin Inspection Readiness
- All validation reports must be readily available
- Audit trail of model changes and validation triggers
- Documentation of validation methodology
- Evidence of independence (organizational structure)
- Management action plans for findings

### Bilingual Support
- Reports may need German version for BaFin
- Technical terms should use German regulatory language where appropriate
- Consider bilingual report generation in Phase 2

### Data Sensitivity
- Models may use sensitive market data or customer data
- Implement appropriate data protection measures
- Anonymize data in examples and documentation
- No production data in version control

## Validation Scenarios for Key risk_pylibrary Models

### Scenario 1: VaR Model Validation (risk_models/econometrics.py)
**Model:** Historical Simulation VaR using `ec.sim2VaR()`

**Validation Activities:**
1. **Conceptual Soundness:**
   - Review historical simulation methodology
   - Validate choice of lookback period (typically 250-500 days)
   - Assess appropriateness of confidence levels (99%, 97.5%)

2. **Implementation:**
   - Test calculation against manual computation
   - Verify return series handling
   - Check portfolio aggregation logic

3. **Backtesting:**
   - Use existing `mc_os_convergence_test` from `risk_analytics/model_validation.py`
   - Add traffic light test (Basel framework)
   - Exception counting and analysis

4. **Outcomes:**
   - Sensitivity to lookback period
   - Comparison with parametric VaR
   - Benchmark against market VaR standards

**Expected Findings:** Focus on assumption documentation, historical period adequacy

---

### Scenario 2: Monte Carlo Stress Testing (risk_models/mc_stress_testing.py)
**Model:** Monte Carlo simulation for stress scenarios

**Validation Activities:**
1. **Conceptual Soundness:**
   - Review probability distribution assumptions (t-distribution, normal)
   - Validate stress scenario design
   - Assess correlation structure

2. **Implementation:**
   - Test random number generation (reproducibility)
   - Verify convergence of simulations
   - Check scenario application logic

3. **Ongoing Monitoring:**
   - Convergence tests using existing `mc_os_convergence_test`
   - Stability of parameters over time
   - Performance under extreme scenarios

4. **Outcomes:**
   - Sensitivity to number of simulations
   - Comparison with historical stress events
   - Tail risk assessment

**Expected Findings:** Convergence adequacy, scenario selection rationale

---

### Scenario 3: P&L FIFO Model (risk_models/pnl_fifo.py - 43KB)
**Model:** Complex FIFO P&L attribution logic

**Validation Activities:**
1. **Conceptual Soundness:**
   - Review FIFO methodology appropriateness
   - Validate trade matching logic
   - Assess handling of corporate actions, splits

2. **Implementation:**
   - **Critical:** Code review due to complexity (43KB file)
   - Unit testing of core FIFO functions
   - Integration testing with `pnl_support.py` (94KB)
   - Test edge cases: partial fills, cancellations, amendments

3. **Data Quality:**
   - Trade data completeness
   - Price data accuracy
   - Reconciliation with trading systems

4. **Outcomes:**
   - P&L reconciliation with actuary systems
   - Attribution breakdown accuracy
   - Comparison with alternative attribution methods

**Expected Findings:** High priority for documentation, edge case handling, unit test coverage

---

### Scenario 4: Liquidity Maturity Ladder (projects/liquidity_risk/maturity_ladder.py)
**Model:** Cash flow bucketing and gap analysis

**Validation Activities:**
1. **Conceptual Soundness:**
   - Review bucketing methodology
   - Validate behavioral assumptions (rollover rates, drawdown)
   - Assess stress scenario calibration

2. **Implementation:**
   - Verify bucket assignment logic
   - Test cash flow aggregation
   - Check gap calculation

3. **Data Quality:**
   - Contract data completeness
   - Maturity date accuracy
   - Behavioral parameter sources

4. **Outcomes:**
   - Sensitivity to behavioral assumptions
   - Comparison with regulatory templates
   - Stress test reasonableness

**Expected Findings:** Behavioral assumption documentation, stress calibration justification

---

### Scenario 5: GARCH Volatility Models (risk_models/garch_models.py)
**Model:** GARCH volatility forecasting

**Validation Activities:**
1. **Conceptual Soundness:**
   - Review GARCH specification (GARCH(1,1) vs others)
   - Validate stationarity assumptions
   - Assess appropriateness for risk factors

2. **Implementation:**
   - Parameter estimation verification
   - Forecast generation testing
   - Convergence of optimization

3. **Ongoing Monitoring:**
   - Parameter stability over time
   - Forecast accuracy metrics (RMSE, MAE)
   - Comparison with realized volatility

4. **Outcomes:**
   - Sensitivity to estimation window
   - Comparison with simpler volatility measures (EWMA, historical)
   - Performance during volatile periods

**Expected Findings:** Parameter stability, forecast accuracy, model specification justification

---

### Scenario 6: Liquidity Forecasting (projects/liquidity_risk/predict_reg_data.py)
**Model:** Regulatory data component forecasting

**Validation Activities:**
1. **Conceptual Soundness:**
   - Review forecasting methodology (SARIMA, OLS, Theta)
   - Validate seasonal pattern assumptions
   - Assess appropriate forecast horizons

2. **Implementation:**
   - Test integration with `risk_models/ols_predict_models.py`, `sarima_models.py`, `theta_models.py`
   - Verify data preprocessing
   - Check forecast aggregation

3. **Ongoing Monitoring:**
   - Forecast vs. actual comparison
   - Error analysis and bias detection
   - Model selection criteria

4. **Outcomes:**
   - Forecast accuracy by component (HQLA, inflows, outflows)
   - Sensitivity to historical data period
   - Comparison across forecasting methods

**Expected Findings:** Model selection documentation, accuracy metrics, seasonal pattern validation

---

## Quick Reference: Model-to-Validation Mapping

| Model File | Primary Validation Areas | Priority | Complexity |
|------------|-------------------------|----------|------------|
| `risk_models/pnl_fifo.py` | Implementation, Outcomes | **Critical** | Very High (43KB) |
| `risk_models/mc_stress_testing.py` | Conceptual, Outcomes | **Critical** | High |
| `risk_models/econometrics.py` | Implementation, Backtesting | **Critical** | Medium-High |
| `projects/liquidity_risk/maturity_ladder.py` | Conceptual, Outcomes | High | Medium |
| `projects/liquidity_risk/predict_reg_data.py` | Ongoing Monitoring, Outcomes | High | Medium |
| `risk_models/garch_models.py` | Ongoing Monitoring | Medium | Medium |
| `projects/stress_testing/mr_stress_test.py` | Conceptual, Outcomes | High | Medium-High |
| `risk_models/pnl_support.py` | Implementation | High | Very High (94KB) |

**Validation Frequency Recommendations:**
- **Critical models:** Annual validation minimum, trigger-based for material changes
- **High priority:** Annual or biennial depending on model stability
- **Medium priority:** Biennial validation, trigger-based for methodology changes

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**risk_pylibrary** is Trade Republic's Risk Modelling library for quantitative risk analysis, portfolio analytics, and regulatory reporting. The codebase supports risk calculations for trading books, market risk modeling, P&L attribution, and external data integration with Snowflake and S3.

## Development Setup

### Local Environment

```bash
# Create and activate virtualenv (Python 3.10-3.12)
python3.12 -m venv venv
source venv/bin/activate

# Install with dev and test dependencies
pip install -e ".[dev,test]"
```

### Docker Build

```bash
docker build \
  --build-arg PYTHON3_ECR=python \
  --build-arg PYTHON3_VERSION=3.12 \
  --build-arg UV_VERSION=latest \
  -t risk-pylibrary:latest .

docker run --rm -it risk-pylibrary:latest
```

### Running Tasks

Tasks are meant to be run as modules from the repository root:

```bash
# From risk_pylibrary root directory
python3 -m automation.task_risk_model_trading_book
python3 -m automation.task_ext_data_risk_factors
python3 -m automation.task_pnl_trading_book
```

**Important:** Always run from the repository root, not from within subdirectories, to ensure proper module resolution.

## Code Architecture

### Core Module Structure

The library is organized into six core modules with clear separation of concerns:

**1. `portfolio_analytics/`** - Portfolio-level analysis and position management
- `positions.py`: Main entry point via `get_port(sec_acc_no, report_date, **kwargs)` which fetches portfolio positions, maps risk factors, and optionally calculates risk metrics
- `bond_analytics.py`: Fixed income analytics
- `performance.py`: Portfolio performance attribution
- `prices.py`, `trades.py`: Position and trade data structures

**2. `risk_analytics/`** - Risk calculation engines
- `risk_engines.py`: Core risk engine with `portfolio_vaR()` supporting multiple methodologies (Historical Simulation, GJR-GARCH, Monte Carlo)
- Provides VaR, CVaR, and SVaR calculations with configurable holding periods

**3. `instruments/`** - Market data and instrument definitions
- `data_prices.py`: External data fetching (Yahoo Finance, market data sources)
- `data_info.py`: Instrument metadata and reference data
- `data_support.py`: Data transformation utilities (parquet conversion via `rm2parquet()`, `rfmapping2parquet()`)
- `data_rf_wrapper.py`: Risk factor mapping and reference

**4. `risk_models/`** - Econometric and statistical models
- `econometrics.py`: Statistical methods for risk modeling
- `garch_models.py`, `mc_models.py`, `sarima_models.py`: Time series forecasting
- `pnl_support.py`, `pnl_fifo.py`: P&L calculation engines

**5. `tools/`** - Infrastructure utilities
- `snowflake_db/db_connection.py`: Snowflake database connectivity via `run_query()`
- `python2s3.py`: S3 upload utilities with `save_in_s3()` and `save_in_s3_local()`
- `config.py`, `utils.py`: Configuration management
- `pandas_patched.py`: Custom pandas extensions (some modules import pandas from here)

**6. `automation/`** - Production task scripts
- Self-contained scripts that orchestrate data pipelines
- Follow pattern: query Snowflake → process data → calculate risk → write parquet → upload to S3
- All tasks use `logging` module with structured INFO/ERROR messages

### Projects Directory

`projects/` contains specialized analysis modules:
- `validation/`: Model validation frameworks
- `pnl/`, `trading_book/`, `stress_testing/`: Domain-specific analyses
- `caracalla/`, `irrbb/`, `liquidity_risk/`: Regulatory reporting modules

### Data Flow Pattern

Typical workflow across the codebase:

1. **Data Retrieval**: Snowflake queries via `tools.snowflake_db.db_connection`
2. **Position Building**: `portfolio_analytics.positions.get_port()` fetches positions and maps risk factors
3. **Risk Calculation**: `risk_analytics.risk_engines.portfolio_vaR()` computes risk metrics
4. **Data Export**: `instruments.data_support` converts to parquet format
5. **S3 Upload**: `tools.python2s3.save_in_s3()` uploads to `tr-risk-data-prd` bucket

### Key Integration Points

- **Snowflake**: Primary data source for positions, trades, and cached valuations
- **S3 Buckets**: Output target (`tr-risk-data-prd`) for risk metrics and risk factor mappings
- **Date Handling**: Functions expect `datetime.date` objects, not strings. Convert with `pd.to_datetime()`
- **Risk Factor Mapping**: The `force_rf` parameter in `get_port()` maps unmapped instruments to default risk factors (bonds → 'global_agg_bond', others → 'msci_world')

## Testing and Code Quality

```bash
# Run tests
pytest

# Run with coverage
coverage run -m pytest
coverage report

# Format code (line length: 120)
black .

# Lint
ruff check .

# Pre-commit hooks
pre-commit run --all-files
```

## Common Patterns

### Working with DataFrames
- The codebase uses both pandas and polars
- Some modules import `from tools import pandas_patched as pd` for custom functionality
- Date columns must be converted to datetime before using `.dt` accessor: `pd.to_datetime(df['report_date'])`

### Authentication
- AWS credentials required for S3 operations (uses boto3 default credential chain)
- Snowflake credentials loaded via environment variables or `.env` files (python-dotenv)

### Module Imports
When creating new automation tasks, import internal modules as:
```python
from portfolio_analytics import positions as pos
from tools.snowflake_db import db_connection as db
from instruments import data_support as data_sup
from tools import python2s3 as ps3
```

### Error Handling in Tasks
Production tasks should:
- Use logging (not print statements) for all output
- Catch exceptions, log with traceback, and return status dictionaries
- Return `{'success': bool, 'message': str}` for calling systems
- Continue processing remaining items on individual failures when appropriate

## Environment Variables

- `TEMP_PATH`: Local temporary directory for parquet files (default: `/tmp`)
- `S3_PATH`: S3 path prefix for uploads (task-specific defaults)
- Snowflake credentials: Set via `.env` file or environment

## DAGs and Orchestration

`dags/` contains Airflow DAG definitions for scheduled automation tasks. These orchestrate the scripts in `automation/`.

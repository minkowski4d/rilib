# risk_pylibrary

Trade Republic's Python library for quantitative risk analysis, portfolio analytics, and regulatory reporting.

## Overview

This library provides the core infrastructure for market risk modeling and portfolio analysis across Trade Republic's trading operations. It integrates with Snowflake for data retrieval, performs sophisticated risk calculations, and outputs results to S3 for downstream consumption.

**Core Capabilities:**
- **Portfolio Analytics**: Position aggregation, performance attribution, and risk factor mapping
- **Risk Modeling**: VaR/CVaR/SVaR calculations using Historical Simulation, GARCH, and Monte Carlo methods
- **Market Data**: Integration with external and internal data sources for price and risk factor data
- **Econometric Models**: Time series forecasting (GARCH, SARIMA, Monte Carlo) for risk projections
- **Regulatory Reporting**: Specialized modules for IRRBB, liquidity risk, and stress testing
- **Automation**: Production-ready tasks for trading book risk updates and external data ingestion

**Key Modules:**
- `portfolio_analytics/` - Portfolio positions and analytics
- `risk_analytics/` - Risk calculation engines
- `risk_models/` - Econometric and statistical models
- `instruments/` - Market data and instrument definitions
- `tools/` - Snowflake, S3, and infrastructure utilities
- `automation/` - Production data pipeline tasks
- `projects/` - Specialized analysis and regulatory reporting

For detailed architecture and development patterns, see [CLAUDE.md](CLAUDE.md).

## Development Setup

### Dependencies

- Python 3.10 to 3.12 (currently using 3.12.12)
- UV package installer (version 0.6.3)

### Local Development Environment

Create a virtualenv and install dependencies:

```shell
# Create and activate virtualenv
python3.12 -m venv venv
source venv/bin/activate

# Install with dev and test dependencies
pip install -e ".[dev,test]"
```

### Docker Container

#### Local Build

Build the Docker image locally for testing:

```shell
docker build \
  --build-arg PYTHON3_ECR=python \
  --build-arg PYTHON3_VERSION=3.12 \
  --build-arg UV_VERSION=latest \
  -t risk-pylibrary:latest .

docker run --rm -it risk-pylibrary:latest
```

## CI/CD Pipeline and ECR Deployment

The repository uses GitHub Actions for automated testing and deployment to AWS Elastic Container Registry (ECR).

### Automated Workflow (`.github/workflows/pr.yml`)

**Trigger Conditions:**
- Pull requests to `main`
- Pushes to `main` branch
- Changes to core modules: `automation/`, `portfolio_analytics/`, `risk_models/`, `risk_analytics/`, `instruments/`, `tools/`, or `pyproject.toml`

**Pipeline Steps:**

1. **Environment Setup** (`env-setup` job)
   - Reads Python version from `.python-version` (3.12.12)
   - Reads UV version from `.uv-version` (0.6.3)
   - Sets repository metadata:
     - ECR Repository: `risk/risk_pylibrary`
     - AWS Account: `263932266204` (eu-central-1)
     - Element: `compliance-and-risk`
     - Atom: `risk`

2. **Test & Coverage** (`test-python-slow` job)
   - Installs dependencies using UV package manager
   - Sets up mock AWS credentials for testing
   - Runs pytest test suite (currently commented out: coverage reporting)
   - Uses GitHub Actions caching for faster builds

3. **ECR Build & Push** (`ecr` job via `build-python.yaml`)
   - Authenticates to AWS ECR using GitHub OIDC (role: `github-actions/risk_pylibrary`)
   - Builds multi-stage Docker image with build metadata:
     - `TR_GIT_REPOSITORY`: GitHub repository name
     - `TR_GIT_COMMIT`: Git commit SHA
     - `TR_ELEMENT`: compliance-and-risk
     - `TR_ATOM`: risk
   - Tags images with:
     - Git SHA: `sha-<commit>`
     - Branch name: `main` (for main branch pushes)
     - PR number: `pr-<number>` (for pull requests)
   - Pushes to: `263932266204.dkr.ecr.eu-central-1.amazonaws.com/risk/risk_pylibrary`
   - Utilizes GitHub Actions cache for layer caching

### Automation Task Execution

The `automation/` directory contains production tasks (e.g., `task_risk_model_trading_book.py`, `task_ext_data_risk_factors.py`) that are:
- Packaged into the ECR Docker image
- Deployed as containerized workloads (likely orchestrated via Airflow DAGs in `/dags/traderepublic/risk_function`)
- Executed with AWS credentials to access Snowflake and S3 resources
- Run as locally Python modules: `python3 -m automation.task_name` out risk_pylibrary

**Key Integration Points:**
- **Base Image**: Uses Trade Republic's internal Python base image from ECR
- **Build Tool**: UV (ultra-fast Python package installer) for dependency management
- **Deployment Target**: AWS ECS/EKS (inferred from ECR usage pattern)
- **Data Sources**: Snowflake (via `tools.snowflake_db`)
- **Data Outputs**: S3 bucket `tr-risk-data-prd`

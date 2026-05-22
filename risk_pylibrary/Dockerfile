# syntax=docker/dockerfile:1.4
# Build dependencies
ARG PYTHON3_ECR
ARG PYTHON3_VERSION
ARG UV_VERSION

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM ${PYTHON3_ECR}:${PYTHON3_VERSION} AS main

ARG TR_GIT_REPOSITORY="N/A"
ARG TR_GIT_COMMIT="N/A"
ARG TR_ELEMENT="N/A"
ARG TR_ATOM="N/A"

ENV TR_GIT_REPOSITORY=${TR_GIT_REPOSITORY}
ENV TR_GIT_COMMIT=${TR_GIT_COMMIT}
ENV TR_ELEMENT=${TR_ELEMENT}
ENV TR_ATOM=${TR_ATOM}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV="/opt/venv"
ENV APPLICATION_DIR="/usr/local/app"
ENV _TYPER_STANDARD_TRACEBACK=1
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}:${APPLICATION_DIR}/bin"

WORKDIR ${APPLICATION_DIR}

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
      git \
    && \
    rm -rf /var/lib/apt/lists/*

RUN --mount=from=uv,source=/uv,target=./uv \
    ./uv venv ${VIRTUAL_ENV}

COPY --link pyproject.toml .
COPY --link README.md .
COPY --link tools tools/
COPY --link automation automation/
COPY --link risk_models risk_models/
COPY --link risk_analytics risk_analytics/
COPY --link instruments instruments/
COPY --link portfolio_analytics portfolio_analytics/
# As we use setuptools_scm, need to get some git info
COPY --link .git .git/

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=from=uv,source=/uv,target=./uv \
    ./uv pip install "setuptools>=65.4" && \
    ./uv pip install .

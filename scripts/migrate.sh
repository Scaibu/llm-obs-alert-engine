#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="python3"
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python3" ]; then
    PYTHON_BIN="${VIRTUAL_ENV}/bin/python3"
elif [ -x ".venv/bin/python3" ]; then
    PYTHON_BIN=".venv/bin/python3"
fi

PYTHONPATH=src "${PYTHON_BIN}" scripts/migrate.py "${@:-up}"

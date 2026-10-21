#!/usr/bin/env bash
set -euo pipefail

ENV="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Rolling back alert-engine in environment: ${ENV}"

case "${ENV}" in
  dev|staging|prod)
    if command -v kubectl >/dev/null 2>&1; then
      kubectl rollout undo deployment/alert-engine -n "llmobs-${ENV}"
    elif command -v helm >/dev/null 2>&1; then
      helm rollback alert-engine --namespace "llmobs-${ENV}"
    fi
    ;;
  *)
    echo "Unknown environment: ${ENV}"
    exit 1
    ;;
esac

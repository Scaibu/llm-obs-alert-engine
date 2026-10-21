#!/usr/bin/env bash
set -euo pipefail

ENV="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Deploying alert-engine to environment: ${ENV}"

case "${ENV}" in
  dev|staging|prod)
    if command -v kubectl >/dev/null 2>&1; then
      kubectl apply -k "${ROOT_DIR}/deploy/k8s/overlays/${ENV}"
      kubectl rollout status deployment/alert-engine -n "llmobs-${ENV}" --timeout=120s
    elif command -v helm >/dev/null 2>&1; then
      helm upgrade --install alert-engine "${ROOT_DIR}/deploy/helm" \
        -f "${ROOT_DIR}/deploy/helm/env-values/values.${ENV}.yaml" \
        --namespace "llmobs-${ENV}" --create-namespace
    fi
    ;;
  local)
    docker-compose -f "${ROOT_DIR}/deploy/docker/compose/docker-compose.single.yml" up -d
    ;;
  *)
    echo "Unknown environment: ${ENV}"
    exit 1
    ;;
esac

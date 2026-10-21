#!/usr/bin/env bash
# Atajo local opcional — NO se incluye en la imagen Docker Hub (.dockerignore).
# Arranque recomendado (documentado en README):
#   docker compose up -d --build
#
# Este script solo envuelve ese flujo. Ya no ejecuta el pipeline NIST/ETL:
# los datos vienen de init.sql en el primer arranque de MySQL.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-primer-parcial}"

DOCKER="docker"
if ! docker info >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    DOCKER="sudo docker"
  else
    echo "ERROR: Docker no esta disponible."
    exit 1
  fi
fi

if $DOCKER compose version >/dev/null 2>&1; then
  COMPOSE_CMD="$DOCKER compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "ERROR: No se encontro docker compose."
  exit 1
fi

echo "Levantando MySQL (init.sql) + Streamlit..."
$COMPOSE_CMD up -d --build

echo ""
echo "Listo. Streamlit: http://localhost:8501"
echo "Si el volumen MySQL ya existia vacio/viejo y no ves datos:"
echo "  $COMPOSE_CMD down -v && $COMPOSE_CMD up -d --build"

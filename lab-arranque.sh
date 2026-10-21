#!/usr/bin/env bash
# Arranque tipo laboratorio (Linux / WSL / máquina de evaluación).
# - Libera puertos 3306 y 8501 (elimina contenedores que los publiquen)
# - Reinicia este proyecto desde cero (down -v → pull Hub → up sin build)
# NO hace prune de todo Docker; solo libera lo que bloquea este stack.
#
# Uso (desde la raíz del repo):
#   chmod +x lab-arranque.sh
#   ./lab-arranque.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-primer-parcial}"

DOCKER="docker"
if ! docker info >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    DOCKER="sudo docker"
  else
    echo "ERROR: Docker no disponible."
    exit 1
  fi
fi

if $DOCKER compose version >/dev/null 2>&1; then
  COMPOSE_CMD="$DOCKER compose"
else
  echo "ERROR: se necesita 'docker compose'."
  exit 1
fi

echo "======================================"
echo " LAB ARRANQUE — Optica y Fotonica"
echo "======================================"

echo ""
echo "[1/4] Liberando puertos 3306 y 8501 (contenedores que los usen)..."
for PORT in 3306 8501; do
  # Contenedores que publican ese puerto
  IDS="$($DOCKER ps -aq --filter "publish=${PORT}" 2>/dev/null || true)"
  if [[ -n "${IDS}" ]]; then
    # shellcheck disable=SC2086
    $DOCKER rm -f ${IDS} 2>/dev/null || true
    echo "  Puerto ${PORT}: contenedores eliminados."
  else
    echo "  Puerto ${PORT}: libre (o sin contenedor Docker)."
  fi
done

# Nombres fijos de este proyecto (por si quedaron huérfanos)
for NAME in mysql_container streamlit_optica; do
  if $DOCKER ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
    $DOCKER rm -f "$NAME" 2>/dev/null || true
    echo "  Eliminado contenedor: $NAME"
  fi
done

echo ""
echo "[2/4] docker compose down -v (solo este proyecto)..."
$COMPOSE_CMD down -v --remove-orphans 2>/dev/null || true

echo ""
echo "[3/4] docker compose pull (imagen Hub + mysql:8.4)..."
$COMPOSE_CMD pull

echo ""
echo "[4/4] docker compose up -d --no-build..."
$COMPOSE_CMD up -d --no-build

echo ""
echo "======================================"
echo " Listo. Abre: http://localhost:8501"
echo " Estado:     $COMPOSE_CMD ps"
echo "======================================"
echo "Nota: init.sql solo corre con volumen vacio (este script hace down -v)."
echo "Si pull falla (imagen aun no en Hub), usa en su lugar:"
echo "  $COMPOSE_CMD up -d --build"
echo "======================================"

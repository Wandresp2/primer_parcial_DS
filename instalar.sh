#!/usr/bin/env bash
# Orquestador unico — Optica y Fotonica (NIST ASD → MySQL → Streamlit)
# Uso (Linux / WSL):
#   chmod +x instalar.sh
#   ./instalar.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
# Nombre fijo: evita que WSL (/mnt/c/...) y Windows generen project names distintos
# y choquen en container_name (mysql_container / streamlit_optica).
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-primer-parcial}"
PROJECT_NAME="$COMPOSE_PROJECT_NAME"

echo "======================================"
echo " INSTALACION AUTOMATICA"
echo " Optica y Fotonica — NIST ASD"
echo "======================================"
echo "Directorio: $SCRIPT_DIR"
echo "Proyecto Compose: $PROJECT_NAME"

# Preferir docker sin sudo; fallback a sudo docker
DOCKER="docker"
if ! docker info >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    DOCKER="sudo docker"
  else
    echo "ERROR: Docker no esta disponible (ni con sudo)."
    echo "En Windows usa WSL con Docker Desktop integrado."
    exit 1
  fi
fi

if $DOCKER compose version >/dev/null 2>&1; then
  COMPOSE_CMD="$DOCKER compose"
elif command -v docker-compose >/dev/null 2>&1; then
  if [[ "$DOCKER" == "sudo docker" ]]; then
    COMPOSE_CMD="sudo docker-compose"
  else
    COMPOSE_CMD="docker-compose"
  fi
else
  echo "ERROR: No se encontro 'docker compose' ni 'docker-compose'."
  exit 1
fi

echo "Usando: $COMPOSE_CMD"

# --------------------------------------------------
# [1/4] Limpieza SOLO de recursos de este proyecto
# --------------------------------------------------
echo ""
echo "======================================"
echo " [1/4] LIMPIANDO RECURSOS DEL PROYECTO"
echo "======================================"

echo "[1/5] Deteniendo docker compose (down -v)..."
$COMPOSE_CMD -f "$COMPOSE_FILE" --profile pipeline down -v --remove-orphans 2>/dev/null || true

echo "[2/5] Eliminando contenedores del proyecto (si existen)..."
for CONTAINER in mysql_container streamlit_optica; do
  if $DOCKER ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    $DOCKER rm -f "$CONTAINER" 2>/dev/null || true
    echo "  Contenedor eliminado: $CONTAINER"
  fi
done
# Contenedores one-shot del pipeline (nombre variable)
PIPELINE_IDS="$($DOCKER ps -a --filter "name=${PROJECT_NAME}-pipeline" --format '{{.ID}}' 2>/dev/null || true)"
if [[ -n "${PIPELINE_IDS}" ]]; then
  # shellcheck disable=SC2086
  $DOCKER rm -f $PIPELINE_IDS 2>/dev/null || true
fi

echo "[3/5] Eliminando volumen del proyecto..."
$DOCKER volume rm "${PROJECT_NAME}_mysql_data" 2>/dev/null || true
$DOCKER volume rm mysql_data 2>/dev/null || true

echo "[4/5] Eliminando red del proyecto..."
$DOCKER network rm "${PROJECT_NAME}_optica_net" 2>/dev/null || true
$DOCKER network rm optica_net 2>/dev/null || true

echo "[5/5] Eliminando imagenes construidas de este proyecto..."
$DOCKER rmi -f "${PROJECT_NAME}-streamlit" 2>/dev/null || true
$DOCKER rmi -f "${PROJECT_NAME}-pipeline" 2>/dev/null || true
$DOCKER rmi -f "primer-parcial-streamlit" 2>/dev/null || true
$DOCKER rmi -f "primer-parcial-pipeline" 2>/dev/null || true
# Imagen base MySQL del stack (como el script de referencia)
$DOCKER rmi -f mysql:8.4 2>/dev/null || true

echo ""
echo "Limpieza del proyecto completada (el resto de Docker no se toco)."

# --------------------------------------------------
# [2/4] MySQL + healthcheck
# --------------------------------------------------
echo ""
echo "======================================"
echo " [2/4] CREANDO MYSQL 8.4"
echo "======================================"

$COMPOSE_CMD -f "$COMPOSE_FILE" up -d mysql

echo ""
echo "Esperando a que MySQL este healthy..."
ATTEMPTS=0
MAX_ATTEMPTS=60
until $DOCKER inspect --format='{{.State.Health.Status}}' mysql_container 2>/dev/null | grep -q "healthy"; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if [[ "$ATTEMPTS" -ge "$MAX_ATTEMPTS" ]]; then
    echo "ERROR: MySQL no quedo healthy a tiempo."
    $DOCKER logs mysql_container || true
    exit 1
  fi
  echo "  Esperando MySQL... ($ATTEMPTS/$MAX_ATTEMPTS)"
  sleep 3
done

echo ""
echo "Estado de contenedores:"
$COMPOSE_CMD -f "$COMPOSE_FILE" ps
echo ""
echo "MySQL listo:"
echo "  Host      : localhost (desde el host) / mysql (desde contenedores)"
echo "  Puerto    : 3306"
echo "  Database  : optica_y_fotonica"
echo "  Usuario   : root"
echo "  Password  : root"
echo "  Contenedor: mysql_container"
echo "  Red       : optica_net"

# --------------------------------------------------
# [3/4] Pipeline (descarga + limpieza + schema + ETL)
# --------------------------------------------------
echo ""
echo "======================================"
echo " [3/4] PIPELINE → MySQL"
echo "======================================"
echo "Construyendo imagen pipeline (si hace falta)..."
$COMPOSE_CMD -f "$COMPOSE_FILE" build pipeline

echo ""
echo "Ejecutando descarga NIST + limpieza + ETL..."
echo "(puede tardar varios minutos por la API del NIST)"
# Forzar LF en scripts montados desde Windows (evita 'pipefail\\r')
$COMPOSE_CMD -f "$COMPOSE_FILE" --profile pipeline run --rm --entrypoint bash pipeline \
  -c "sed -i 's/\\r\$//' scripts/*.sh && bash scripts/run_pipeline.sh"
echo ""
echo "Verificacion rapida de conteos:"
$DOCKER exec mysql_container mysql -uroot -proot -N -e \
  "SELECT 'linea_espectral', COUNT(*) FROM optica_y_fotonica.linea_espectral
   UNION ALL SELECT 'nivel_energia', COUNT(*) FROM optica_y_fotonica.nivel_energia;" \
  2>/dev/null || true

# --------------------------------------------------
# [4/4] Streamlit en background
# --------------------------------------------------
echo ""
echo "======================================"
echo " [4/4] INICIANDO STREAMLIT"
echo "======================================"

$COMPOSE_CMD -f "$COMPOSE_FILE" build streamlit
$COMPOSE_CMD -f "$COMPOSE_FILE" up -d streamlit

echo ""
echo "======================================"
echo " INSTALACION COMPLETA"
echo "======================================"
echo "Interfaz Streamlit : http://localhost:8501"
echo "MySQL (host)       : localhost:3306"
echo "  database         : optica_y_fotonica"
echo "  user / password  : root / root"
echo "creado por         : Andres David Perez"
echo "======================================"
echo ""
echo "Streamlit corre en Docker (background)."
echo "Para ver logs:  $COMPOSE_CMD -f docker-compose.yml logs -f streamlit"
echo "Para apagar:    $COMPOSE_CMD -f docker-compose.yml down"
echo "======================================"

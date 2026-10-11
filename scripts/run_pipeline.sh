#!/usr/bin/env bash
# Entrypoint del servicio pipeline: descarga → limpieza → schema+ETL.
set -euo pipefail

cd /app

echo "======================================"
echo " PIPELINE OPTICA Y FOTONICA"
echo "======================================"

echo ""
echo "[1/3] Descarga NIST..."
python scripts/01_descarga_datos.py

echo ""
echo "[2/3] Limpieza L1-L14..."
python scripts/03_limpieza_datos.py

echo ""
echo "[3/3] Schema + ETL MySQL..."
export APPLY_SCHEMA="${APPLY_SCHEMA:-1}"
python scripts/04_etl_mysql.py

echo ""
echo "Pipeline completado."

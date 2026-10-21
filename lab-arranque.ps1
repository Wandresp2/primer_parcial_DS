# Arranque tipo laboratorio (Windows PowerShell / Docker Desktop).
# Libera puertos 3306 y 8501, reinicia este proyecto y usa imagen de Hub.
#
# Uso (desde la raiz del repo):
#   .\lab-arranque.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:COMPOSE_PROJECT_NAME = if ($env:COMPOSE_PROJECT_NAME) { $env:COMPOSE_PROJECT_NAME } else { "primer-parcial" }

Write-Host "======================================"
Write-Host " LAB ARRANQUE — Optica y Fotonica"
Write-Host "======================================"

Write-Host ""
Write-Host "[1/4] Liberando puertos 3306 y 8501..."
foreach ($port in 3306, 8501) {
  $ids = docker ps -aq --filter "publish=$port" 2>$null
  if ($ids) {
    docker rm -f $ids 2>$null | Out-Null
    Write-Host "  Puerto ${port}: contenedores eliminados."
  } else {
    Write-Host "  Puerto ${port}: libre (o sin contenedor Docker)."
  }
}

foreach ($name in @("mysql_container", "streamlit_optica")) {
  $exists = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $name }
  if ($exists) {
    docker rm -f $name 2>$null | Out-Null
    Write-Host "  Eliminado contenedor: $name"
  }
}

Write-Host ""
Write-Host "[2/4] docker compose down -v..."
docker compose down -v --remove-orphans 2>$null

Write-Host ""
Write-Host "[3/4] docker compose pull..."
docker compose pull

Write-Host ""
Write-Host "[4/4] docker compose up -d --no-build..."
docker compose up -d --no-build

Write-Host ""
Write-Host "======================================"
Write-Host " Listo. Abre: http://localhost:8501"
Write-Host " Estado:     docker compose ps"
Write-Host "======================================"
Write-Host "Si pull falla (imagen aun no en Hub):"
Write-Host "  docker compose up -d --build"
Write-Host "======================================"

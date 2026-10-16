# Óptica y Fotónica — NIST ASD → MySQL → Streamlit

Pipeline automatizado de datos atómicos (H–Ne) del [NIST Atomic Spectra Database](https://physics.nist.gov/PhysRefData/ASD/): descarga, limpieza, carga en MySQL 8.4 e interfaz analítica con Streamlit.

**Un solo comando** reproduce el sistema completo.

## Requisitos

- Docker Engine + Compose (en Windows: Docker Desktop con integración **WSL2**)
- Bash (Linux nativo o **WSL**)
- Puertos libres **3306** (MySQL) y **8501** (Streamlit)
- Internet (imágenes Docker, pip en el build, API NIST)

## Arranque

En WSL o Linux, desde la raíz del repositorio:

```bash
chmod +x instalar.sh
./instalar.sh
```

El script:

1. Limpia solo los recursos Docker de este proyecto (`down -v`, volumen, red, imágenes del stack).
2. Levanta MySQL 8.4 y espera el healthcheck.
3. Ejecuta el pipeline en Docker: descarga NIST → limpieza L1–L14 → `sql/schema.sql` → ETL (9 tablas).
4. Levanta Streamlit en background.

### URLs y credenciales

| Servicio | Acceso |
|----------|--------|
| Streamlit | http://localhost:8501 |
| MySQL (desde el host) | `localhost:3306` |
| Base de datos | `optica_y_fotonica` |
| Usuario / password | `root` / `root` |
| Host MySQL (entre contenedores) | `mysql` |
| Red Docker | `optica_net` |

Credenciales fijas en `docker-compose.yml` (laboratorio). Streamlit y el pipeline usan las mismas variables de entorno.

### Comandos útiles

```bash
docker compose ps
docker compose logs -f streamlit
docker compose down          # apaga sin borrar datos MySQL
docker compose down -v       # apaga y borra el volumen MySQL
```

Reinstalación completa desde cero: vuelve a ejecutar `./instalar.sh`.

## Estructura

```text
instalar.sh                 Orquestador único
docker-compose.yml          mysql + pipeline (profile) + streamlit
Dockerfile.pipeline         Imagen del pipeline de datos
Dockerfile.streamlit        Imagen de la UI
requirements-*.txt          Dependencias Python por imagen
sql/schema.sql              DDL: 9 tablas + vista v_linea_analisis
scripts/
  01_descarga_datos.py      Extract NIST → data/originales/
  03_limpieza_datos.py      Transform → data/procesados/
  04_etl_mysql.py           Load → MySQL
  run_pipeline.sh           01 → 03 → 04
app/
  streamlit_app.py          UI (7 secciones + filtros)
  db.py                     Conexión MySQL
data/                       Generada en runtime (CSV no versionados)
```

## Autor

Perez Criollo Andres David

Pipeline del proyecto del primer parcial usando Streamlit 

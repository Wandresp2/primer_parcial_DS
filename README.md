# Óptica y Fotónica — MySQL + Streamlit (NIST ASD)

Datos atómicos (H–Ne) del [NIST Atomic Spectra Database](https://physics.nist.gov/PhysRefData/ASD/) en MySQL 8.4, con interfaz analítica en Streamlit.

**Arranque:** `docker compose up -d --build`. La base se puebla sola con `init.sql`.

## Requisitos

- Docker Engine + Compose (en Windows: Docker Desktop)
- Puertos libres **3306** (MySQL) y **8501** (Streamlit)

## Arranque

Desde la raíz del repositorio:

```bash
docker compose up -d --build
```

La primera vez (volumen MySQL vacío):

1. MySQL ejecuta `init.sql` → crea `optica_y_fotonica`, 9 tablas, vista y datos.
2. Se construye la imagen de Streamlit → `http://localhost:8501`.

Si el volumen quedó vacío o a medias:

```bash
docker compose down -v
docker compose up -d --build
```

### URLs y credenciales

| Servicio | Acceso |
|----------|--------|
| Streamlit | http://localhost:8501 |
| MySQL (desde el host) | `localhost:3306` |
| Base de datos | `optica_y_fotonica` |
| Usuario / password | `root` / `root` |
| Host MySQL (entre contenedores) | `mysql` |
| Red Docker | `optica_net` |

Credenciales de laboratorio en `docker-compose.yml`. La app lee `MYSQL_*` por entorno.

**Nice to have (futuro):** `.env` + `.env.example` para externalizar `MYSQL_*` (el `.env` real no se versiona ni va a la imagen).

### Streamlit

- Pin: **`streamlit==1.51.0`** en `requirements.txt` (`width="stretch"`; evitar **1.65+**).
- Tras cambiar deps: `docker compose build streamlit && docker compose up -d streamlit`.

### Comandos útiles

```bash
docker compose ps
docker compose logs -f streamlit
docker compose logs -f mysql
docker compose down          # apaga; conserva datos MySQL
docker compose down -v       # apaga y borra volumen (reaplica init.sql al subir)
```

## `init.sql` (base portátil)

- Dump de schema + datos (~4–5 MB) en la raíz.
- Montado en MySQL: `./init.sql` → `/docker-entrypoint-initdb.d/01_init.sql`.
- Solo en el **primer arranque** con volumen vacío.

### Volumen de datos

| Tabla | Filas (aprox.) |
|-------|---------------:|
| elemento | 10 |
| espectro | 18 |
| exactitud | 13 |
| tipo_transicion | 5 |
| referencia | 377 |
| nivel_energia | 5 752 |
| linea_espectral | 18 288 |
| nivel_referencia | 3 592 |
| linea_referencia | 24 757 |
| **Total tablas** | **~52 812** |
| Vista `v_linea_analisis` | 18 288 |

**Nice to have (no crítico):** reducir el subconjunto H–Ne si el primer import se siente lento.

Regenerar el dump (opcional, con MySQL ya poblado):

```bash
docker exec mysql_container mysqldump -uroot -proot \
  --databases optica_y_fotonica --default-character-set=utf8mb4 \
  --single-transaction --routines --triggers --set-gtid-purged=OFF \
  -r /tmp/init.sql
docker cp mysql_container:/tmp/init.sql ./init.sql
```

## Estructura

```text
docker-compose.yml             # mysql + streamlit
Dockerfile                     # imagen de la app Streamlit
.dockerignore
requirements.txt               # deps pinneadas
init.sql                       # schema + datos (mount en MySQL)
app/
  streamlit_app.py
  db.py
docs/                          # documentación técnica (historial del parcial)
PLAN_AUTOMATIZACION.md
README.md
```

## Documentación técnica

Los `docs/` describen el trabajo de exploración, limpieza y ETL que **originó** los datos. El runtime actual ya no ejecuta ese pipeline: usa `init.sql`.

| Doc | Contenido |
|-----|-----------|
| [docs/02_…](docs/02_exploracion_caracterizacion_datos.md) | Diagnóstico metodológico |
| [docs/03_…](docs/03_limpieza_datos.md) | Decisiones L1–L14 |
| [docs/04_…](docs/04_pipeline_etl_mysql.md) | Modelo relacional y ETL |
| [docs/05_…](docs/05_consultas_analisis_cientifico.md) | Pregunta científica → UI |

Más contexto de diseño: [PLAN_AUTOMATIZACION.md](PLAN_AUTOMATIZACION.md).

## Autor

Perez Criollo Andres David  
Primer Parcial — Desarrollo de Software

# Plan de automatización — Óptica y Fotónica (NIST ASD)

**Proyecto:** Primer Parcial — Desarrollo de Software  
**Estudiante:** Perez Criollo Andres David  
**Estado:** **implementado** (Fases 1–8 + refactor `init.sql` / Compose sin pipeline)  
**Documento vivo:** historial de diseño. El arranque actual es `docker compose up -d --build` + `init.sql` (ver `README.md`).  
**Limpieza 2026-10-20:** eliminados del repo `scripts/`, `data/`, `sql/`, `instalar.sh` (ya no son runtime). Se conservan `docs/` y este plan como documentación del parcial.

**Referencia de patrón (solo estructura, no temática):** proyecto anterior (exoplanetas) — `instalar.sh` + Compose + ETL `.py` + Streamlit. La carpeta `automatizacion/` de referencia **ya fue eliminada** (Fase 7 / D18).

---

## 1. Objetivo final

Una persona clona el repositorio desde GitHub (Windows con WSL, o Linux), ejecuta **un solo comando** en la raíz:

```bash
chmod +x instalar.sh
./instalar.sh
```

Y obtiene, sin pasos manuales (sin DBeaver, sin Jupyter, sin notebooks, sin pip a mano):

1. Contenedores Docker del proyecto limpios y recreados.
2. MySQL 8.4 saludable con la base `optica_y_fotonica`.
3. Descarga automática de datos NIST (líneas + niveles H–Ne).
4. Limpieza / transformación → CSV procesados.
5. DDL (`sql/schema.sql`) + carga ETL de las 9 tablas (+ vista).
6. Interfaz Streamlit en `http://localhost:8501` con filtros, análisis científico y explorador.

**Resultado esperado al terminar el script:** Streamlit escuchando y MySQL consultable en `localhost:3306`.

---

## 2. Decisiones cerradas (acuerdo explícito)

| ID | Decisión | Acuerdo |
|----|----------|---------|
| D1 | Streamlit | Tercer… en realidad **segundo** servicio Docker (MySQL + Streamlit). Va en `docker-compose.yml`. |
| D2 | Jupyter | **No se incluye.** No es necesario para el flujo automatizado. |
| D3 | Notebooks `.ipynb` | **Se eliminan / reemplazan** por scripts `.py`. El proyecto se limpia. |
| D4 | ETL / pipeline | Todo en `.py`, invocable sin interacción humana. |
| D5 | Exploración (ex-notebook 02) | **No forma parte del pipeline automatizado** (ver §4). |
| D6 | Limpieza Docker al instalar | **Siempre instalación completa:** `down -v`, borrar volumen/red/contenedores/imágenes del proyecto. Reproducible desde cero en cualquier máquina. |
| D7 | Dónde corre el Python del pipeline | **Dentro de Docker (B1):** servicio one-shot / `docker compose run` con host MySQL = `mysql`. |
| D8 | Sistema operativo | Linux nativo o **Windows vía WSL**. El orquestador es `instalar.sh` (Bash). |
| D9 | Ubicación del instalador | **Raíz del repo:** `./instalar.sh`. |
| D10 | Credenciales | Sin cambios: MySQL `root`/`root`, DB `optica_y_fotonica`. Nada de configuración manual. |
| D11 | Descarga NIST | **Siempre se descarga** en cada instalación completa. |
| D12 | Streamlit UI | Inventario + distribución + cobertura Aki + λ–Aki + tipos + explorador + respuesta científica; filtros estilo proyecto astronomía; queries propias según el GUI. |
| D13 | Documentación de plan | Este archivo `PLAN_AUTOMATIZACION.md` es el ancla de contexto. |
| D14 | CSV en Git | **No versionar.** `data/` en `.gitignore`. Cada instalación regenera originales y procesados (máxima reproducibilidad del *proceso*). Ver §3.4. |
| D15 | Imágenes Docker | **Dos:** `Dockerfile.pipeline` y `Dockerfile.streamlit`. |
| D16 | Cómo queda Streamlit | Contenedor en **background** (`docker compose up -d streamlit`). El usuario abre `http://localhost:8501` en el navegador. Ver §3.5. |
| D17 | Documentación `docs/` | **Actualizar** rutas y flujo (sin Jupyter/notebooks; apuntar a scripts + `./instalar.sh`). |
| D18 | Carpeta `automatizacion/` | **Eliminar** al limpiar el repo (solo fue referencia de patrón). |
| D19 | Red Docker | Nombre oficial: **`optica_net`**. Contenedor Streamlit: **`streamlit_optica`**. |

---

## 3. Respuestas a dudas de diseño

### 3.1 ¿Borrar el volumen siempre es lo mejor para reproducibilidad?

**Sí, para este objetivo.**  
Si el script siempre hace `docker compose down -v` + recrear + descargar + limpiar + cargar:

- Dos PCs distintas llegan al mismo estado.
- No hay “datos viejos” de una corrida anterior.
- El clon de GitHub no depende de un volumen Docker local previo.

El coste es tiempo (NIST + ETL en cada `./instalar.sh`). Se acepta a cambio de reproducibilidad fuerte.  
**No** se implementará modo `--solo-ui` en la primera versión (se puede añadir después si hace falta).

### 3.2 ¿B1 (pipeline en Docker) es lo más reproducible?

**Sí, con Docker + WSL/Linux.**  
Ventajas frente al venv en el host (proyecto astronomía):

- Mismas versiones de Python/librerías en cualquier PC.
- El pipeline habla con MySQL por el nombre del servicio (`mysql`), igual que haría un contenedor en la red Compose.
- El host no necesita `pip install` ni pelear con PEP 668.
- Streamlit ya va en Docker → coherencia total: **solo se pide Docker + Bash (WSL)**.

### 3.3 ¿El notebook 02 es necesario en la cadena? (análisis de código/docs)

**No. El 03 no depende de salidas del 02.**

Evidencia:

| Pieza | Entrada | Salida |
|-------|---------|--------|
| Docs/código **02** | `datos_originales/` (o descarga si faltan) | Diagnóstico en memoria / gráficos; puede consolidar `nist_levels_todos_original.csv` como caché, pero **no** escribe el set de CSV que consume el ETL |
| Docs/código **03** | Solo lectura de `datos_originales/` | Escribe `datos_procesados/` (`lineas_limpias.csv`, `niveles_limpios.csv`, tablas para modelo, etc.) |

El 02 es **diagnóstico metodológico** (faltantes, IQR, validación física) que **justificó** las decisiones L1–L14 del 03. Esas decisiones ya están embebidas en la lógica de limpieza.  
Para automatizar: **01 descarga → 03 limpieza → 04 ETL → Streamlit**. El ex-02 no se traduce a script de pipeline; su valor documental queda en `docs/02_...md` (actualizado).

### 3.4 ¿Versionar CSV en Git o regenerarlos? (reproducibilidad)

**Mejor opción para reproducibilidad del sistema: no versionar CSV; regenerar siempre.**

| Enfoque | Pros | Contras |
|---------|------|---------|
| **A — Regenerar (elegido)** | Mismo proceso en cualquier PC; datos frescos de NIST; repo liviano; alinea con wipe + `./instalar.sh` | Requiere internet; instalación más lenta |
| B — Versionar originales en Git | Funciona offline; evidencia fija en el commit | Repo pesado; puede desfasarse de NIST; dos “fuentes de verdad” |

Reproducibilidad aquí significa: **mismo procedimiento → mismo sistema funcionando**, no necesariamente byte-idéntico a un CSV de hace meses.  
Por eso: `data/` completa en `.gitignore`; el script 01 siempre descarga; el 03 siempre regenera procesados.

### 3.5 Streamlit en background vs foreground (acceso a localhost)

Ambos modos permiten abrir la UI en el navegador. La diferencia es solo la terminal:

| Modo | Qué pasa | ¿Puedes entrar a localhost:8501? |
|------|----------|----------------------------------|
| **Background `-d` (elegido)** | `instalar.sh` levanta el contenedor, imprime la URL y **termina**. Streamlit sigue corriendo en Docker. | **Sí** — abres `http://localhost:8501` cuando quieras |
| Foreground | La terminal queda “pegada” mostrando logs; Ctrl+C puede tumbar el proceso si no es contenedor | También sí, pero peor UX |

**Acuerdo:** al final de `instalar.sh`:

```bash
docker compose up -d streamlit
echo "Interfaz: http://localhost:8501"
```

El usuario entra al navegador (en Windows, con Docker Desktop + WSL, normalmente basta esa URL). No hace falta dejar la terminal bloqueada.

---

## 4. Arquitectura objetivo

```text
┌─────────────────────────────────────────────────────────────┐
│                     ./instalar.sh                           │
│                  (orquestador único, raíz)                  │
└───────┬─────────────┬──────────────────┬────────────────────┘
        │             │                  │
        ▼             ▼                  ▼
  [1] Limpieza   [2] Compose up     [3] Pipeline (one-shot)
  selectiva      MySQL healthy      contenedor Python:
  del proyecto   + red + vol.         01_descarga.py
                                      03_limpieza.py
                                      schema.sql → mysql
                                      04_etl_mysql.py
                                                     │
                                                     ▼
                                               MySQL datos
                                                     │
                     [4] Compose up Streamlit ◄──────┘
                              (GUI :8501)
```

### Roles

| Pieza | Rol |
|-------|-----|
| `instalar.sh` | Orquesta limpieza → infra → pipeline → Streamlit |
| `docker-compose.yml` | Servicios `mysql` + `streamlit` (+ servicio `pipeline` one-shot o perfil) |
| `Dockerfile` / `Dockerfile.pipeline` | Imagen Python con deps del pipeline |
| `Dockerfile.streamlit` (o multi-stage / misma imagen) | Imagen de la app Streamlit |
| `requirements.txt` | Dependencias Python (pipeline + app, o dos archivos si se separan) |
| `sql/schema.sql` | DDL: DB + 9 tablas + vista `v_linea_analisis` |
| `scripts/01_descarga_datos.py` | Extract NIST → `data/originales/` |
| `scripts/03_limpieza_datos.py` | Transform → `data/procesados/` |
| `scripts/04_etl_mysql.py` | Load → MySQL |
| `app/streamlit_app.py` (o paquete `app/`) | UI + queries propias |
| `.gitattributes` | `*.sh text eol=lf` |
| `.gitignore` | venv, `__pycache__`, datos generados, checkpoints |

### Red y hosts

| Quién | Host MySQL | Puerto |
|-------|------------|--------|
| Contenedor pipeline / Streamlit | `mysql` (nombre de servicio Compose) | `3306` |
| DBeaver / cliente en el host (opcional, no requerido) | `localhost` | `3306` |

### Credenciales fijas (en compose / env del compose)

| Parámetro | Valor |
|-----------|-------|
| `MYSQL_ROOT_PASSWORD` | `root` |
| `MYSQL_DATABASE` | `optica_y_fotonica` |
| Contenedor MySQL | `mysql_container` (o renombrar de forma consistente) |
| Red | `jupyter_mysql` → **renombrar** a algo neutro, p. ej. `optica_net` (ya no hay Jupyter) |
| Volumen | `mysql_data` |
| Streamlit | puerto host `8501:8501` |

**Nice to have (futuro, no bloqueante):** `.env` + `.env.example` para `MYSQL_*` (compose con `env_file`), sin versionar el `.env` real. Hoy las variables viven en `docker-compose.yml`; es suficiente para laboratorio.

### Dump portable `init.sql` (camino Docker Hub)

Tras un MySQL ya cargado por el pipeline:

```bash
docker exec mysql_container mysqldump -uroot -proot \
  --databases optica_y_fotonica --default-character-set=utf8mb4 \
  --single-transaction --routines --triggers --set-gtid-purged=OFF \
  -r /tmp/init.sql
docker cp mysql_container:/tmp/init.sql ./init.sql
```

- Tamaño tipico: **~4.5 MB**; ~52 812 filas en tablas + vista.
- Uso: montar o hornear en `/docker-entrypoint-initdb.d/` (solo primer arranque con volumen vacío).
- Regenerar dump **antes** de `down -v` si se vuelve a poblar con pipeline.
- **Nice to have:** recortar H–Ne (menos elementos/líneas) si el import se percibe lento; no es crítico con ~5 MB.
- `instalar.sh` **no** se incluye en la imagen Hub; el arranque público objetivo es compose (+ init), no el pipeline NIST.

---

## 5. Estructura de repositorio objetivo

```text
primer-parcial/
├── instalar.sh                 # Único comando de entrada
├── docker-compose.yml          # mysql + streamlit (+ pipeline)
├── Dockerfile.pipeline         # (nombre tentativo)
├── Dockerfile.streamlit        # (nombre tentativo)
├── requirements.txt            # o requirements-pipeline.txt + requirements-app.txt
├── PLAN_AUTOMATIZACION.md      # Este plan (ancla de contexto)
├── README.md                   # Cómo clonar y ejecutar (actualizar)
├── .gitignore
├── .gitattributes
├── sql/
│   └── schema.sql
├── scripts/
│   ├── 01_descarga_datos.py
│   ├── 03_limpieza_datos.py
│   └── 04_etl_mysql.py
├── app/
│   ├── streamlit_app.py        # entrada Streamlit
│   ├── db.py                   # conexión / helpers
│   ├── pages/ o secciones      # módulos por pantalla (opcional)
│   └── ...
├── data/                       # generada en runtime (idealmente no versionar CSV grandes)
│   ├── originales/             # salida 01 (ex notebooks/datos_originales)
│   └── procesados/             # salida 03 (ex notebooks/datos_procesados)
├── docs/                       # documentación técnica (actualizar rutas; quitar refs a Jupyter/notebooks)
│   ├── 02_...md                # puede quedar como historial metodológico del diagnóstico
│   ├── 03_...md
│   ├── 04_...md
│   └── 05_...md
```

> La carpeta `automatizacion/` (referencia del proyecto anterior) **fue eliminada en Fase 7** (D18).


### Qué se elimina / deja de ser el camino principal

- Carpeta `notebooks/**/*.ipynb` (01–05).
- Servicio `jupyter` en `docker-compose.yml`.
- Pasos de README que digan “abre Jupyter / ejecuta schema en DBeaver / corre notebooks en orden”.
- Dependencia de CSV ya presentes en el repo para el flujo feliz (el 01 debe poder poblar `data/originales/` solo).

### Nota sobre CSV actualmente versionados

Hoy hay `notebooks/datos_originales/` y `datos_procesados/` en el repo.  
**Decisión final (D14):** se dejan de versionar; pasan a generarse bajo `data/` en cada instalación. En la fase de limpieza del repo se eliminan del tracking de Git.

---

## 6. Flujo detallado de `instalar.sh`

Convenciones:

- `set -euo pipefail`
- Detectar `docker compose` (plugin) o `docker-compose`
- En WSL/Linux: preferir Docker sin forzar `sudo` si el usuario está en el grupo `docker`; si hace falta, documentar. El script de referencia usaba `sudo`; adaptar con detección.
- Mensajes claros `[1/4]`, `[2/4]`, …

### [1/4] Limpieza selectiva del proyecto

Solo recursos de este stack (nunca `docker system prune` global):

1. `docker compose -f docker-compose.yml down -v --remove-orphans`
2. Eliminar contenedores por nombre si quedaron huérfanos (`mysql_container`, `streamlit_optica`, `pipeline_optica`, etc.)
3. Eliminar volumen `mysql_data` (y el prefijo de proyecto Compose si aplica)
4. Eliminar red del proyecto (`optica_net` / la que quede definida)
5. Eliminar imágenes usadas por este proyecto (mysql:8.4, imagen pipeline, imagen streamlit)

### [2/4] Infraestructura MySQL

1. `docker compose up -d mysql` (o `up -d` solo del servicio mysql)
2. Esperar healthcheck `healthy` (bucle con tope de intentos, como el script de astronomía)
3. Mostrar `docker compose ps` / datos de conexión

### [3/4] Pipeline de datos (dentro de Docker)

Orden estricto:

1. **Descarga** — `python scripts/01_descarga_datos.py`  
   - Endpoints NIST: `lines1.pl`, `energy1.pl`  
   - Escribe: `data/originales/nist_lines_H_Ne_original.csv`  
   - Escribe: `data/originales/niveles/nist_levels_*_original.csv` (18 espectros)  
   - Escribe: `data/originales/nist_levels_todos_original.csv`  
   - Reintentos / timeouts ante fallos de red  
   - No modificar archivos tras guardar (evidencia cruda)

2. **Limpieza** — `python scripts/03_limpieza_datos.py`  
   - Lee solo `data/originales/`  
   - Aplica L1–L14 (misma lógica que el notebook 03)  
   - Escribe `data/procesados/` (`lineas_limpias.csv`, `niveles_limpios.csv`, CSVs de tablas, diccionario, etc.)

3. **Schema** — aplicar DDL sin DBeaver:  
   ```bash
   docker exec -i mysql_container mysql -uroot -proot < sql/schema.sql
   ```  
   (o equivalente desde el contenedor pipeline montando el SQL)

4. **ETL** — `python scripts/04_etl_mysql.py`  
   - Espera MySQL con reintentos  
   - Host: `mysql`  
   - Inserta en orden de FKs (catálogos → espectro → niveles/líneas → tablas puente)  
   - Misma semántica que el notebook 04

Implementación del paso 3 en Compose (elegir una en implementación; preferida = A):

- **A (preferida):** servicio `pipeline` con `profiles: ["pipeline"]` o sin `restart`, invocado con  
  `docker compose run --rm pipeline`  
  que ejecute un entrypoint `run_pipeline.sh` interno: descarga → limpieza → schema → etl.
- **B:** `instalar.sh` hace varios `docker compose run --rm pipeline python scripts/0X_....py` en secuencia.

### [4/4] Streamlit

```bash
docker compose up -d streamlit
```

- Puerto `8501`
- Variables de entorno MySQL apuntando a `mysql` / `root` / `root` / `optica_y_fotonica`
- `depends_on: mysql: condition: service_healthy` (los datos ya deben estar cargados por el paso 3 antes de subir Streamlit)
- Mensaje final: URL `http://localhost:8501` + credenciales MySQL para inspección opcional

El script termina tras `up -d streamlit` e imprime `http://localhost:8501`. Streamlit queda corriendo en Docker; el usuario abre esa URL en el navegador (ver §3.5).

---

## 7. Scripts Python — alcance de traducción

### 7.1 `scripts/01_descarga_datos.py` (ex-notebook 01)

- Descargar líneas H–Ne (I y II) vía `lines1.pl`.
- Descargar 18 espectros de niveles vía `energy1.pl`.
- Consolidar niveles.
- Guardar bajo `data/originales/` sin alterar contenido crudo.
- Logging claro de URLs, filas, rutas, tamaños.
- Fallar con código ≠ 0 si NIST no responde tras reintentos (el `.sh` aborta por `set -e`).

### 7.2 `scripts/03_limpieza_datos.py` (ex-notebook 03)

- Portar decisiones L1–L14 y exportación a `data/procesados/`.
- No imputar Aki; conservar ética científica del proyecto.
- Validaciones de aceptación al final (conteos esperados como checks blandos o asserts documentados).
- **No** incluir el recorrido exploratorio del 02 (gráficos de diagnóstico), salvo utilidades mínimas compartidas (p. ej. decodificar `="..."`).

### 7.3 `scripts/04_etl_mysql.py` (ex-notebook 04)

- Conexión parametrizada por env: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`.
- Defaults dentro de Docker: host `mysql`, resto root/root/`optica_y_fotonica`.
- Cargar desde `data/procesados/` hacia tablas ya creadas por `schema.sql`.
- Orden de inserción respetando FKs.
- Idempotencia: schema.sql ya hace DROP/CREATE; el ETL asume tablas vacías post-schema o trunca de forma controlada. **Definir en implementación:** schema siempre reconstruye estructura; ETL solo INSERT.

### 7.4 No se crea `02_exploracion.py` de pipeline

El diagnóstico del 02 queda en documentación (`docs/02_...md`) si se mantiene; no bloquea la automatización.

### 7.5 Ex-notebook 05

No se traduce como script batch obligatorio. Su valor analítico pasa a **Streamlit** (queries propias + gráficos). La narrativa de la respuesta científica se puede hardcodear/resumir en una página de la app, recalculando métricas desde SQL en vivo.

---

## 8. Streamlit — mapa de interfaz (acordado)

Navegación (sidebar), estilo filtros del proyecto de astronomía:

| # | Sección | Contenido |
|---|---------|-----------|
| 1 | Inventario | Conteos: elementos, espectros, líneas, niveles; rango de λ; sanity check BD no vacía |
| 2 | Distribución espectral | Líneas por región (IR/visible/UV/…); filtros elemento / espectro / ionización |
| 3 | Cobertura Aki | % líneas con Aki por espectro; destacar coberturas bajas |
| 4 | Relación λ–Aki | Scatter log-log; Pearson/Spearman; filtros elemento, exactitud (p. ej. AAA–A) |
| 5 | Tipos de transición | Boxplot / stats E1 vs E2/M1/M2; permitidas vs prohibidas |
| 6 | Explorador de líneas | Tabla filtrable (λ, Aki, niveles, tipo, exactitud, refs) |
| 7 | Respuesta científica | Texto + métricas clave alineadas a la pregunta del proyecto |

**Sidebar global:** filtros reutilizables + crédito “creado por: Andres David Perez” (o el texto académico que se acuerde).

**Queries:** propias del GUI (pueden inspirarse en C1–C8 del notebook 05, sin obligación de ser idénticas). Usar la vista `v_linea_analisis` cuando convenga (`region_espectral`, `log10_aki`).

**Stack UI:** Streamlit + Plotly (como el proyecto de referencia) + pandas + conector MySQL/SQLAlchemy.

---

## 9. `docker-compose.yml` objetivo (bosquejo)

```yaml
services:
  mysql:
    image: mysql:8.4
    container_name: mysql_container
    # env root/root, DB optica_y_fotonica
    # ports 3306:3306
    # volume mysql_data
    # healthcheck mysqladmin ping
    # network optica_net

  pipeline:
    build: { context: ., dockerfile: Dockerfile.pipeline }
    # volumes: .:/app  (o copiar en build)
    # working_dir: /app
    # env MYSQL_HOST=mysql ...
    # networks: optica_net
    # depends_on mysql healthy
    # profiles: ["pipeline"]   # no queda corriendo
    # entrypoint: descarga → limpieza → schema → etl

  streamlit:
    build: { context: ., dockerfile: Dockerfile.streamlit }
    container_name: streamlit_optica
    ports: ["8501:8501"]
    environment:
      MYSQL_HOST: mysql
      MYSQL_PORT: 3306
      MYSQL_USER: root
      MYSQL_PASSWORD: root
      MYSQL_DATABASE: optica_y_fotonica
    depends_on:
      mysql:
        condition: service_healthy
    networks: [optica_net]
    restart: unless-stopped

networks:
  optica_net:
    driver: bridge

volumes:
  mysql_data:
```

**Decisión D15:** dos Dockerfiles / dos imágenes (`Dockerfile.pipeline` y `Dockerfile.streamlit`). Red **`optica_net`**, contenedor UI **`streamlit_optica`**.

---

## 10. Requisitos del entorno (usuario final)

| Requisito | Notas |
|-----------|--------|
| Docker Engine + Compose | Docker Desktop en Windows con integración WSL2 recomendada |
| WSL (si Windows) o Linux | Para ejecutar `./instalar.sh` |
| Puertos libres `3306` y `8501` | Si están ocupados, el script falla; documentar en README |
| Internet | Imágenes Docker, `pip` en build, API NIST |
| Git clone | Repo completo |

No se requiere: Python en el host, Jupyter, DBeaver, venv local, edición de `.env`.

---

## 11. Fases de trabajo (una fase ≈ una sesión de Cursor)

**Cómo usar esto:** al empezar una sesión, decir “implementa la Fase N” y leer este plan. No mezclar dos fases grandes en el mismo chat si el contexto ya está cargado. Marcar checkboxes al cerrar cada fase.

---

### Fase 0 — Plan y acuerdos *(hecha)*
**Entregable:** este documento con decisiones cerradas.  
**No se toca código de producto.**

- [x] Arquitectura acordada
- [x] Preguntas menores 1–6 cerradas (CSV, 2 imágenes, Streamlit `-d`, docs, borrar `automatizacion/`, `optica_net`)
- [x] Fases partidas para trabajo incremental

**Criterio de salida:** se puede empezar Fase 1 sin ambigüedad de diseño.

---

### Fase 1 — Infraestructura Docker (sin datos reales aún) *(hecha)*
**Entregable:** Compose + Dockerfiles + ignores; MySQL y un Streamlit “hola mundo” levantan.

- [x] Reescribir `docker-compose.yml`: quitar Jupyter; red `optica_net`; servicios `mysql`, `pipeline` (profile), `streamlit`
- [x] Crear `Dockerfile.pipeline` y `Dockerfile.streamlit` (dos imágenes)
- [x] `requirements-pipeline.txt` y `requirements-app.txt` (mínimos; app pinned `streamlit==1.51.0`)
- [x] `.gitattributes` → `*.sh text eol=lf`
- [x] `.gitignore` → CSV en `data/`, `__pycache__/`, etc.
- [x] Stub `app/streamlit_app.py` que muestre “Óptica y Fotónica — OK” y pruebe ping a MySQL si está up
- [x] Crear carpetas `scripts/`, `data/originales/`, `data/procesados/`, `app/` (con `.gitkeep`)
- [x] Probar a mano: `docker compose up -d mysql streamlit` y abrir `http://localhost:8501`

**Criterio de salida:** MySQL healthy + Streamlit accesible en localhost (aunque la BD esté vacía).  
**Aún no:** scripts 01/03/04 ni `instalar.sh` completo.

#### Estado del repo tras Fase 1 (qué se desarrolló)

| Path | Qué hace |
|------|----------|
| `docker-compose.yml` | Servicios `mysql`, `streamlit`, `pipeline` (profile `pipeline`); red `optica_net`; volumen `mysql_data` |
| `Dockerfile.pipeline` | Python 3.11 + deps pipeline + `mysql-client` (para schema en fases siguientes) |
| `Dockerfile.streamlit` | Python 3.11 + Streamlit; escucha `0.0.0.0:8501`; flags headless/CORS/XSRF para Docker |
| `requirements-pipeline.txt` | pandas, requests, numpy, conectores MySQL |
| `requirements-app.txt` | streamlit==1.51.0, plotly, pandas, numpy, conectores MySQL |
| `app/streamlit_app.py` | Stub UI + ping MySQL por env (`MYSQL_HOST=mysql`, …) |
| `scripts/.gitkeep` | Placeholder hasta Fase 2 |
| `data/originales/.gitkeep`, `data/procesados/.gitkeep` | Destino de CSV regenerados (ignorados por git) |
| `.gitattributes` | Fuerza LF en `*.sh` |
| `.gitignore` | Ignora CSV en `data/`, venv, pycache |

**Cómo probar Fase 1:**

```bash
docker compose up -d --build mysql streamlit
# Abrir http://localhost:8501  (o http://127.0.0.1:8501)
docker compose ps
docker compose down          # apaga sin borrar datos
docker compose down -v       # apaga y borra volumen MySQL
```

**Nota UI:** si la página queda en negro/blanco vacío, hard-refresh (Ctrl+F5) o rebuild con la imagen pinned a Streamlit **1.51.0** (evitar 1.65+). Dataframes/plotly usan `width="stretch"` (reemplazo de `use_container_width`).  
**README / docs/02–05:** actualizados en **Fase 7** (flujo `./instalar.sh` + scripts + Streamlit).


---

### Fase 2 — Script de descarga (ex-notebook 01) *(hecha)*
**Entregable:** `scripts/01_descarga_datos.py` funcional dentro del contenedor pipeline.

- [x] Portar descarga `lines1.pl` + `energy1.pl` (18 espectros)
- [x] Salidas en `data/originales/` (+ `niveles/`)
- [x] Reintentos / errores con exit code ≠ 0
- [x] Probar: `docker compose --profile pipeline run --rm pipeline python scripts/01_descarga_datos.py`

**Criterio de salida:** existen los CSV crudos regenerados sin notebooks.  
**Dependencia:** Fase 1.

#### Estado tras Fase 2

| Path | Contenido |
|------|-----------|
| `scripts/01_descarga_datos.py` | Descarga NIST con reintentos (3), pause 1s entre niveles, exit ≠ 0 si falla; valida CSV (rechaza HTML/`Unknown parameter`) |
| `data/originales/nist_lines_H_Ne_original.csv` | Texto crudo lines1.pl (~4.1 MB) |
| `data/originales/niveles/nist_levels_*_original.csv` | 18 CSV crudos energy1.pl |
| `data/originales/nist_levels_todos_original.csv` | Consolidado con columna `espectro` (**5 752** filas, 13 cols — alineado al notebook) |

**Nota NIST (2026):**  
- `energy1.pl` renombró parámetros (`show_conf` → `conf_out`, etc.).  
- `lines1.pl` requiere explícitamente `g_out`, `f_out`, `loggf_out`, `ids_out` para traer `g_i`/`g_k`, `fik`, `log_gf`, `ID_i`/`ID_k` (necesarios en Fase 3).

```bash
docker compose --profile pipeline run --rm pipeline python scripts/01_descarga_datos.py
```

---

### Fase 3 — Script de limpieza (ex-notebook 03) *(hecha)*
**Entregable:** `scripts/03_limpieza_datos.py` → `data/procesados/`.

- [x] Portar L1–L14 (misma ética: no imputar Aki, etc.)
- [x] Exportar CSV que el ETL necesita
- [x] Checks de conteos (18 288 líneas, 5 752 niveles)
- [x] Probar encadenado: 01 → 03 dentro del pipeline

**Criterio de salida:** `data/procesados/` listo para cargar.  
**Dependencia:** Fase 2.

#### Estado tras Fase 3

| Path | Contenido |
|------|-----------|
| `scripts/03_limpieza_datos.py` | Port del notebook 03 (generado/ajustado); stubs de plots; asserts finales |
| ~~`scripts/_gen_03_from_nb.py`~~ | Eliminado en Fase 7 (ya no hay notebooks fuente) |
| `data/procesados/lineas_limpias.csv` | 18 288 × 47 |
| `data/procesados/niveles_limpios.csv` | 5 752 × 14 |
| `data/procesados/dataset_limpio.csv` | 18 288 × 65 |
| `data/procesados/diccionario_columnas.csv` | 58 × 5 |

**Dependencia de Fase 2 corregida:** `01_descarga_datos.py` debe pedir `g_out`, `f_out`, `loggf_out`, `ids_out` en `lines1.pl` (sin eso faltan `ID_i`/`ID_k`/`fik`/`log_gf`/`g_i`/`g_k` y falla L6+).

```bash
docker compose --profile pipeline run --rm pipeline python scripts/03_limpieza_datos.py
```

---

### Fase 4 — Schema + ETL (ex-notebook 04) *(hecha)*
**Entregable:** carga automática en MySQL sin DBeaver.

- [x] Ajustar comentarios de `sql/schema.sql` (flujo automatizado)
- [x] Portar `scripts/04_etl_mysql.py` (env `MYSQL_HOST=mysql`, …)
- [x] Entrypoint `scripts/run_pipeline.sh`: 01 → 03 → schema+04
- [x] Probar ETL: 52 812 filas, 0 FK huérfanas, vista 18 288

**Criterio de salida:** base `optica_y_fotonica` poblada solo con el contenedor pipeline.  
**Dependencia:** Fase 3.

#### Estado tras Fase 4

| Path | Rol |
|------|-----|
| `scripts/04_etl_mysql.py` | Aplica `sql/schema.sql` (`mysql --skip-ssl`), construye 9 tablas desde CSV limpios, TRUNCATE+INSERT, verifica |
| `scripts/run_pipeline.sh` | Orquesta 01 → 03 → 04 (CMD del `Dockerfile.pipeline`) |
| MySQL `optica_y_fotonica` | 9 tablas + `v_linea_analisis` pobladas |

Conteos verificados: elemento 10, tipo 5, exactitud 13, referencia 377, espectro 18, nivel 5 752, línea 18 288, línea_ref 24 757, nivel_ref 3 592 (**total 52 812**).

```bash
# Solo ETL (si ya existen CSV procesados):
docker compose --profile pipeline run --rm --entrypoint python pipeline scripts/04_etl_mysql.py

# Pipeline completo (descarga + limpieza + ETL):
docker compose --profile pipeline run --rm pipeline
```

---

### Fase 5 — Orquestador `instalar.sh` *(hecha)*
**Entregable:** un comando en la raíz que haga wipe → MySQL → pipeline → Streamlit `-d`.

- [x] Escribir `./instalar.sh` (`set -euo pipefail`, detección compose, limpieza selectiva, healthcheck, mensajes `[n/4]`)
- [x] Al final: `docker compose up -d streamlit` + echo de `http://localhost:8501`
- [x] Probar de punta a punta (bash/WSL; ~4 min con rebuild + NIST)

**Criterio de salida:** en máquina limpia de este stack, solo `./instalar.sh` deja MySQL+datos+UI.  
**Dependencia:** Fase 4. Streamlit aún puede ser el stub de Fase 1.

#### Estado tras Fase 5

| Path | Rol |
|------|-----|
| `instalar.sh` (raíz) | Wipe selectivo → MySQL healthy → pipeline 01+03+04 → Streamlit `-d` |

```bash
chmod +x instalar.sh
./instalar.sh
# UI: http://localhost:8501
```

**Nota Windows/WSL:** los `.sh` deben estar en LF (`.gitattributes`). El `instalar.sh` además ejecuta `sed` sobre `scripts/*.sh` dentro del contenedor para tolerar CRLF del volumen OneDrive/Windows.

---

### Fase 6 — Aplicación Streamlit completa *(hecha)*
**Entregable:** las 7 secciones con filtros y Plotly contra MySQL real.

- [x] `app/db.py` (conexión por env)
- [x] Secciones 1–7 (inventario → respuesta científica)
- [x] Filtros sidebar estilo astronomía
- [x] Queries propias (vista `v_linea_analisis` donde convenga)
- [x] Crédito en sidebar
- [x] Rebuild/recreate Streamlit y verificar en `:8501` (MySQL ping 18 288 líneas)

**Criterio de salida:** UI usable y alineada a la pregunta científica.  
**Dependencia:** Fase 4 (datos).

#### Estado tras Fase 6

| Path | Rol |
|------|-----|
| `app/db.py` | Engine SQLAlchemy + `read_sql` con `IN` expanding |
| `app/streamlit_app.py` | 7 secciones, filtros globales, Plotly, respuesta científica |

Secciones: Inventario · Distribución · Cobertura Aki · λ–Aki · Tipos · Explorador · Respuesta.

**Nota Compose:** `instalar.sh` fija `COMPOSE_PROJECT_NAME=primer-parcial` para que WSL y Windows no creen redes/proyectos distintos con el mismo `container_name`.

---

### Fase 7 — Limpieza del repositorio + docs *(hecha)*
**Entregable:** repo alineado al nuevo flujo; sin Jupyter/notebooks/`automatizacion/`.

- [x] Eliminar `notebooks/**/*.ipynb` (y todo `notebooks/`)
- [x] Eliminar CSV versionados bajo `notebooks/datos_*` (ya no se versionan)
- [x] Eliminar carpeta `automatizacion/`
- [x] Eliminar `scripts/_gen_03_from_nb.py` (dependía de notebooks)
- [x] Actualizar `README.md` (WSL/Docker + `./instalar.sh` + URLs `8501`/`3306`)
- [x] Actualizar `docs/02`…`05` (rutas `data/`, scripts, sin Jupyter; 02 queda como historial metodológico)
- [x] Actualizar comentarios en `sql/schema.sql` (apuntan a `scripts/04` + Streamlit)
- [x] Revisar que no queden referencias rotas a paths eliminados

**Criterio de salida:** un clon nuevo no menciona pasos manuales obsoletos.  
**Dependencia:** tras Fase 5–6 estables.

---

### Fase 8 — Validación final *(hecha)*
**Entregable:** checklist de aceptación en verde.

- [x] Ejecutar `./instalar.sh` en entorno limpio (wipe previo OK)
- [x] Abrir `http://localhost:8501` y recorrer las 7 secciones
- [x] Comprobar MySQL `localhost:3306` / conteos básicos
- [x] Re-ejecutar `./instalar.sh` y confirmar que vuelve a un estado sano
- [x] Marcar §12 y poner estado del plan: **implementado**

#### Evidencia Fase 8 (2026-10-11)

| Chequeo | Resultado |
|---------|-----------|
| 1.ª `./instalar.sh` | exit 0 → Streamlit `:8501`, MySQL healthy |
| Conteos MySQL | elemento 10 · espectro 18 · nivel 5 752 · línea 18 288 · ref 377 · tipo 5 · exactitud 13 · linea_ref 24 757 · nivel_ref 3 592 (**52 812** filas) |
| HTTP Streamlit | `200` + `_stcore/health` = `ok` |
| UI 7 secciones | Inventario → Distribución → Cobertura → λ–Aki → Tipos → Explorador → Respuesta |
| Filtros | Sidebar: Elemento/Espectro/Región/Tipo/Exactitud + toggles Aki / AAA–A |
| Ping app→MySQL | `MySQL 8.4.11 · 18,288 líneas` |
| 2.ª `./instalar.sh` | exit 0; mismos conteos; UI/HTTP OK de nuevo |

**Criterio de salida:** definición de terminado (§12) cumplida.  
**Dependencia:** Fases 1–7.

---

### Mapa rápido de dependencias

```text
Fase 0 (plan)
   └─► Fase 1 (Docker stub)
          ├─► Fase 2 (descarga)
          │      └─► Fase 3 (limpieza)
          │             └─► Fase 4 (schema+ETL)
          │                    ├─► Fase 5 (instalar.sh)
          │                    └─► Fase 6 (Streamlit UI)  ← puede solaparse con 5
          └─► Fase 7 (limpieza repo+docs)  ← después de 5+6
                 └─► Fase 8 (validación)
```

---

## 12. Checklist de aceptación (definición de terminado)

- [x] En WSL/Linux, desde un clone, `./instalar.sh` termina sin intervención.
- [x] MySQL healthy; base `optica_y_fotonica` con tablas pobladas.
- [x] No existe dependencia de abrir Jupyter ni DBeaver.
- [x] No quedan notebooks como paso obligatorio.
- [x] Streamlit responde en `http://localhost:8501` con las 7 secciones.
- [x] Filtros interactivos funcionan contra datos reales.
- [x] Re-ejecutar `./instalar.sh` vuelve a dejar el sistema en el mismo estado (wipe + rebuild).
- [x] README y `docs/` describen el flujo nuevo (scripts + `./instalar.sh`).
- [x] Carpeta `automatizacion/` eliminada; red `optica_net`; CSV no versionados en `data/`.

---

## 13. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| NIST lento o caído | Reintentos, timeouts, mensajes claros; fallar el script si no hay datos |
| Puerto 3306/8501 ocupado | Detectar/fallar con mensaje; documentar cambio de mapeo |
| CRLF en `instalar.sh` | `.gitattributes` `eol=lf` |
| Contexto de chat de Cursor se llena | **Una fase por sesión**; leer este PLAN al retomar |
| Port de limpieza 03 muy grande | Fase 3 partida en 3a/3b si hace falta |
| UI Streamlit grande | Fase 6 partida en 6a/6b/6c si hace falta |
| Build Docker lento | Cache de capas; dos imágenes enfocadas |
| Windows sin WSL | Fuera de alcance v1; README exige WSL o Linux |

---

## 14. Preguntas menores — cerradas

| # | Pregunta | Resolución |
|---|----------|------------|
| 1 | ¿CSV en Git? | **No.** Regenerar siempre (`data/` ignorada). Mejor para reproducibilidad del proceso. |
| 2 | ¿Una o dos imágenes? | **Dos** (pipeline + Streamlit). |
| 3 | ¿Background o foreground? | **Background `-d`**. La UI se abre en `http://localhost:8501` en el navegador. |
| 4 | ¿Docs? | **Actualizar** `docs/` + README. |
| 5 | ¿Borrar `automatizacion/`? | **Sí**, en Fase 7. |
| 6 | ¿Red / nombres? | Red **`optica_net`**; contenedor UI **`streamlit_optica`**. |

---

## 15. Resumen en una frase

> **Wipe del stack Docker → MySQL healthy → pipeline Python en contenedor (descarga NIST → limpieza → schema → ETL) → Streamlit en Docker (`-d`) en `http://localhost:8501`; todo disparado por `./instalar.sh` en la raíz, sin Jupyter ni notebooks.**

---

## 16. Historial de acuerdos (conversación)

| Fecha | Acuerdo |
|-------|---------|
| 2026-10-10 | Streamlit en Docker; ETL en `.py`; instalación completa con borrado de volumen; WSL OK; pipeline B1 en Docker; reemplazar notebooks; descarga NIST siempre; UI con 7 secciones + filtros; queries propias; `instalar.sh` en raíz; sin Jupyter; plan detallado en este `.md`. |
| 2026-10-10 | Confirmado: notebook 02 no es dependencia de datos del 03; se omite del pipeline. |
| 2026-10-10 | CSV no versionados; 2 Dockerfiles; Streamlit en `-d` (localhost:8501); actualizar docs; borrar `automatizacion/`; red `optica_net`; plan dividido en Fases 0–8. |
| 2026-10-10 | **Fase 1 hecha:** compose sin Jupyter; `optica_net`; Dockerfiles pipeline/streamlit; stub UI; MySQL healthy + Streamlit HTTP 200 en `:8501`. |
| 2026-10-10 | **Fase 2 hecha:** `scripts/01_descarga_datos.py`; CSV en `data/originales/`; params `energy1.pl` actualizados; consolidado 5 752 niveles; probado en `pipeline` (exit 0). |
| 2026-10-10 | **Fase 3 hecha:** `scripts/03_limpieza_datos.py`; `data/procesados/` con 4 CSV; checks 18288/5752 OK. Ajuste Fase 2: `lines1.pl` + `g_out`/`f_out`/`loggf_out`/`ids_out`. |
| 2026-10-10 | **Fase 4 hecha:** `04_etl_mysql.py` + `run_pipeline.sh`; schema auto; MySQL 52 812 filas; 0 FK huérfanas. |
| 2026-10-10 | **Fase 5 hecha:** `instalar.sh` en raíz; prueba E2E OK (Streamlit `:8501`); mitigación CRLF en scripts montados. |
| 2026-10-10 | **Fase 6 hecha:** UI Streamlit 7 secciones + filtros + Plotly; `COMPOSE_PROJECT_NAME` fijo en `instalar.sh`. |
| 2026-10-10 | **Fase 7 hecha:** eliminados `notebooks/`, `automatizacion/`, `_gen_03_from_nb.py`; README + docs/02–05 + `schema.sql` alineados a `./instalar.sh`. |
| 2026-10-11 | **Fase 8 hecha:** doble `./instalar.sh` OK; MySQL 52 812 filas; Streamlit 7 secciones + filtros; plan marcado **implementado**. |
| 2026-10-20 | Streamlit pin **1.40.2 → 1.51.0** (estable; `width="stretch"` en UI; evitar 1.65+). `.env` documentado como nice-to-have (no implementado). |
| 2026-10-20 | Dump **`init.sql`** (~4.5 MB) desde `mysql_container` (`optica_y_fotonica`, ~52 812 filas). Camino Hub: init en primer arranque, sin pipeline obligatorio. Reducir datos = nice to have. `instalar.sh` no va dentro de la imagen Hub. |
| 2026-10-20 | **Refactor entrega:** un `Dockerfile` + `requirements.txt` pinneado; `.dockerignore`; compose monta `init.sql` (opción A); sin servicio `pipeline`; arranque `docker compose up -d --build`; `instalar.sh` solo atajo local. |
| 2026-10-20 | **Limpieza repo:** eliminados `scripts/`, `data/`, `sql/`, `instalar.sh`. Runtime = compose + `init.sql` + `app/`. Conservados `docs/` y este plan. |
| 2026-10-20 | Compose Streamlit: `image: andresperez3/optica-fotonica:latest` + `build` local. Arranque `docker compose up -d`; push documentado en README. |
| 2026-10-20 | Entrega Hub (PDF Labs 8–10): `lab-arranque.sh` / `.ps1` liberan 3306/8501, `down -v`, `pull`, `up --no-build`. Tag `latest`. Push lo hace el autor (pasos en README). |

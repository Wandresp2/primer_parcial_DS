# Documentación técnica — Pipeline ETL NIST ASD → MySQL

**Implementación:** `scripts/04_etl_mysql.py` (tras `01` y `03` en `run_pipeline.sh`)  
**Orquestación:** `./instalar.sh`  
**Proyecto:** Óptica y Fotónica — Primer Parcial  
**Estudiante:** Perez Criollo Andres David  
**Base de datos:** `optica_y_fotonica`  
**DDL:** `sql/schema.sql`  
**Justificación de limpieza:** [docs/03_limpieza_datos.md](03_limpieza_datos.md)  
**Rol en la cadena:** `01` → `02` (historial) → `03` → **04 (este)** → UI Streamlit

---

## 1. Contexto

El script `04_etl_mysql.py` aplica el DDL y carga MySQL de forma **idempotente** (vacía y vuelve a cargar). La descarga y la limpieza L1–L14 ya ocurrieron en `scripts/01_descarga_datos.py` y `scripts/03_limpieza_datos.py`.

### Orden del flujo automatizado

```
1. docker compose up -d mysql          (healthcheck)
2. pipeline: 01 → 03 → 04
   - 04 aplica sql/schema.sql
   - 04 puebla las 9 tablas desde data/procesados/
3. docker compose up -d streamlit
```

Si falta la base o alguna tabla tras el DDL, el ETL se detiene con un mensaje claro en lugar de inventar DDL ad hoc.

---

## 2. Qué se hizo (lectura simple)

Sin pasos manuales en un cliente SQL:

1. Se conecta al MySQL del Docker usando el nombre del servicio (`mysql`), no `localhost`.
2. Aplica `sql/schema.sql` (base + 9 tablas + vista).
3. Lee los CSV relacionales generados por la limpieza (`data/procesados/tabla_*.csv`).
4. Vacía las tablas en el orden seguro respecto a las claves foráneas y las vuelve a llenar.
5. Verifica conteos e integridad (cero referencias rotas).

El resultado es una base lista para la UI Streamlit (`app/streamlit_app.py`).

---

## 3. Recorrido del script

| Paso | Qué hace |
|---|---|
| Conexión | SQLAlchemy/PyMySQL; host `mysql` en red `optica_net` |
| DDL | Ejecutar `sql/schema.sql` vía cliente mysql |
| Lectura | Cargar `tabla_*.csv` desde `data/procesados/` |
| Integridad | Chequeo de claves **antes** de insertar |
| Carga | Vaciar (orden inverso de FK) y cargar en transacción |
| Verificación | Conteos post-carga; JOINs de humo |

---

## 4. Decisiones metodológicas y justificación

### 4.1 Schema primero, datos después

**Qué:** El script aplica DDL desde `sql/schema.sql` y luego DML (DELETE/TRUNCATE + INSERT). El modelo no se inventa en Python.

**Por qué:** Separar definición de estructura y carga automatizada. Mezclar `CREATE TABLE` ad hoc ocultaría el modelo y dificultaría reconstruir la base desde cero.

### 4.2 Host `mysql`, no `localhost`

**Qué:** La URL de conexión usa el hostname del servicio Compose.

**Por qué:** Pipeline y Streamlit están en la red Docker `optica_net`. Desde esos contenedores, `localhost` sería el propio contenedor, no el servidor MySQL.

### 4.3 Idempotencia (vaciar y recargar)

**Qué:** Cada ejecución limpia las 9 tablas y vuelve a insertar.

**Por qué:** Evita errores de clave duplicada al re-correr `./instalar.sh` o el profile `pipeline`. El vaciado respeta dependencias (hijo antes que padre; o FK desactivadas temporalmente según la implementación).

### 4.4 Limpieza L1–L14 fuera del ETL

**Qué:** La transformación ya ocurrió en `scripts/03_limpieza_datos.py`; el ETL carga tablas ya normalizadas.

**Por qué:** El ETL debe ser reproducible desde los artefactos de `data/procesados/`. Las justificaciones físicas y estadísticas **viven** en [docs/03_limpieza_datos.md](03_limpieza_datos.md); aquí se documenta la carga, no se repite el tratado de limpieza.

### 4.5 Forma relacional (por qué 9 tablas)

La tabla ancha de exploración viola formas normales (listas de referencias en una celda, atributos de catálogo repetidos, derivados calculables). El modelo aplicado:

| Tabla | Rol | Filas cargadas |
|---|---|---|
| `elemento` | Catálogo H–Ne | 10 |
| `tipo_transicion` | E1, M1, … y si es permitida | 5 |
| `exactitud` | Códigos Acc del NIST + orden | 13 |
| `referencia` | Bibliografía | 377 |
| `espectro` | Ion concreto (H I, Ne II, …) | 18 |
| `nivel_energia` | Escalones del átomo | 5 752 |
| `linea_espectral` | Transiciones (hechos) | 18 288 |
| `linea_referencia` | Puente N:M línea↔ref | 24 757 |
| `nivel_referencia` | Puente N:M nivel↔ref | 3 592 |
| **Total** | | **52 812** |

**Por qué tablas puente:** las referencias vienen como listas separadas por comas (violación de 1FN). Separarlas permite integridad referencial y consultas por paper sin parsear texto.

**Por qué no guardar `region_espectral` ni `log10_aki` en la tabla de líneas:** son derivadas; se exponen en la vista `v_linea_analisis` para no violar 3FN y aun así facilitar el análisis en Streamlit.

### 4.6 Integridad antes y después de cargar

**Qué:** Se comprueban FK huérfanas en Python y de nuevo tras insertar; se contrastan conteos MySQL vs DataFrames.

**Por qué:** Cargar sin ese chequeo podría dejar una base “llena” pero científicamente inválida (líneas apuntando a niveles inexistentes). Resultado típico de la ejecución: **0** huérfanas en todas las FK críticas.

### 4.7 Parámetros NIST alineados con exploración

**Qué:** Misma estrategia de parámetros validados en el diagnóstico (docs/02); la descarga real vive en `scripts/01_descarga_datos.py`.

**Por qué:** El ETL no debe reintroducir silenciosamente un conjunto distinto al diagnosticado. Si el archivo ya está en `datos_originales/`, no se vuelve a golpear al NIST.

---

## 5. Resultados y artefactos

### Integridad y volumen (salida típica del pipeline)

- ~18 288 líneas, ~5 752 niveles en CSV limpios; ~52 812 filas totales en MySQL tras el ETL.
- Base de evidencia con Aki coherente con la limpieza (sin imputar Aki).
- Conteos MySQL alineados con los CSV de `data/procesados/`.
- 0 FK huérfanas post-carga.

### Artefactos

| Destino | Qué |
|---|---|
| MySQL `optica_y_fotonica` | 9 tablas pobladas + vista `v_linea_analisis` |
| `sql/schema.sql` | DDL aplicado por el script 04 |
| `data/procesados/` | Entrada del ETL (`tabla_*.csv`, líneas/niveles limpios) |

---

## 6. Límites y qué sigue

**Este script no:** responde la pregunta científica con gráficos ni correlación por elemento; no sustituye el diseño del modelo (ese vive en el DDL).

**Siguiente paso:** consultas y respuesta científica en la UI Streamlit  
(`app/streamlit_app.py`) / [docs/05_consultas_analisis_cientifico.md](05_consultas_analisis_cientifico.md).

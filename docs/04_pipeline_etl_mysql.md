# Documentación técnica — Pipeline ETL NIST ASD → MySQL

**Notebook:** `notebooks/04_pipeline_etl_mysql.ipynb`  
**Proyecto:** Óptica y Fotónica — Primer Parcial  
**Estudiante:** Perez Criollo Andres David  
**Base de datos:** `optica_y_fotonica`  
**DDL previo:** `sql/schema.sql`  
**Justificación de limpieza:** [docs/03_limpieza_datos.md](03_limpieza_datos.md)  
**Rol en la cadena:** `01` → `02` → `03` → **04 (este)** → `05`

---

## 1. Contexto

Este notebook ejecuta **de punta a punta y sin pasos manuales** el ciclo de datos:

**descarga (con caché) → limpieza L1–L14 → forma relacional → carga en MySQL**.

Es autocontenido (puede correrse solo) e **idempotente** (vacía y vuelve a cargar). **No crea** la base ni las tablas: el DDL vive únicamente en `sql/schema.sql`.

### Orden obligatorio del proyecto

```
1. docker compose up -d
2. Ejecutar sql/schema.sql   → crea optica_y_fotonica y 9 tablas vacías
3. Ejecutar ESTE notebook    → las puebla
```

Si falta la base o alguna tabla, el notebook se detiene en la Sección 2 con un mensaje claro en lugar de inventar DDL.

---

## 2. Qué se hizo (lectura simple)

En lugar de cargar a mano miles de filas en DBeaver, el notebook:

1. Se conecta al MySQL del Docker usando el nombre del servicio (`mysql`), no `localhost`.
2. Comprueba que las 9 tablas del esquema existan.
3. Lee (o descarga una vez) los CSV del NIST y aplica la misma limpieza ya justificada en el notebook 03.
4. Parte la tabla ancha en **catálogos + hechos + puentes** (forma normal).
5. Vacía las tablas en el orden seguro respecto a las claves foráneas y las vuelve a llenar en una sola corrida.
6. Verifica conteos e integridad (cero referencias rotas) y reexporta CSV de apoyo.

El resultado es una base lista para que el notebook 05 responda la pregunta científica con SQL.

---

## 3. Recorrido por secciones

| Sección | Qué hace |
|---|---|
| 1 | Librerías; SQLAlchemy/PyMySQL; credenciales; host `mysql` |
| 2 | Verificar que existen las 9 tablas del esquema |
| 3 | Extracción NIST con la misma estrategia de caché que exploración |
| 4 | Transformación: decisiones L1–L14 (condensadas, misma lógica) |
| 5 | Construcción de DataFrames relacionales + chequeo de integridad **antes** de insertar |
| 6 | Vaciar (orden inverso de FK) y cargar (orden de dependencia) en transacción |
| 7 | Verificación post-carga; demo de JOIN doble (línea ↔ niveles) |
| 8 | Reexportar subproductos a `datos_procesados/` |

---

## 4. Decisiones metodológicas y justificación

### 4.1 Schema primero, datos después

**Qué:** El notebook solo hace DML (DELETE/TRUNCATE + INSERT). El DDL está en `sql/schema.sql`.

**Por qué:** Es un requisito del proyecto separar definición de estructura y carga automatizada. Mezclar `CREATE TABLE` dentro del ETL ocultaría el modelo y dificultaría reconstruir la base desde cero en DBeaver.

### 4.2 Host `mysql`, no `localhost`

**Qué:** La URL de conexión usa el hostname del servicio Compose.

**Por qué:** Jupyter y MySQL están en la red Docker `jupyter_mysql`. Desde el contenedor Jupyter, `localhost` sería el propio Jupyter, no el servidor MySQL.

### 4.3 Idempotencia (vaciar y recargar)

**Qué:** Cada ejecución limpia las 9 tablas y vuelve a insertar.

**Por qué:** Evita errores de clave duplicada al re-correr el pipeline durante desarrollo o sustentación. El vaciado respeta dependencias (hijo antes que padre; o FK desactivadas temporalmente según la implementación del notebook).

### 4.4 Misma limpieza L1–L14, sin re-explicarla toda

**Qué:** Se reaplica la transformación del notebook 03 (decodificar, Ritz, no imputar Aki, IDs texto, etc.).

**Por qué:** El ETL debe ser reproducible desde los originales. Las justificaciones físicas y estadísticas **viven** en [docs/03_limpieza_datos.md](03_limpieza_datos.md); aquí se documenta el *pipeline*, no se repite el tratado de limpieza.

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

**Por qué no guardar `region_espectral` ni `log10_aki` en la tabla de líneas:** son derivadas; se exponen en la vista `v_linea_analisis` para no violar 3FN y aun así facilitar el análisis del notebook 05.

### 4.6 Integridad antes y después de cargar

**Qué:** Se comprueban FK huérfanas en Python y de nuevo tras insertar; se contrastan conteos MySQL vs DataFrames.

**Por qué:** Cargar sin ese chequeo podría dejar una base “llena” pero científicamente inválida (líneas apuntando a niveles inexistentes). Resultado típico de la ejecución: **0** huérfanas en todas las FK críticas.

### 4.7 Parámetros NIST alineados con exploración

**Qué:** Misma estrategia de caché y parámetros validados en el notebook 02 (versión corregida para el pipeline).

**Por qué:** El ETL no debe reintroducir silenciosamente un conjunto distinto al diagnosticado. Si el archivo ya está en `datos_originales/`, no se vuelve a golpear al NIST.

---

## 5. Resultados y artefactos

### Integridad y volumen (salida típica del notebook)

- 18 288 líneas, 5 752 niveles, 0 valores físicamente imposibles en la validación condensada.
- Base de evidencia con Aki: 12 603 (coherente con limpieza).
- Conteos MySQL = conteos Python en las 9 tablas.
- 0 FK huérfanas post-carga.

### Artefactos

| Destino | Qué |
|---|---|
| MySQL `optica_y_fotonica` | 9 tablas pobladas + vista `v_linea_analisis` |
| `sql/schema.sql` | Estructura vacía (prerrequisito) |
| `notebooks/datos_procesados/` | Reexport de líneas/niveles limpios y/o `tabla_*.csv` según celdas del notebook |

---

## 6. Límites y qué sigue

**Este notebook no:** responde la pregunta científica con gráficos ni correlación por elemento; no sustituye el DDL; no debe ejecutarse contra un MySQL sin `schema.sql`.

**Siguiente paso:** consultas y respuesta científica en  
`notebooks/05_consultas_analisis_cientifico.ipynb` / [docs/05_consultas_analisis_cientifico.md](05_consultas_analisis_cientifico.md).

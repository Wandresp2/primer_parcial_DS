# Documentación técnica — Limpieza y transformación de datos

**Notebook:** `notebooks/03_limpieza_datos.ipynb`  
**Proyecto:** Óptica y Fotónica — Primer Parcial  
**Estudiante:** Perez Criollo Andres David  
**Entrada:** `notebooks/datos_originales/` (solo lectura)  
**Salida:** `notebooks/datos_procesados/`  
**Diagnóstico de partida:** `notebooks/02_exploracion_caracterizacion_datos.ipynb` / [docs/02_exploracion_caracterizacion_datos.md](02_exploracion_caracterizacion_datos.md)  
**Rol en la cadena:** `01` → `02` → **03 (este)** → `04` → `05`

---

## 1. Contexto

### Pregunta científica

> ¿Cómo se distribuyen las líneas espectrales de los primeros diez elementos de la tabla periódica (H a Ne) a lo largo del espectro electromagnético, y qué relación existe entre la probabilidad de transición espontánea (coeficiente de Einstein Aki) y la longitud de onda de emisión en cada elemento?

### Principio que gobierna toda la limpieza

> **En un dataset científico, un valor ausente es información.**

Que el NIST no haya medido el Aki de una línea no es un hueco que haya que tapar: es un hecho sobre el estado del conocimiento experimental. Por eso la limpieza es **deliberadamente conservadora**:

- **No se imputa** ningún valor en variables críticas (λ, Aki, energías, elemento).
- **No se elimina** ningún valor atípico estadístico.
- Solo se eliminan **2 filas** (cabeceras incrustadas, no observaciones).
- Solo se descartan **4 columnas** secundarias con alto % de ausencias e irrelevancia para la pregunta.

> El dataset no está sucio: está **codificado**. La ganancia viene de decodificar el formato e interpretar la notación del NIST, no de rellenar huecos.

---

## 2. Qué se hizo (lectura simple)

Partiendo de los CSV crudos (sin modificarlos), el notebook:

1. Hace visibles los verdaderos vacíos (envoltorio `="..."`).
2. Quita dos filas que no son datos sino títulos repetidos del archivo.
3. Pone todas las longitudes de onda en la misma convención (vacío), porque mezclar aire y vacío es como mezclar metros y yardas en una sola columna.
4. Lee la notación científica del NIST (`[energía]`, `+x`, etc.) en lugar de tirar esas celdas.
5. Completa λ con el valor Ritz cuando falta la medida observada (eso es física, no “promediar”).
6. **Deja Aki en blanco** donde el NIST no lo midió, y marca si hay o no hay Aki.
7. Une cada línea con sus dos niveles y exporta CSV limpios para el modelo relacional y el ETL.

---

## 3. Recorrido por secciones

Orden de **ejecución** de decisiones: L3 → L1 → L2 → L4 → L5 → L6 → L7 → L8 → L9 → L10 → L11 → L12 → L13 → L14.

| Sección | Decisión | Acción |
|---|---|---|
| 1 | Carga | Lee `datos_originales/`; reconstruye medio aire/vacío **antes** de filtrar |
| 2 | L3 | Decodificar envoltorio de exportación |
| 3 | L1 | Eliminar 2 cabeceras incrustadas |
| 4 | L2 | Unificar λ a vacío; conservar original |
| 5 | L4 | Interpretar notación NIST → valor + bandera |
| 6 | L5 | Parsear J de fracción a número |
| 7 | L6 | Proteger IDs de nivel como texto |
| 8 | L7 | Normalizar categóricas (`Type` vacío → E1; Acc ordinal) |
| 9 | L8 | λ definitiva = observada o Ritz |
| 10 | L9 | Aki **no** se imputa |
| 11 | L10 | Derivadas: `log10_aki`, región, energía del fotón |
| 12 | L11 | Descartar 4 columnas secundarias |
| 13 | L12 | Marcar 70 “duplicados” físicos; no eliminar |
| 14 | L13 | Conservar outliers IQR con justificación física |
| 15–16 | L6/L14 + diccionario | snake_case, unión por Level ID, diccionario de columnas |
| 17–18 | Validación | Criterios de aceptación + chequeo frente al esquema relacional |
| 19 | Exportación | CSV en `datos_procesados/` |

---

## 4. Decisiones L1–L14 y justificación

| ID | Nombre | Qué se hizo | Por qué | Evidencia / cifra |
|---|---|---|---|---|
| **L1** | Cabeceras incrustadas | Eliminar 2 filas que son headers del 2.º/3.er bloque del CSV | **No son observaciones**: son metadatos del formato de exportación | 18 290 → **18 288** |
| **L2** | Unificar λ a vacío | Reconstruir medio por posición; λ_vac = λ_aire × 1,00028; conservar λ original | Una columna que mezcla dos definiciones **no es una variable**; la diferencia (~0,03 %) es pequeña pero **sistemática** | Bloques: 3 689 vacío / **10 428 aire** / 4 171 vacío |
| **L3** | Decodificar `="..."` | Revelar NaN reales; no decidir aún qué hacer con ellos | Hasta que no se haga, los ausentes son **invisibles**; decodificar ≠ limpiar | **80 697** ausencias reveladas |
| **L4** | Notación NIST | Extraer número + bandera (`[]`, `+x`, `+`, `*`) | `[186101.55]` **sí contiene la energía**; no es un `tbd` basura | ~28 020 valores “no convertibles” salvados como número + bandera |
| **L5** | J fracción → número | Regex estricta; casos ambiguos quedan texto | `3/2` es 1,5; hace posible validar `g = 2J + 1` | Cumplimiento **100 %** en 5 570 casos |
| **L6** | IDs como texto | No convertir `006002.000001` a float | Convertir a número destruye ceros y **rompe la unión** con niveles | Cobertura de merge subió a ~**98,8 %** |
| **L7** | Categóricas | `Type` vacío → `E1`; `Acc` como ordinal | Vacío en Type **no es faltante**: en el ASD significa transición permitida dipolar eléctrica | Type vacío ~98,17 % |
| **L8** | Respaldo Ritz | λ definitiva = observada si existe, si no Ritz; bandera de origen | Ritz **no es estimación estadística**: es longitud de onda de la diferencia de niveles (física); imputar la mediana inventaría una línea que no existe | Base de evidencia λ+Aki: **4 462 → 12 603** |
| **L9** | No imputar Aki | Conservar NaN + bandera `tiene_aki` | Imputar Aki equivale a **inventar la respuesta** a la pregunta; la asimetría es enorme (~40); el % ausente por espectro **es** un hallazgo | 12 603 con Aki; 5 685 sin; He I 99,5 % … Ne II 12,2 % |
| **L10** | Variables derivadas | `log10_aki`, `region_espectral`, `energia_foton_ev` | Condición para responder: correlación y distribución visibles; Pearson pasa de ~0 a ~−0,61 en log-log | Tras L8: IR 43,34 %, UV 34,71 %, Vis 20,90 % |
| **L11** | Drop 4 columnas | Lande, Prefix, Suffix, Leading percentages | Criterio: **% nulos + irrelevancia** para la pregunta; Prefix ya se capturó en banderas | Nulos ~99,5 / 78,8 / 74,0 / 69,4 % |
| **L12** | Duplicados físicos | Bandera `medicion_repetida`; 0 eliminados | Son mediciones independientes del mismo salto: **valiosa, no basura** | 0 exactos; **70** por identidad física |
| **L13** | Atípicos | IQR detecta; **0 eliminados** | Los extremos suelen ser **transiciones prohibidas** (Aki órdenes de magnitud menor); IQR obliga a mirar, no a borrar | 2 181 (17,3 %) marcados por IQR en Aki |
| **L14** | Unión por Level ID | Doble merge inferior/superior + nombres snake_case | Una línea **es** un salto entre dos niveles; la clave empírica ganadora del notebook 02 | 18 073 (98,82 %) con ambos niveles; +0 filas artificiales |

### Por qué este orden

L3 va primero porque sin ver los nulos reales el resto del diagnóstico y la limpieza mentirían. L1 quita filas que no son datos antes de convertir tipos. L2 necesita el medio reconstruido desde el archivo crudo **antes** de filtrar. L8 amplía la base de λ antes de L10 (región espectral). L9 se declara explícitamente para no “arreglar” Aki por costumbre de ML. L14 al final une fuentes ya saneadas.

---

## 5. Resultados y artefactos

### Resumen de impacto

| Acción | Cantidad |
|---|---|
| Filas eliminadas | **2** (cabeceras) |
| Columnas descartadas | **4** (secundarias) |
| Imputaciones en críticas | **0** |
| Outliers eliminados | **0** |
| Líneas finales | **18 288** |
| Niveles finales | **5 752** |
| Líneas con λ + Aki (base de correlación) | **12 603** |
| Valores físicamente imposibles | **0** |

### Validación (sección 17)

Se comprueban criterios de aceptación alineados con el principio conservador: cuartiles no colapsados, 0 imposibles, IDs con ceros preservados, merge sin multiplicar filas, correlación log-log coherente (~**−0,608**).

### Chequeo frente al esquema (sección 18)

Antes del ETL se verifica que las claves que usará MySQL son viables: IDs únicos, 0 FK huérfanas de nivel en los datos limpios, espectro de la línea coherente con el de sus niveles.

### Artefactos escritos

| Archivo | Contenido |
|---|---|
| `notebooks/datos_procesados/lineas_limpias.csv` | 18 288 líneas |
| `notebooks/datos_procesados/niveles_limpios.csv` | 5 752 niveles |
| `notebooks/datos_procesados/dataset_limpio.csv` | Unión ancha de análisis |
| `notebooks/datos_procesados/diccionario_columnas.csv` | Diccionario de variables |

Los MD5 de `datos_originales/` se verifican para demostrar que la evidencia cruda no se alteró.

---

## 6. Límites y qué sigue

**Este notebook no:** crea la base MySQL, no inserta filas, no responde la pregunta con SQL.

**Siguiente paso:** el pipeline ETL en  
`notebooks/04_pipeline_etl_mysql.ipynb` / [docs/04_pipeline_etl_mysql.md](04_pipeline_etl_mysql.md), que reaplica L1–L14 de forma automatizada y carga las 9 tablas definidas en `sql/schema.sql`.

# Documentación técnica — Consultas SQL y análisis científico

**Notebook:** `notebooks/05_consultas_analisis_cientifico.ipynb`  
**Proyecto:** Óptica y Fotónica — Primer Parcial  
**Estudiante:** Perez Criollo Andres David  
**Fuente de datos:** MySQL `optica_y_fotonica` (poblada por el notebook 04)  
**Conexión:** contenedor Jupyter → host Docker `mysql`, red `jupyter_mysql`  
**Documentación previa:** [docs/04_pipeline_etl_mysql.md](04_pipeline_etl_mysql.md)  
**Rol en la cadena:** `01` → `02` → `03` → `04` → **05 (este)**

---

## 1. Contexto

### Pregunta científica

> ¿Cómo se distribuyen las líneas espectrales de H a Ne a lo largo del espectro electromagnético, y qué relación existe entre el coeficiente de Einstein Aki y la longitud de onda de emisión **en cada elemento**?

Este notebook **no descarga ni limpia de nuevo**. Lee el modelo relacional por SQL, procesa resultados con Pandas y responde las dos mitades de esa pregunta.

### Por qué SQL (y la vista)

El enunciado exige demostrar que Jupyter consulta MySQL por la red interna. Además, `region_espectral` y `log10_aki` viven en la vista `v_linea_analisis` (no se almacenan en la tabla de hechos, para no violar 3FN), así que hay que calcularlos en el servidor.

---

## 2. Qué se hizo (lectura simple)

1. Se confirma que la base correcta está llena.
2. Con SQL se cuenta cuántas líneas caen en infrarrojo, visible, ultravioleta, etc. (**todas** las líneas).
3. Se mira qué tan completo está Aki en cada espectro (porque no se inventó Aki en la limpieza).
4. Se distingue transiciones permitidas vs prohibidas (Aki bajo no es “error”).
5. Se traen a Pandas solo las filas con λ y Aki, se grafica y se correlaciona en escala logarítmica, **por elemento**.
6. Se escribe una respuesta defendible, con matices (qué mide el catálogo y qué no).

---

## 3. Recorrido por secciones

| Bloque | Contenido |
|---|---|
| 0 | Conexión Jupyter → MySQL; comprobar base `optica_y_fotonica` y que `linea_espectral` no esté vacía |
| C1–C8 | Consultas SQL progresivas (inventario → distribución → cobertura → tipos → exactitud → JOIN → subconsulta → extractor) |
| 2.1–2.5 | Análisis Pandas: distribución, justificación log-log, correlación por elemento, boxplot por tipo, lectura con cobertura |
| 3 | Respuesta consolidada a la pregunta científica |

---

## 4. Decisiones metodológicas y justificación

### 4.1 Orden de las consultas C1–C8

No es caprichoso: primero se confirma el inventario, luego la distribución (primera mitad de la pregunta) y después la evidencia de la relación λ–Aki (segunda mitad), **sin tratar todos los elementos como si estuvieran igual de medidos**.

| ID | Propósito | Justificación |
|---|---|---|
| **C1** | Inventario (elementos, espectros, líneas, niveles, rango de λ) | Sin volumen conocido no hay respuesta defendible |
| **C2** | Líneas por región (`GROUP BY` sobre la vista) | Responde la 1.ª mitad con **todas** las líneas (con o sin Aki) |
| **C3** | % de líneas con Aki por espectro | La pregunta dice *en cada elemento*; sin cobertura, la correlación no es comparable |
| **C4** | Aki típico por tipo de transición (JOIN a `tipo_transicion`) | ¿Aki bajo = error o transición prohibida? |
| **C5** | Subconjunto alta exactitud (AAA–A) | ¿La relación λ–Aki aparece también en datos que el NIST califica como buenos? |
| **C6** | Doble JOIN a niveles (ej. mayores Aki) | Muestra la física del salto y que E_sup > E_inf |
| **C7** | Subconsulta: cobertura bajo la mediana | Señala quién está peor documentado (p. ej. Ne II) |
| **C8** | Extractor de filas con λ y Aki | Muestra de trabajo para Pandas (**sin imputar** ausentes) |

### 4.2 Todas las líneas para distribución; solo con Aki para correlación

**Por qué:** La primera mitad pregunta cómo se distribuyen las transiciones tabuladas. Filtrar solo las que tienen Aki sesgaría la distribución hacia espectros mejor medidos. La segunda mitad **solo** puede calcularse donde el NIST midió Aki; inventarlo rompería la ética del notebook 03 (L9).

### 4.3 Escala log-log, no Aki crudo

**Justificación física:** el coeficiente de Einstein de emisión espontánea escala aproximadamente como \(A \propto \nu^3 |\mu|^2\). Como \(\nu = c/\lambda\), Aki tiende a ser **menor** cuando λ es mayor → nube con pendiente negativa en log-log.

**Justificación empírica:** Aki recorre muchos órdenes de magnitud. En lineal, Pearson se va a ~0 aunque la relación exista.

| Métrica | Valor (salida del notebook) |
|---|---|
| Pearson λ–Aki crudo | **−0,000848** (~0) |
| Pearson log λ – log Aki | **−0,607996** |
| Spearman log-log | **−0,644526** |
| Pearson log-log (solo exactitud AAA–A, n=3 905) | **−0,6815** |

### 4.4 Correlación **por elemento**, contrastada con cobertura

**Por qué:** Un único r global mezcla átomos con coberturas muy distintas (He I **99,5 %** de Aki vs Ne II **12,2 %**). Reportar el signo y la fuerza por elemento, y citar C3/C7, es lo que hace defendible el “en cada elemento” de la pregunta.

Resultado: **10/10** elementos con Pearson log-log **negativo** (más fuerte en H ≈ −0,689; más débil en N ≈ −0,384). En H, Spearman (−0,268) ≪ Pearson → hay tendencia, **no** una recta limpia.

### 4.5 Conservar prohibidas en el análisis

**Por qué:** En limpieza (L13) no se borraron outliers IQR. En C4/boxplot se ve que E1 tiene log₁₀(Aki) típico alto y M1/E2 mucho menor: son física distinta, no basura.

### 4.6 Aki es tasa, no “probabilidad” literal

**Por qué el cuidado de lenguaje:** Aki es el coeficiente de Einstein (s⁻¹), tasa de emisión espontánea. En la pregunta del proyecto se habla de “probabilidad de transición” en sentido amplio; la respuesta final aclara que no se interpreta como probabilidad [0,1].

---

## 5. Resultados y artefactos

### Primera mitad — distribución (C2)

| Región | Líneas | % |
|---|---|---|
| Infrarrojo | 7 926 | 43,34 % |
| Ultravioleta | 6 348 | 34,71 % |
| Visible | 3 822 | 20,90 % |
| Rayos X | — | 0,62 % |
| Microondas/Radio | — | 0,43 % |

- Visible: **3 822 (20,9 %)**  
- IR + UV: **14 274 (78,1 %)**

**Lectura simple:** en el catálogo NIST de H–Ne, la mayoría de las transiciones documentadas **no** cae en luz visible. Eso describe **cuántas transiciones distintas están tabuladas**, no la potencia luminosa de una lámpara.

### Segunda mitad — relación λ–Aki

- Muestra de trabajo: **12 603** líneas con λ y Aki (68,9 % del catálogo).
- Relación global log-log negativa (~−0,61); más fuerte en el subconjunto de alta exactitud (~−0,68).
- Signo negativo en los 10 elementos; fuerza desigual; cobertura desigual.

### Artefactos

- Resultados y figuras **dentro** del notebook (no se escriben CSV nuevos).
- Dependencia dura: MySQL poblado por `04_pipeline_etl_mysql.ipynb` y vista `v_linea_analisis` de `sql/schema.sql`.

---

## 6. Respuesta defendible (síntesis) y límites

**Distribución:** ~78 % de las líneas tabuladas de H–Ne están en IR o UV; ~21 % en visible.

**Relación Aki–λ:** donde hay Aki medido, en escala log-log hay asociación negativa coherente con \(A \propto \nu^3\); se observa en todos los elementos, con intensidad distinta y siempre condicionada a la cobertura.

**Caveats que el notebook deja explícitos (no se omiten):**

1. Los porcentajes describen el **catálogo**, no la potencia emitida por una muestra.
2. La correlación solo usa líneas con Aki (**sin imputar**).
3. El signo es común; la fuerza no (H vs N; Pearson vs Spearman en H).
4. El escalado \(\nu^3\) **encaja** con el signo observado; el notebook **no demuestra** la ley (el momento dipolar también varía).
5. Aki es **tasa** (s⁻¹), no probabilidad en [0, 1].
6. Comparar elementos exige mirar cobertura (He I vs Ne II).
7. Las transiciones prohibidas se conservaron: su Aki menor es esperable.

**Este notebook no:** modifica datos, no re-ejecuta el ETL, no sustituye la justificación de L1–L14.

**Cierre de la cadena del proyecto:** descarga → diagnóstico → limpieza → modelo/ETL → **respuesta a la pregunta científica desde Jupyter contra MySQL**.

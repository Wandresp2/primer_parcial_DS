# Documentación técnica — Exploración y caracterización de datos

**Notebook:** `notebooks/02_exploracion_caracterizacion_datos.ipynb`  
**Proyecto:** Óptica y Fotónica — Primer Parcial  
**Estudiante:** Perez Criollo Andres David  
**Fuente:** NIST Atomic Spectra Database (ASD)  
**Rol en la cadena:** `01` (descarga) → **02 (este)** → `03` (limpieza) → `04` (ETL) → `05` (consultas)

---

## 1. Contexto

### Pregunta científica que orienta todo el análisis

> ¿Cómo se distribuyen las líneas espectrales de los primeros diez elementos de la tabla periódica (H a Ne) a lo largo del espectro electromagnético, y qué relación existe entre la probabilidad de transición espontánea (coeficiente de Einstein Aki) y la longitud de onda de emisión en cada elemento?

De esa pregunta se deriva la prioridad de variables:

| Prioridad | Variables | Razón |
|---|---|---|
| Críticas | Longitud de onda, Aki, elemento/espectro, energías de los niveles | Sin ellas no se puede responder ninguna mitad de la pregunta |
| Secundarias | Incertidumbres, referencias, leading percentages, factor de Landé | Útiles para calidad y trazabilidad, no para la respuesta central |

### Qué es este notebook

Es el **diagnóstico**. Obtiene (o reutiliza en caché) las dos fuentes del NIST, las caracteriza, mide faltantes, valida física básica y construye un `df_analysis` de exploración. **No limpia:** no imputa, no unifica λ, no elimina outliers ni columnas.

---

## 2. Qué se hizo (lectura simple)

Se trabajó con dos catálogos del NIST sobre H–Ne (átomo neutro e ionizado una vez):

1. **Líneas espectrales** — cada fila es un “color” que el átomo puede emitir (un salto de un electrón entre dos niveles).
2. **Niveles de energía** — cada fila es un “escalón” interno del átomo.

Antes de tocar nada, el notebook mira el texto crudo: el NIST exporta muchos valores envueltos como `="91.23"`. Ese envoltorio hacía que Python viera “texto lleno” donde en realidad había huecos. Quitar el envoltorio **no es limpiar**: es hacer visibles los ausentes reales.

Después se midió qué tan completo está cada espectro (sobre todo Aki), se comprobaron reglas físicas (λ > 0, Aki > 0, energía superior > inferior, `g = 2J + 1`) y se unieron líneas con sus dos niveles para explorar. El resultado es un mapa de problemas que justifica la limpieza del notebook 03.

---

## 3. Recorrido por secciones

| Sección | Qué hace |
|---|---|
| 1 | Librerías y entorno (instalación solo si falta) |
| 2 | Obtención con caché (`lines1.pl` + `energy1.pl`), inspección del CSV literal, decodificación del envoltorio, registro de procedencia |
| 3 | Primera inspección separada de líneas y niveles; mapeo semántico de columnas |
| 4 | Tipos declarados vs contenido; vistas numéricas auxiliares de diagnóstico |
| 5 | Valores faltantes globales y por espectro |
| 6 | Estadística descriptiva |
| 7 | Duplicados e inconsistencias; validación física |
| 8 | Distribuciones, scatter λ–Aki, región espectral; se explica por qué **no** hay series temporales |
| 9 | Outliers por IQR: solo se cuantifican, no se eliminan |
| 10 | Correlaciones (incluye `log10(Aki)`) |
| 11 | Unión líneas ↔ niveles (prueba de estrategias de clave) → `df_analysis` |
| 12 | Diagnóstico consolidado: insumos para la limpieza |

---

## 4. Decisiones metodológicas y justificación

### 4.1 Autocontención y caché en disco

**Qué:** Si ya existen los CSV en `datos_originales/`, se leen; si no, se descargan y se guardan sin modificar.

**Por qué:** Completar niveles exige **18 peticiones** al NIST (un espectro por consulta) más 1 de líneas: 19 en total. Re-pedirlas en cada ejecución sería lento y descortés con un servidor público. El archivo guardado es **el texto crudo tal como lo devolvió el NIST**, evidencia de la fuente oficial.

### 4.2 Inspeccionar el texto crudo antes de parsear

**Qué:** Se abre el CSV como texto y se miran las primeras filas antes de `read_csv`.

**Por qué:** Ver el envoltorio `="..."` y las cabeceras incrustadas **antes** evita diagnosticar mal los tipos (“todo es texto” o “cero nulos”).

### 4.3 Decodificar el envoltorio ≠ limpiar

**Qué:** Se quita el formato de exportación Excel (`="valor"` → `valor` o NaN). Se conservan copias `_raw`.

**Por qué:** `="91.23"` y `91.23` son el mismo dato físico. Sin decodificar, `isnull()` devolvería **cero nulos** y el diagnóstico mentiría. Tras decodificar aparecen las ausencias reales (~**80 697** celdas que estaban ocultas).

> Decodificar es deshacer el envoltorio de exportación. Limpiar es tomar decisiones sobre el contenido. Eso no se hace aquí.

### 4.4 Prioridad de variables según la pregunta

**Qué:** El análisis profundo se concentra en λ, Aki, espectro y energías.

**Por qué:** La pregunta pide distribución espectral y relación Aki–λ **por elemento**. Todo lo demás es contexto o calidad, no el núcleo de la respuesta.

### 4.5 Vistas numéricas auxiliares (`errors='coerce'`)

**Qué:** Se crean `df_lines_num` / `df_levels_num` solo para histogramas y estadísticas.

**Por qué:** Permiten ver la forma de las variables sin alterar los DataFrames originales. **Esto no es la limpieza.**

### 4.6 Faltantes por espectro, no solo globales

**Qué:** Se calcula el % de Aki ausente (y otras variables) por ion (H I, He I, Ne II, …).

**Por qué:** Si Ne II casi no tiene Aki y He I sí, una correlación “por elemento” sin decirlo estaría **sesgada por cobertura**. Ese hallazgo se arrastra hasta el notebook 05.

### 4.7 Validación física (imposibles ≠ outliers)

**Qué:** Se comprueban λ > 0, Aki > 0, E_superior > E_inferior y `g = 2J + 1`.

**Por qué:** Un valor físicamente imposible no es un “punto raro”: es un error de dato. Resultado del notebook: **0** imposibles; cumplimiento de `g = 2J + 1` al **100 %** (5 570 casos comprobables); **0** filas exactamente duplicadas.

### 4.8 Escala logarítmica en Aki

**Qué:** Histogramas y correlación también en `log10(Aki)`.

**Por qué:** Aki abarca muchos órdenes de magnitud (~10⁻⁵ … 10⁹). En escala lineal casi todo se pega al cero; Pearson sobre el valor crudo queda ~0 aunque la relación exista. En el notebook: Pearson λ–Aki crudo **−0,0023** vs log-log **−0,6805** (n = 4 462 con λ observada + Aki).

### 4.9 Región espectral solo como diagnóstico

**Qué:** Se clasifican líneas en UV / visible / IR / etc. cuando hay λ.

**Por qué:** Es una forma de responder la primera mitad de la pregunta en exploración. Antes del respaldo Ritz (que llega en limpieza), ~**46 %** quedaba “sin dato” de λ observada: eso **no se “arregla” aquí**.

### 4.10 No construir series temporales

**Qué:** No se ordenan los datos por fecha de publicación ni se tratan como evolución en el tiempo.

**Por qué:** Las propiedades atómicas tabuladas son fijas; las fechas de las referencias son bibliografía, no una serie temporal del fenómeno.

### 4.11 Outliers IQR: cuantificar, no eliminar

**Qué:** Se aplica IQR a variables numéricas y se reporta cuántos puntos salen.

**Por qué:** En física atómica un atípico estadístico suele ser una transición real pero poco común (p. ej. prohibidas). Eliminarlos aquí destruiría evidencia. La decisión de conservación se formaliza en L13 del notebook 03.

### 4.12 Estrategia de unión líneas ↔ niveles

**Qué:** Se prueban claves (Level ID vs config+término+J vs energía) y se adopta **doble merge** por Level ID (nivel inferior + superior).

**Por qué empírico:** cobertura A **98,81 %**, B **97,23 %**, C **80,36 %**.  
**Por qué conceptual:** *unir para explorar, separar para modelar* — `df_analysis` sirve para diagnóstico; el esquema relacional final no es una tabla ancha.

---

## 5. Resultados y artefactos

### Cifras de diagnóstico (ejecución del notebook)

| Hallazgo | Cifra |
|---|---|
| Líneas | ~18 290 (antes de quitar cabeceras incrustadas) |
| Niveles | 5 752 |
| Espectros | 18 |
| Ausencias reveladas tras decodificar | ~80 697 |
| Violaciones físicas | 0 |
| Duplicados exactos | 0 |
| Cumplimiento `g = 2J + 1` | 100 % |
| Pearson λ–Aki (crudo) | −0,0023 |
| Pearson log-log | −0,6805 |
| Merge por Level ID (ambos niveles) | 98,81 % |

### Artefactos

- `notebooks/datos_originales/nist_lines_H_Ne_original.csv`
- `notebooks/datos_originales/nist_levels_todos_original.csv`
- `notebooks/datos_originales/niveles/nist_levels_*_original.csv` (18 archivos)
- `df_analysis` en memoria (no se escribe como “modelo final”)

Los CSV originales **no se modifican**.

---

## 6. Límites y qué sigue

**Este notebook no:** imputa Aki ni λ, no unifica aire/vacío, no elimina outliers, no carga MySQL, no responde la pregunta científica con la base poblada.

**Siguiente paso:** ejecutar y documentar la limpieza conservadora en  
`notebooks/03_limpieza_datos.ipynb` / [docs/03_limpieza_datos.md](03_limpieza_datos.md), donde cada hallazgo de este diagnóstico se convierte en una decisión L1–L14.

# Plan de trabajo — Obtención, Exploración y Diagnóstico de Datos
## Proyecto: Óptica y Fotónica (NIST Atomic Spectra Database)
### Primer Parcial — Desarrollo de Software

**Estudiante:** Perez Criollo Andres David
**Fuente oficial:** NIST Physical Reference Data – Atomic & Molecular Data (Atomic Spectra Database)
**Fecha de elaboración del plan:** Por completar al ejecutar

---

## 1. Contexto general del proyecto

El parcial exige construir un sistema completo de gestión y análisis de datos científicos,
integrando Python, Pandas, MySQL, Docker, JupyterLab y DBeaver. El ciclo completo definido
por el enunciado es:

1. Investigación del fenómeno físico y formulación de una pregunta científica
2. **Obtención de los datos desde la fuente oficial (archivo plano, sin modificar)**
3. **Exploración inicial con Python/Pandas**
4. **Limpieza y transformación de los datos**
5. Diseño del modelo relacional
6. Modelo entidad-relación en DBeaver
7. Implementación en MySQL
8. Dockerización (MySQL + JupyterLab en red compartida, con volumen persistente)
9. ETL automatizado (Python → MySQL)
10. Consultas SQL de distinto nivel de complejidad
11. Análisis científico integrando SQL + Python
12. Documentación y sustentación reproducible

Este documento cubre **los puntos 2, 3 y 4**: la etapa de obtención, exploración y
diagnóstico/limpieza de los datos, que es la base sobre la que se construirá todo lo demás
(el modelo relacional del punto 5 depende directamente de lo que se descubra aquí).

---

## 2. Pregunta científica de referencia

> **¿Cómo se distribuyen las líneas espectrales de los primeros diez elementos de la tabla
> periódica (H a Ne) a lo largo del espectro electromagnético, y qué relación existe entre
> la probabilidad de transición espontánea (coeficiente de Einstein Aki) y la longitud de
> onda de emisión en cada elemento?**

Esta pregunta orienta qué variables son críticas de cuidar en la limpieza (longitud de onda,
Aki, elemento/espectro, región espectral) y cuáles son secundarias (referencias
bibliográficas, incertidumbres, leading percentages), aunque igual se descarguen y se
inspeccionen todas.

---

## 3. Fuentes de datos y forma de obtención

Ya se construyeron dos notebooks de descarga que consultan la API pública del NIST ASD:

| Notebook | Endpoint NIST | Qué trae | Nivel de granularidad |
|---|---|---|---|
| `01_descarga_lineas_espectrales.ipynb` | `lines1.pl` | Líneas espectrales (transiciones) | Una petición con los 18 espectros juntos |
| `02_descarga_niveles_energia.ipynb` | `energy1.pl` | Niveles de energía | 18 peticiones, una por espectro, luego consolidadas |

Son dos fuentes **complementarias, no independientes**: cada línea espectral es en realidad
un salto de un electrón entre dos niveles de energía (uno inferior, uno superior). El
archivo de líneas ya trae *columnas embebidas* con información parcial de esos niveles
(configuración, término, energía), pero el archivo de niveles trae información adicional
que no está en el de líneas (incertidumbre del nivel, factor de Landé-g, leading
percentages, IDs internos de nivel).

---

## 4. Decisión de arquitectura: ¿un solo notebook y una sola tabla unificada?

### 4.1. Un único notebook: **Sí**

Tal como se pidió, todo el trabajo de esta etapa —descarga + exploración + diagnóstico +
limpieza— se hará en **un único archivo `.ipynb`**, no en notebooks separados. Esto es
razonable porque:

- Ambas fuentes alimentan la misma pregunta científica y se necesitan juntas para
  responderla.
- Mantener todo en un solo notebook permite que el flujo `request → DataFrame → limpieza`
  quede documentado de principio a fin, sin depender de que otro notebook se haya
  ejecutado antes.
- Facilita la reproducibilidad exigida por la rúbrica: alguien más puede abrir un solo
  archivo y correrlo de arriba a abajo.

### 4.2. ¿Una sola tabla unificada (merge) o mantener dos tablas separadas?

**Recomendación: mantener los dos DataFrames originales separados (`df_lines` y
`df_levels`) y construir un tercer DataFrame de análisis (`df_analysis`) que sea el
resultado de unirlos**, sin descartar los dos originales. Razones:

- **Para el análisis exploratorio y las visualizaciones de esta etapa**, tener una sola
  tabla ancha (`df_analysis`) es mucho más práctico: permite hacer histogramas, boxplots y
  correlaciones cruzando propiedades de la línea (Aki, longitud de onda) con propiedades
  del nivel (incertidumbre, Landé-g) sin tener que ir saltando entre dos DataFrames.
- **Para el diseño del modelo relacional (etapa 5, más adelante en el proyecto)**, esa
  unión NO debe ser la estructura final de la base de datos. Unir todo en una sola tabla
  ancha generaría redundancia (cada línea repetiría los datos completos de sus dos
  niveles), que es justamente lo que la rúbrica penaliza si "se importa el CSV como una
  única tabla". El modelo relacional seguirá construyéndose con tablas separadas
  (`elemento`, `espectro`, `nivel_energia`, `linea`) y claves foráneas.
- Es decir: **unir para explorar, separar para modelar**. El `df_analysis` es una
  herramienta de diagnóstico de esta etapa, no el producto final de la base de datos.

**Importante sobre la clave de unión (join key):** el archivo de líneas normalmente
identifica los niveles inferior y superior por su configuración, término y energía (y a
veces por un identificador de nivel), mientras que el archivo de niveles tiene su propio
identificador por espectro. **La columna o combinación de columnas exactas que sirven para
hacer el `merge` no se puede asumir de antemano** — se debe inspeccionar la estructura real
de ambos DataFrames una vez descargados (con `.columns`, `.head()`, `.dtypes`) y decidir en
ese momento si la unión se hace por energía + espectro, por configuración + término +
espectro, o por un ID de nivel si existe en ambos conjuntos. Esta decisión se toma **en
vivo**, dentro del notebook, no en este documento.

---

## 5. Estructura propuesta del notebook único

El notebook se llamará algo como `03_EDA_y_limpieza_optica_fotonica.ipynb` y seguirá este
orden de secciones:

### Sección 0 — Encabezado y documentación
Markdown con fuente, fecha, pregunta científica y objetivo de la etapa (igual que en los
notebooks de descarga).

### Sección 1 — Instalación e importación de librerías
```python
!pip install pandas numpy matplotlib seaborn requests

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import requests
from io import StringIO
```
`seaborn` se agrega porque permite construir mejores gráficos de distribución
(`histplot`, `boxplot`, `kdeplot`, `heatmap` de nulos) con menos código, tal como se ve en
los notebooks de ejemplo revisados.

### Sección 2 — Obtención de datos (reutilizando lo ya construido)
Se copian dentro de este mismo notebook las celdas de petición HTTP que ya se armaron en
los dos notebooks de descarga:
- Petición a `lines1.pl` con los 18 espectros → `df_lines`
- Loop de 18 peticiones a `energy1.pl` → consolidación → `df_levels`

Se guardan también los archivos originales en `datos_originales/` sin modificarlos, igual
que antes, para no perder la evidencia de la fuente.

### Sección 3 — Primera inspección de cada DataFrame (por separado)
Antes de unir nada, se revisa cada fuente de manera independiente:
- `.shape` → cantidad de filas y columnas de cada una
- `.head()` / `.tail()` → primeras y últimas filas
- `.columns` → nombres exactos de columnas (necesarios para decidir la clave de unión)
- `.info()` → tipo de dato que pandas detectó por columna y conteo de no-nulos
- `.dtypes` → tipos de dato en detalle

### Sección 4 — Verificación de tipos de dato vs. contenido real
Un tipo de dato que pandas asigna automáticamente no siempre es el correcto. Se verifica
columna por columna si lo que pandas interpretó coincide con lo que realmente contiene:

- Columnas que deberían ser numéricas (longitud de onda, Aki, log(gf), energía) pero que
  pandas cargó como texto (`object`) — esto suele pasar cuando el NIST incluye símbolos
  como `?`, `*`, paréntesis de incertidumbre, o celdas vacías representadas con guiones.
- Se usa `pd.to_numeric(columna, errors='coerce')` para forzar la conversión y ver cuántos
  valores "se pierden" (se vuelven `NaN`) en el intento — eso indica cuántos registros
  tienen texto no numérico en una columna que debería ser numérica.
- Columnas categóricas (elemento, tipo de transición, término espectroscópico) se
  inspeccionan con `.unique()` para detectar variantes de escritura, códigos no
  documentados o valores inesperados.

**No se asume de antemano qué columnas van a tener este problema** — se ejecuta esta
verificación sobre las columnas reales que traiga la descarga y se documentan los
hallazgos según lo que aparezca.

### Sección 5 — Análisis de valores faltantes
- `df.isnull().sum()` y `df.isnull().mean() * 100` para cantidad y porcentaje de nulos por
  columna, en cada una de las dos fuentes.
- Tabla resumen combinando ambas métricas (siguiendo el patrón de
  `pd.concat([total, porcentaje], axis=1)` visto en el notebook de referencia).
- Visualización con `sns.heatmap(df.isnull(), cbar=False)` para ver de un vistazo en qué
  filas/columnas se concentran los nulos.
- Con esos resultados (una vez calculados, no antes) se decide qué columnas tienen tantos
  nulos que deberían descartarse, y cuáles son candidatas a imputación.

### Sección 6 — Estadística descriptiva
- `df.describe()` para columnas numéricas (mínimo, máximo, media, cuartiles, desviación
  estándar).
- `df.describe(include='object')` para columnas categóricas (conteo, valores únicos, moda).
- Aquí es donde se detectan valores estadísticamente sospechosos: por ejemplo, un máximo
  muy alejado del percentil 75, tal como en el ejemplo de `User_Count` del notebook de
  referencia, que ya sugiere presencia de outliers antes incluso de graficar nada.

### Sección 7 — Detección de inconsistencias y duplicados
- `df.duplicated().sum()` para filas completamente repetidas.
- Verificación de valores físicamente imposibles: longitudes de onda negativas o iguales a
  cero, Aki negativo, energía de nivel superior menor que la del nivel inferior (lo cual
  violaría la física de la transición). Estas reglas de validación no se inventan a priori
  con números concretos: se calculan los rangos reales de cada columna y se comparan
  contra lo que es físicamente posible para decidir si hay o no violaciones.
- Revisión de inconsistencias de formato en columnas de texto: mismos elementos escritos de
  forma distinta, espacios extra, mayúsculas/minúsculas inconsistentes en `spectrum` o en el
  nombre del elemento.

### Sección 8 — Distribuciones de las variables (herramientas gráficas)
Para cada variable numérica relevante (longitud de onda, Aki, log(gf), energía de niveles):
- Histograma (`df[col].hist()` o `sns.histplot`) para ver la forma de la distribución
  (simétrica, sesgada, bimodal).
- Como Aki y algunas intensidades suelen variar en varios órdenes de magnitud, se evalúa
  también graficar su histograma en **escala logarítmica** (`plt.xscale('log')`), ya que en
  escala lineal estas variables suelen verse como una sola barra pegada al cero y el
  histograma no es informativo.
- Diagrama de cajas y bigotes (`plt.boxplot` o `sns.boxplot`) por variable, y también
  agrupado por elemento (`sns.boxplot(x='espectro', y='Aki', data=df)`) para comparar
  visualmente cómo cambia cada variable entre los 10 elementos.
- Gráfico de dispersión (`sns.scatterplot`) de longitud de onda vs. Aki, coloreado por
  elemento, que es la visualización que más directamente conecta con la pregunta
  científica planteada.
- **Nota sobre series temporales:** los datos del NIST ASD no tienen una componente
  temporal real (no son mediciones repetidas en el tiempo, son propiedades atómicas
  fijas), por lo que no aplica construir una serie temporal clásica. Esto se documentará
  explícitamente en el notebook como una aclaración, en lugar de forzar un gráfico que no
  tiene sentido físico para este conjunto de datos.

### Sección 9 — Rango de las variables y outliers
- Cálculo de rango (`max - min`) por variable numérica.
- Detección de outliers con el método de rango intercuartílico (IQR), igual que en el
  notebook de limpieza de referencia:
  ```python
  q1 = df[col].quantile(0.25)
  q3 = df[col].quantile(0.75)
  iqr = q3 - q1
  limite_inferior = q1 - 1.5 * iqr
  limite_superior = q3 + 1.5 * iqr
  outliers = df[(df[col] < limite_inferior) | (df[col] > limite_superior)]
  ```
- Para los datos de física atómica, un "outlier" estadístico no siempre implica un error:
  puede ser una transición real pero poco común (por ejemplo, una línea muy débil o muy
  energética). Por eso cada outlier detectado se revisa antes de decidir si se trata como
  dato erróneo o como una observación física válida y simplemente rara.

### Sección 10 — Relaciones entre variables
- Matriz de correlación (`df[columnas_numericas].corr()`) y su versión visual con
  `sns.heatmap(matriz_correlacion, annot=True, cmap='coolwarm')`.
- Cruces categóricos relevantes: por ejemplo, conteo de líneas por elemento y por tipo de
  transición (permitida vs. prohibida) usando `pd.crosstab()` o `sns.countplot(hue=...)`,
  siguiendo el mismo patrón usado en el notebook de referencia para cruzar clase y
  supervivencia en el Titanic.

### Sección 11 — Unión de las dos fuentes en una tabla de análisis
- Inspección final de las columnas candidatas a clave de unión en ambos DataFrames.
- Construcción de `df_analysis = pd.merge(df_lines, df_levels, on=..., how='left')`,
  documentando explícitamente qué columnas se usaron como llave y por qué, según lo que se
  haya encontrado en la Sección 3.
- Verificación de integridad del merge: cuántas filas de `df_lines` no encontraron
  coincidencia en `df_levels` (`indicator=True` en el merge para contar `left_only`), ya
  que esto es en sí mismo un hallazgo de calidad de datos.
- Repetición rápida de histogramas/boxplots clave sobre `df_analysis` para confirmar que la
  unión no introdujo distorsiones (por ejemplo, duplicación de filas si la clave no era
  única).

### Sección 12 — Diagnóstico consolidado (resultado de esta etapa)
Un bloque final en Markdown, redactado **después de ejecutar todo lo anterior y con base en
los resultados reales obtenidos**, que resuma en lenguaje claro:
- Cantidad final de filas y columnas de cada fuente y del `df_analysis`.
- Lista de columnas con problemas de tipo de dato y cómo se corrigieron.
- Lista de columnas con valores faltantes relevantes y qué estrategia de imputación se
  eligió para cada una (ver Sección 6 de este documento, más abajo).
- Lista de inconsistencias encontradas (duplicados, valores imposibles, categorías mal
  escritas) y cómo se resolvieron.
- Outliers identificados y la decisión tomada sobre cada uno (conservar como dato físico
  válido, corregir, o eliminar).
- Este bloque es equivalente al apartado *"Resultados del análisis exploratorio"* del
  notebook de referencia de limpieza, adaptado a los datos reales de física atómica.

---

## 6. Metodología de limpieza a aplicar (explicada, para ejecutar en vivo)

Esta sección documenta **el criterio** que se usará para limpiar, no los resultados
concretos (esos solo se conocen al correr el notebook con datos reales). Se basa en las
mismas técnicas usadas en el notebook de limpieza de referencia (`Video Game Sales`):

### 6.1. Valores nulos
| Situación | Estrategia |
|---|---|
| Columna con nulos y variable numérica de distribución aproximadamente simétrica | Imputar con la **media** |
| Columna con nulos y variable numérica con distribución sesgada (cola larga, como suele pasar con Aki o intensidades) | Imputar con la **mediana**, porque no se ve afectada por valores extremos |
| Columna categórica con nulos | Imputar con la **moda**, o con una categoría explícita tipo `"Desconocido"` si la moda no tiene sentido físico |
| Columna con porcentaje de nulos muy alto (a definir según lo que se observe, no un número fijo de antemano) | Evaluar **eliminar la columna completa** si no aporta a la pregunta científica |
| Fila sin dato en una columna clave para identificar el registro (por ejemplo, sin espectro/elemento) | Evaluar **eliminar la fila**, ya que no se puede usar sin saber a qué elemento pertenece |

La decisión entre media/mediana **no se toma a priori**: se decide observando el
histograma real de cada columna (Sección 8), exactamente como en el notebook de
referencia, donde una distribución sesgada hacia la derecha llevó a preferir la mediana
sobre la media.

### 6.2. Corrección de tipos de dato
- Conversión de columnas numéricas mal tipadas usando `pd.to_numeric(col, errors='coerce')`
  y luego decidiendo qué hacer con los valores que no pudieron convertirse (revisar caso
  por caso qué texto contenían antes de descartarlos).
- Conversión de columnas de conteo o clasificación a tipos más eficientes (`int64` en vez de
  `float64`) una vez que ya no tengan nulos, igual que se hizo con `Critic_Count` y
  `User_Count` en el notebook de referencia.
- Normalización de texto en columnas categóricas: quitar espacios extra (`.str.strip()`),
  unificar mayúsculas/minúsculas si aplica, y unificar variantes de escritura del mismo
  valor (por ejemplo, si el mismo tipo de transición aparece escrito de más de una forma).

### 6.3. Tratamiento de outliers
- Se usa el método de rango intercuartílico (IQR) descrito en la Sección 9, replicando el
  procedimiento del notebook de referencia (`User_Count`), pero **adaptando la decisión
  final al contexto físico**: en el dataset del Titanic un outlier de tarifa puede ser un
  error o un caso genuino de un pasajero rico; en física atómica, un outlier puede ser una
  transición real pero rara, así que antes de "convertirlo en nulo" automáticamente se
  revisa si tiene sentido físico conservarlo.
- Cuando se decida sí tratar un valor como outlier erróneo, se reemplaza por `NaN` y luego
  sigue el mismo flujo de imputación de la Sección 6.1, nunca se elimina la fila completa
  sin antes evaluar qué otras columnas de esa fila siguen siendo útiles.

### 6.4. Duplicados
- Eliminación de filas exactamente duplicadas con `df.drop_duplicates()`, documentando
  cuántas filas se eliminaron.

### 6.5. Trazabilidad de la limpieza
- Siguiendo el patrón del notebook de referencia (`df_toclean`, `df_aux`, `df_fix`), se
  trabajará siempre sobre una **copia** del DataFrame original (`df.copy()`), nunca sobre
  `df_lines` o `df_levels` originales directamente, de manera que en cualquier momento se
  pueda comparar el antes y el después.
- Cada paso de limpieza queda documentado en una celda Markdown inmediatamente antes o
  después del código, explicando qué problema se detectó y por qué se eligió esa solución
  (igual que en ambos notebooks de referencia), en vez de aplicar transformaciones sin
  justificación.
- Al final, el DataFrame limpio se exporta a `datos_procesados/` (nunca sobrescribiendo la
  carpeta `datos_originales/`), dejando dos archivos: uno para líneas limpias y uno para
  niveles limpios, además de (opcionalmente) el `df_analysis` limpio ya unido, que servirá
  de insumo para el diseño del modelo relacional en la siguiente etapa del proyecto.

---

## 7. Regla general para todo el proceso

**Nada de lo anterior se ejecuta ni se concluye sobre datos hipotéticos.** Este documento
define el método y el orden de trabajo; los números concretos (cuántos nulos hay, qué
columnas tienen problemas de tipo, qué outliers aparecen, qué estrategia de imputación
gana en cada columna) solo se determinan **en el momento en que el notebook se ejecuta
contra los datos reales descargados del NIST**. Cualquier hallazgo mencionado como ejemplo
en este plan (por ejemplo, "Aki puede tener notación científica" o "el término
espectroscópico puede tener variantes de escritura") es una hipótesis de trabajo a
verificar, no un hecho asumido de antemano.

---

## 8. Entregable de esta etapa

Al finalizar el notebook único se debe tener:
- `datos_originales/` — archivos CSV crudos, sin modificar (ya generados por los notebooks
  de descarga).
- `datos_procesados/` — versión limpia de `df_lines`, `df_levels` y `df_analysis`.
- El notebook `03_EDA_y_limpieza_optica_fotonica.ipynb` con todo el proceso de descarga,
  exploración, diagnóstico y limpieza documentado paso a paso.
- El bloque de diagnóstico consolidado (Sección 12) como insumo directo para arrancar la
  siguiente etapa del proyecto: el diseño del modelo relacional.

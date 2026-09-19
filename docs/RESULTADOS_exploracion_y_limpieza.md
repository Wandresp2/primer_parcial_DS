# Resultados de la exploración y la limpieza de los datos
## Proyecto: Óptica y Fotónica — Primer Parcial
### Fuente: NIST Atomic Spectra Database

**Estudiante:** Perez Criollo Andres David
**Notebooks:** `03_exploracion_caracterizacion_datos.ipynb` (exploración) y `04_limpieza_datos.ipynb` (limpieza)
**Datos originales:** `notebooks/datos_originales/` — nunca modificados
**Datos procesados:** `notebooks/datos_procesados/`

> Este documento está escrito para que pueda entenderse **sin formación previa en física**.
> Las cifras que aparecen salen todas de la ejecución real de los dos notebooks.

---

## 1. Qué son estos datos

Cuando un elemento químico se calienta, emite luz **en colores muy específicos**, como un
código de barras propio. El hidrógeno emite unos colores concretos y el neón otros — por eso
los letreros de neón son rojizos. Ese patrón es único de cada elemento, y es la razón por la
que se puede saber de qué está hecha una estrella a millones de años luz sin ir hasta ella.

Del NIST, el organismo de metrología de Estados Unidos, se descargaron **dos catálogos
complementarios** de los diez primeros elementos de la tabla periódica (del hidrógeno al
neón), en dos estados: el átomo neutro y el átomo al que le falta un electrón.

| Catálogo | Qué es cada fila | Registros |
|---|---|---|
| **Líneas espectrales** | Un color concreto que un elemento puede emitir | 18 288 |
| **Niveles de energía** | Un "escalón" de energía interno del átomo | 5 752 |

**Cómo se relacionan:** cada color emitido es un electrón que salta de un escalón a otro. La
energía que pierde en el salto se convierte en luz, y el color depende del tamaño del salto.
Así que los dos catálogos describen el mismo fenómeno desde dos ángulos: uno lista los saltos,
el otro lista los escalones.

### Las tres variables que importan

| Variable | Qué significa |
|---|---|
| **Longitud de onda** | Qué color exactamente. Se mide en nanómetros. Valores bajos = ultravioleta (invisible), 380–780 = luz visible, valores altos = infrarrojo |
| **Aki** (coeficiente de Einstein) | **Con qué facilidad** el átomo emite ese color. Un valor alto significa que la emisión ocurre casi instantáneamente; uno bajo, que el átomo puede tardar muchísimo |
| **Elemento / espectro** | De qué átomo se trata, y si está neutro o ionizado |

### La pregunta que orienta todo el proyecto

> **¿Cómo se distribuyen las líneas espectrales de los diez primeros elementos a lo largo del
> espectro electromagnético, y qué relación existe entre `Aki` y la longitud de onda en cada
> elemento?**

En lenguaje llano: *¿en qué colores emiten estos átomos, y los colores que emiten con más
facilidad son los mismos en todos los elementos?*

---

## 2. Qué encontró la exploración

### La sorpresa: los datos no están sucios, están mal empaquetados

Lo habitual al recibir datos reales es encontrarlos llenos de errores. Aquí ocurrió lo
contrario. Se aplicaron cinco pruebas que cualquier dato erróneo habría fallado:

| Prueba | Qué detectaría | Resultado |
|---|---|---|
| Longitud de onda negativa o cero | Un color imposible | **0 casos** |
| `Aki` negativo | Una probabilidad negativa | **0 casos** |
| Escalón superior más bajo que el inferior | Un salto al revés | **0 casos** |
| Energía negativa | Imposible por definición | **0 casos** |
| Filas exactamente repetidas | Error de captura | **0 casos** |

Además, existe una regla matemática interna del átomo (`g = 2J + 1`) que relaciona dos de
las columnas. **Se cumple en el 100 % de los 5 570 registros donde puede comprobarse.**

Los problemas eran de otra naturaleza, y los cuatro pasaban desapercibidos.

### Problema 1 — Todo venía envuelto en "papel de regalo"

El NIST exporta cada valor con un envoltorio técnico para que Excel no lo malinterprete: en
vez de `91.23`, el archivo trae `="91.23"`.

Eso tiene dos efectos, y el segundo es grave:

1. Python lee todo como **texto**, no como números. No se podía calcular ni un promedio.
2. Un dato **ausente** llegaba como envoltorio vacío (`=""`), que es un texto perfectamente
   válido. Así que el programa reportaba **23 640 ausencias cuando en realidad había
   122 295**.

Es decir: el dataset *parecía* casi completo y no lo era. **80 697 ausencias estaban
escondidas** detrás del envoltorio.

### Problema 2 — Dos reglas de medida mezcladas en la misma columna

Este es el más serio y el más silencioso.

La longitud de onda puede medirse **en el vacío** o **en el aire**, y los dos valores no son
iguales porque el aire desvía ligeramente la luz. El NIST alterna entre las dos convenciones
según el rango, y lo avisa insertando una cabecera nueva en mitad del archivo… que quedó
mezclada con los datos.

Resultado: la respuesta venía en **tres bloques**, y el del medio usa una convención distinta:

| Bloque | Filas | Medida en |
|---|---|---|
| 1 | 3 689 | vacío |
| 2 | **10 428** | **aire** |
| 3 | 4 171 | vacío |

Las 10 428 mediciones en aire terminaron bajo una columna llamada `obs_wl_vac(nm)`, es decir,
**etiquetada como vacío**. No produce ningún error ni ninguna alarma: produce una columna que
*parece* homogénea y no lo es. Es exactamente el tipo de defecto que no se nota hasta que
arruina una conclusión.

Y de paso, las 2 cabeceras intermedias quedaron dentro de los datos como si fueran dos líneas
espectrales más.

### Problema 3 — El NIST escribe con su propia taquigrafía

Unos 28 020 valores no se podían convertir a número porque contienen anotaciones con
significado:

| Lo que trae el archivo | Qué significa |
|---|---|
| `[186101.55]` | La energía fue **calculada**, no medida en laboratorio |
| `934593.0+x` | La energía se conoce, pero **medida desde un punto de partida desconocido** |
| `74.4794+` | El valor es un **límite**, no una medida exacta |
| `500*`, `a*` | La línea tiene alguna particularidad (es difusa, está mezclada con otra…) |
| `3/2` | Un número cuántico escrito como **fracción** — es simplemente 1,5 |

Aplicar la conversión automática de Python habría convertido los 28 020 en huecos vacíos.
Pero el número está ahí: lo que el símbolo aporta es *cómo se obtuvo*, no lo anula.

### Problema 4 — Los datos faltantes no son aleatorios

`Aki` falta en el 31 % de las líneas, pero **no se reparte por igual entre elementos**:

| Peor documentados | Tienen `Aki` | Mejor documentados | Tienen `Aki` |
|---|---|---|---|
| Ne II | **12,2 %** | He I | **99,5 %** |
| Be II | 21,9 % | N I | 98,3 % |
| Ne I | 33,4 % | N II | 97,2 % |

Esto no es ruido: significa que unos elementos están **mucho mejor estudiados
experimentalmente** que otros. Es un hallazgo en sí mismo, y condiciona qué comparaciones son
legítimas.

### Un problema adicional: los notebooks de descarga no funcionaban

Durante la exploración se descubrió que los dos notebooks originales de descarga usaban
**nombres de parámetro que el NIST no reconoce**. La web respondía con una página de error de
3 KB que se estaba guardando como si fueran los datos científicos. Se corrigieron leyendo los
nombres reales de los formularios oficiales del NIST.

---

## 3. Qué se puede responder de la pregunta científica

### Primera mitad: cómo se distribuyen los colores

**Respondible por completo.** Tras la limpieza, el **100 %** de las líneas tiene longitud de
onda asignada, y se pueden clasificar todas:

| Región del espectro | Líneas | % |
|---|---|---|
| Rayos X | 113 | 0,62 % |
| **Ultravioleta** | **6 347** | **34,71 %** |
| Visible | 3 823 | 20,90 % |
| **Infrarrojo** | **7 926** | **43,34 %** |
| Microondas / Radio | 79 | 0,43 % |
| **Sin clasificar** | **0** | **0 %** |

Antes de la limpieza, el 46 % de las líneas quedaba sin clasificar por falta de longitud de
onda. Ahora no queda ninguna.

Un resultado que ya se puede leer aquí: **la mayor parte de lo que emiten estos átomos es
invisible para el ojo humano.** Solo una de cada cinco líneas cae en el rango visible; el
78 % está en el infrarrojo o el ultravioleta.

### Segunda mitad: la relación entre `Aki` y el color

**Respondible, y ya hay un adelanto del resultado.**

Si se comparan las dos variables tal cual vienen, la correlación es **−0,0023**:
prácticamente cero. Parecería que no existe ninguna relación.

Pero `Aki` abarca **35 órdenes de magnitud** — desde 0,000…0004 hasta 700 000 000 000. En una
escala así, casi todos los valores se apelotonan contra el cero y cualquier medida estadística
queda dominada por un puñado de extremos.

Al pasar ambas variables a **escala logarítmica**, la relación aparece:

| Cómo se mide | Correlación | Sobre cuántas líneas |
|---|---|---|
| Valores tal cual | **−0,0023** | 4 462 |
| Escala logarítmica (muestra inicial) | **−0,6805** | 4 462 |
| Escala logarítmica (**muestra completa tras la limpieza**) | **−0,6080** | **12 603** |

En lenguaje llano: **cuanto más larga es la onda, menos probable es que el átomo emita esa
luz.** La relación estaba ahí todo el tiempo; solo era invisible sin el cambio de escala.

> **Nota honesta sobre la última fila:** al incorporar las 8 141 líneas que recuperó la
> limpieza, la correlación bajó de −0,68 a −0,61. No es un empeoramiento: es una cifra
> **más representativa**, calculada sobre casi el triple de evidencia. La muestra inicial,
> limitada a las líneas con medición directa, estaba sesgada hacia las mejor estudiadas.

### La salvedad importante

La pregunta dice *"en cada elemento"*, y ahí hay un límite que no depende del método: con
Ne II solo se tiene el 12,2 % de los datos y con He I el 99,5 %. **Se pueden comparar
elementos, pero hay que decir explícitamente que algunos están mejor documentados que otros**,
y que las diferencias observadas pueden reflejar el estado del conocimiento científico tanto
como la física del átomo.

Lejos de ser una debilidad del trabajo, esto es un resultado que conviene reportar.

---

## 4. Qué se hizo en la limpieza y por qué

Se aplicaron **14 decisiones**, cada una justificada desde dos ángulos: computacional (qué
problema técnico resuelve) y físico (por qué tiene sentido para el fenómeno).

El principio que gobierna todas: **en un dataset científico, un valor ausente es información.**
Que el NIST no haya medido el `Aki` de una línea es un hecho sobre el estado del conocimiento,
no un hueco que haya que tapar.

| # | Qué se hizo | Por qué |
|---|---|---|
| **L1** | Eliminar las 2 cabeceras incrustadas | No son observaciones, son metadatos del formato. **Único paso que elimina filas** |
| **L2** | Reconstruir si cada línea se midió en aire o en vacío, y añadir una columna homogénea | Una columna que mezcla dos definiciones **no es una variable**. Se dedujo del bloque del archivo en que estaba cada fila |
| **L3** | Quitar el envoltorio `="..."` | Sin esto los datos son texto y las ausencias invisibles. **No es limpiar: es desenvolver** |
| **L4** | Interpretar la taquigrafía del NIST en vez de descartarla | `[186101.55]` **sí contiene la energía**. Se extrae el número y se guarda el matiz en una columna aparte |
| **L5** | Convertir `3/2` en 1,5 | Un `to_numeric` habría anulado el 46 % de la columna. Se verificó con la regla `g = 2J+1`, que da **100 %** |
| **L6** | Proteger los identificadores como texto | `006002.000001` convertido a número se vuelve `6002.000001` y **pierde los ceros**, rompiendo la unión entre catálogos |
| **L7** | Rellenar el tipo de transición vacío con `E1` | Vacío no significa "falta": por convención del NIST significa "transición permitida". Se documenta en el dato en vez de esconderlo |
| **L8** | Usar la longitud de onda calculada cuando falta la medida | **La decisión de mayor impacto.** Ver abajo |
| **L9** | **No imputar** `Aki` | Es la variable que la pregunta quiere explicar: imputarla sería inventar la respuesta |
| **L10** | Crear `log10_aki`, región espectral y energía del fotón | Sin la escala logarítmica la relación buscada es invisible |
| **L11** | Descartar 4 columnas | Todas secundarias y con más del 69 % de ausencias |
| **L12** | Marcar los duplicados, no borrarlos | Las 70 repeticiones son **mediciones independientes de distintos laboratorios**, no basura |
| **L13** | **Conservar** los 2 181 valores atípicos | Ver abajo |
| **L14** | Unir los dos catálogos por identificador de nivel | Cada línea es un salto entre **dos** escalones, así que se une dos veces |

### Las dos decisiones que más conviene poder explicar

**L8 — Recuperar la longitud de onda con el valor calculado**

La longitud de onda *medida en laboratorio* falta en el 46 % de las líneas. Pero el catálogo
trae una segunda columna: la longitud de onda **calculada a partir de la diferencia entre los
dos escalones de energía**. No es una estimación estadística: es física exacta. Y está
disponible en el 97,8 % de las filas.

El efecto de usarla como respaldo:

| Base de evidencia | Líneas | % |
|---|---|---|
| Solo con longitud de onda medida **y** `Aki` | 4 462 | 24,4 % |
| Con longitud de onda medida **o calculada** y `Aki` | **12 603** | **68,9 %** |
| Con alguna longitud de onda | **18 288** | **100 %** |

**Se casi triplica la evidencia disponible sin inventar un solo dato.** Cada fila conserva una
columna que dice si su longitud de onda es medida o calculada, así que cualquier análisis
posterior puede restringirse a las medidas si lo necesita.

**L13 — Conservar los valores atípicos**

El método estadístico estándar marca **2 181 valores de `Aki` como anómalos** y sugeriría
eliminarlos. No se eliminó ninguno, y la razón es física:

| Tipo de transición | Cuántas | `Aki` típico (escala log) |
|---|---|---|
| **Permitida** (la normal) | 12 342 | **+5,69** |
| Prohibida (E2) | 152 | −0,93 |
| Prohibida (M2) | 17 | −1,41 |
| Prohibida (M1) | 92 | **−3,31** |

Las llamadas *transiciones prohibidas* son emisiones reales pero muchísimo más lentas —
**unos nueve órdenes de magnitud** por debajo de las normales. El método estadístico las marca
porque son minoría (1,8 % de las líneas), no porque sean erróneas.

Eliminarlas habría borrado **una categoría entera de fenómeno físico** por hacerle caso ciego
a una fórmula.

---

## 5. Cómo quedaron los datos

### Antes y después

| Métrica | Antes | Después |
|---|---|---|
| Filas de líneas | 18 290 | **18 288** (−2 cabeceras) |
| Filas de niveles | 5 752 | **5 752** (ninguna eliminada) |
| Columnas numéricas utilizables | **0** (todo era texto) | **28** |
| Ausencias visibles | 23 640 | **122 295** (ya no están escondidas) |
| Líneas útiles para la pregunta | 4 462 | **12 603** |
| Líneas con región espectral asignada | 9 862 (53,9 %) | **18 288 (100 %)** |
| Correlación longitud de onda ↔ `Aki` | −0,0023 | **−0,6080** |
| Valores físicamente imposibles | 0 | 0 |
| **Filas eliminadas** | — | **2** |
| **Valores imputados** | — | **0** |

### Los archivos generados

| Archivo | Filas | Columnas | Para qué sirve |
|---|---|---|---|
| `dataset_limpio.csv` | 18 288 | 65 | **Entregable principal**: cada línea con sus dos niveles ya unidos |
| `lineas_limpias.csv` | 18 288 | 47 | Alimentará la tabla de líneas de la base de datos |
| `niveles_limpios.csv` | 5 752 | 14 | Alimentará la tabla de niveles |
| `diccionario_columnas.csv` | 58 | 5 | Qué significa cada columna, su unidad y su nombre original en el NIST |

**Por qué tres archivos de datos y no uno solo:** 2 201 niveles (el **38,3 %** del catálogo) no
participan en ninguna línea documentada. Si se guardara únicamente la tabla unida, se
perderían — y son precisamente los que la base de datos necesita para tener el catálogo
completo de escalones de energía.

Los nombres de las columnas se cambiaron a un formato limpio (`aki_s1` en vez de `Aki(s^-1)`)
porque los originales tienen paréntesis y símbolos que complican las consultas SQL. El
diccionario guarda la correspondencia con el nombre original, así que la trazabilidad con la
fuente oficial no se pierde.

### Garantías de calidad verificadas automáticamente

El notebook de limpieza se detiene si alguna de estas ocho comprobaciones falla. Las ocho
pasan:

1. Los cuartiles de las variables críticas siguen siendo distintos entre sí — es decir, **la
   limpieza no aplanó ninguna distribución**.
2. Cero valores físicamente imposibles.
3. La regla `g = 2J + 1` se sigue cumpliendo al 100 %.
4. Se conservan exactamente 18 288 líneas.
5. La unión de los dos catálogos no duplicó ni una fila.
6. La base de evidencia llega a 12 603 líneas.
7. La correlación sigue en el rango esperado.
8. Los identificadores conservan sus ceros a la izquierda (100 %).

Y los 20 archivos originales se comprobaron con firma digital **antes y después**: son
idénticos. No se tocó ninguno.

---

## 6. En una frase

El dataset es de **excelente calidad física** pero venía en un formato que lo disfrazaba. Por
eso la limpieza es deliberadamente conservadora: **descarta 4 columnas, elimina 2 filas y no
inventa ni un solo dato**. La ganancia no vino de rellenar huecos, sino de **decodificar bien
e interpretar la notación del NIST** — eso por sí solo llevó la evidencia utilizable de 4 462
a 12 603 líneas y destapó 80 697 ausencias que estaban ocultas.

**Con estos datos, la pregunta científica es respondible.**

---

## 7. Qué sigue

El siguiente paso es llevar estos datos a una base de datos relacional. La propuesta completa
—qué tablas crear, cómo se relacionan y por qué— está en
**`docs/PROPUESTA_modelo_relacional.md`**.

La verificación de la sección 18 del notebook 04 ya confirmó que los datos limpios soportan
ese modelo: las claves primarias son únicas, **no hay ni una sola clave foránea huérfana**, y
el espectro de cada línea coincide con el de sus niveles en el 100 % de los 18 073 casos
comprobables.

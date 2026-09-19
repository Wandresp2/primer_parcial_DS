# Plan de limpieza de datos — NIST Atomic Spectra Database
## Proyecto: Óptica y Fotónica — Primer Parcial
### Desarrollo de Software

**Estudiante:** Perez Criollo Andres David
**Documento base:** `docs/PLAN_analisis_exploratorio_limpieza.md`
**Evidencia:** `notebooks/03_exploracion_caracterizacion_datos.ipynb` (ejecutado)
**Datos originales:** `notebooks/datos_originales/`

---

## 1. Contexto y alcance

Este documento **propone y justifica** la limpieza de los datos descargados del NIST ASD.
No la ejecuta: la ejecución corresponde a la etapa siguiente del proyecto.

Todas las cifras que aparecen aquí provienen de la ejecución real del notebook de
exploración, en cumplimiento de la regla fijada en la sección 7 del plan original: *nada se
concluye sobre datos hipotéticos*. Cada decisión de este plan puede rastrearse hasta una
celda concreta del notebook.

**Volumen sobre el que se trabaja:**

| Conjunto | Filas | Columnas | % de celdas vacías |
|---|---|---|---|
| Líneas espectrales | 18 290 | 27 | 18,26 % |
| Niveles de energía | 5 752 | 13 | 30,78 % |
| `df_analysis` (unión) | 18 290 | 46 | 23,40 % |

---

## 2. Criterio rector: la pregunta científica manda

> **¿Cómo se distribuyen las líneas espectrales de H a Ne a lo largo del espectro
> electromagnético, y qué relación existe entre el coeficiente de Einstein Aki y la longitud
> de onda de emisión en cada elemento?**

Esta pregunta define una jerarquía que gobierna **todas** las decisiones siguientes:

| Nivel | Variables | Consecuencia para la limpieza |
|---|---|---|
| **Críticas** | longitud de onda, `Aki(s^-1)`, `element`/`espectro`, `Ei`/`Ek` | Nunca se imputan con un valor inventado. Se recuperan con respaldos físicamente válidos o se marcan como no disponibles. |
| **Auxiliares** | `Type`, `Acc`, `g_i`/`g_k`, `J_i`/`J_k`, `conf`/`term` | Se normalizan y se corrigen de tipo, porque explican y contextualizan a las críticas. |
| **Secundarias** | `unc_*`, `tp_ref`, `line_ref`, `Reference`, `Leading percentages`, `Prefix`/`Suffix`, `Lande` | Pueden descartarse si su tasa de nulos es alta; su ausencia no impide responder la pregunta. |

**Principio general adoptado:** *en un dataset científico, un valor ausente es información.*
Que el NIST no haya medido el `Aki` de una línea es un hecho sobre el estado del
conocimiento, no un hueco que haya que tapar. Por eso este plan **evita la imputación en las
variables críticas** y prefiere recuperar el dato desde otra columna físicamente equivalente,
o dejarlo explícitamente ausente. Imputar un `Aki` con la mediana produciría una línea
espectral que no existe.

---

## 3. Resultados del análisis exploratorio

Lista de problemas detectados, cada uno con su evidencia numérica.

### 3.1 Problemas de formato y estructura

| # | Hallazgo | Evidencia |
|---|---|---|
| **H1** | Todos los valores vienen envueltos en el artefacto de exportación `="valor"`, y los ausentes llegan como el texto `=""`, no como `NaN` | Sin decodificar, líneas aparentaba 23 640 nulos; la cifra real es **90 149** |
| **H2** | La respuesta contiene **3 bloques con cabeceras repetidas**, y el bloque central usa longitud de onda **en aire** mientras los otros dos la usan **en vacío** | Bloques de 3 689 (vacío), **10 428 (aire)** y 4 171 (vacío) filas |
| **H3** | 2 filas de cabecera quedaron incrustadas como datos | `element` tiene 11 valores únicos: los 10 elementos + el literal `"element"` |
| **H4** | La coma final de la cabecera hace que pandas invente una columna `Unnamed: 26` completamente vacía | Ya descartada en el parseo del notebook |

### 3.2 Problemas de tipo de dato

**17 columnas mal tipadas en líneas** y **5 en niveles**. Tras decodificar, 28 020 valores
en líneas y 2 454 en niveles siguen sin poder convertirse a número, por contener
**notación científica propia del NIST**:

| Símbolo | Significado en el NIST | Dónde aparece | Magnitud |
|---|---|---|---|
| `[valor]` | Energía **interpolada o teórica**, no medida | `Ei(cm-1)`, `Ek(cm-1)` | parte de 19,04 % y 21,90 % |
| `+x`, `+y` | Energía con un **origen desconocido** (ej. `934593.0+x`) | `Ei(cm-1)`, `Ek(cm-1)` | ídem |
| `+` final | Longitud de onda Ritz con límite superior (ej. `74.4794+`) | `ritz_wl_vac(nm)` | 216 valores (1,19 %) |
| `*`, `a`, `a*`, `3*` | Banderas de intensidad (línea difusa, mezclada, etc.) | `intens` | **3 769 valores (38,14 %)** |
| `3/2`, `1/2` | Números cuánticos como **fracción** | `J_i` (46,47 %), `J_k` (46,76 %), `J` niveles (43,02 %) | mayoritario |
| `0,1,2` | J **no resuelto**: varios valores posibles | `J_i`, `J_k`, `J` | decenas de casos |
| `---` | Nivel sin J determinado | `J` (niveles) | 52 casos |
| `(1.2004)` | Factor de Landé **estimado**, no medido | `Lande` | 96,55 % de los presentes |

**Caso especial — identificadores que parecen números:** `ID_i`, `ID_k` y `Level ID`
contienen códigos como `006002.000001`. Convertirlos a número los transforma en
`6002.000001`, **destruyendo los ceros a la izquierda**. Durante la exploración esto llegó a
degradar la tasa de unión entre fuentes; al protegerlos, subió a 98,81 %.

### 3.3 Valores faltantes

**Líneas espectrales** (sobre 18 290 filas):

| Columna | Faltantes | % | Lectura |
|---|---|---|---|
| `Type` | 17 955 | 98,17 % | **No es un faltante**: vacío = transición permitida (E1) |
| `unc_obs_wl` | 10 598 | 57,94 % | Secundaria |
| `obs_wl_vac(nm)` | 8 424 | 46,06 % | **Crítica** — pero tiene respaldo |
| `intens` | 8 409 | 45,98 % | Secundaria, escala arbitraria |
| `line_ref` | 8 003 | 43,76 % | Secundaria |
| `Aki(s^-1)`, `fik`, `log_gf`, `Acc`, `tp_ref` | 5 685 | 31,08 % | **Crítica** — faltan en bloque |
| `unc_ritz_wl` | 5 020 | 27,45 % | Secundaria |
| `J_k` / `J_i` / `term_*` | 433–501 | 2,4–2,7 % | Auxiliares |
| `conf_*`, `Ei`, `Ek`, `ID_*` | 215 | 1,18 % | Críticas, pero marginal |
| `ritz_wl_vac(nm)` | 182 | 1,00 % | **Crítica — la mejor cubierta (97,8 %)** |
| `element`, `sp_num`, `g_i`, `g_k` | 0 | 0 % | Completas |

**Niveles de energía** (sobre 5 752 filas):

| Columna | Faltantes | % |
|---|---|---|
| `Lande` | 5 723 | **99,50 %** |
| `Prefix` | 4 532 | 78,79 % |
| `Suffix` | 4 258 | 74,03 % |
| `Leading percentages` | 3 991 | 69,38 % |
| `Reference` | 2 241 | 38,96 % |
| `Uncertainty (eV)` | 2 063 | 35,87 % |
| `Level (eV)` | 63 | 1,10 % |
| `g` / `J` / `Term` | 41–52 | 0,7–0,9 % |
| `Configuration` | 1 | 0,02 % |
| `Level ID`, `espectro` | 0 | 0 % |

**Los faltantes no se reparten de forma homogénea** — este es el hallazgo que más condiciona
la estrategia de imputación. La cobertura de `Aki` por espectro:

| Peor cubiertos | % con Aki | Mejor cubiertos | % con Aki |
|---|---|---|---|
| Ne II | **12,2 %** | He I | **99,5 %** |
| Be II | 21,9 % | N I | 98,3 % |
| Ne I | 33,4 % | N II | 97,2 % |
| F II | 44,7 % | O I | 93,8 % |

Y en `Ei(cm-1)`, He I tiene **99,9 %** de faltantes mientras C I y Ne I tienen 0,0 %.

### 3.4 Duplicados e integridad

| Chequeo | Resultado |
|---|---|
| Filas exactamente duplicadas (líneas / niveles) | **0 / 0** |
| Transiciones con la misma identidad física repetida | 70 |
| Niveles con la misma identidad cuántica repetida | 16 |
| Claves `Level ID` duplicadas | **0** (clave única) |

### 3.5 Validación física — todo correcto

| Validación | Violaciones |
|---|---|
| Longitud de onda ≤ 0 | **0** |
| `Aki` ≤ 0 | **0** |
| `Ek ≤ Ei` (nivel superior no supera al inferior) | **0** |
| `Ei` < 0 | **0** |
| `g = 2J + 1` en niveles | **0 incumplimientos** sobre 5 570 evaluables (100 %) |

**No hay un solo valor físicamente imposible en todo el dataset.** Esto cambia por completo
el carácter de la limpieza: no se trata de corregir errores, sino de **hacer utilizable** un
dato que ya es correcto.

### 3.6 Valores atípicos

| Variable | Outliers (IQR) | % | Asimetría |
|---|---|---|---|
| `intens` | 1 200 | 19,63 % | 39,92 |
| `unc_ritz_wl` | 2 299 | 17,33 % | 115,11 |
| `Aki(s^-1)` | 2 181 | **17,31 %** | 40,16 |
| `fik` | 1 902 | 15,09 % | 87,94 |
| `ritz_wl_vac(nm)` | 2 267 | 12,67 % | 57,79 |
| `Ei(cm-1)` | 53 | 0,36 % | 1,27 |

`Aki` abarca **35,2 órdenes de magnitud** (de 4,24 × 10⁻²⁴ a 7,00 × 10¹¹ s⁻¹).

Y la explicación de esos atípicos es **física, no un error** — la mediana de log₁₀(Aki) por
tipo de transición:

| Tipo de transición | n | mediana log₁₀(Aki) |
|---|---|---|
| Permitida (E1) | 12 342 | **+5,69** |
| Prohibida (E2) | 152 | −0,93 |
| Prohibida (M2) | 17 | −1,41 |
| Prohibida (M1) | 92 | **−3,31** |

Las transiciones prohibidas viven **nueve órdenes de magnitud por debajo** de las permitidas.
El IQR las marca como atípicas porque son minoría (1,83 %), no porque sean erróneas.

### 3.7 La relación central de la pregunta científica

| Medida de correlación λ ↔ Aki | Valor |
|---|---|
| Pearson sobre valores crudos | **−0,0023** |
| Pearson sobre log₁₀ de ambas | **−0,6805** |
| Spearman | −0,5862 |

Sobre los valores crudos **no hay relación aparente**. En escala logarítmica aparece una
correlación negativa fuerte. Esto no es un detalle estadístico: determina que la
transformación logarítmica no es opcional.

### 3.8 Unión de las dos fuentes

| Métrica | Resultado |
|---|---|
| Estrategia adoptada | **A — identificador interno de nivel** (`ID_i`/`ID_k` ↔ `Level ID`) |
| Cobertura (estrategia A) | **98,81 %** |
| Cobertura alternativa (B: espectro+configuración+término+J) | 97,23 % |
| Líneas huérfanas | 217 (1,19 %) |
| Filas duplicadas por el merge | **+0** |

---

## 4. Plan de limpieza, problema por problema

### L1 — Eliminar las filas de cabecera incrustadas

**Hallazgo:** 2 filas de cabecera quedaron como datos (H3).

**Decisión:** eliminarlas.

**Justificación:** no son observaciones, son metadatos del formato. Es el único caso de todo
el plan en que se eliminan filas, y se hace porque esas filas no representan ninguna
transición física. Se eliminan **antes** que nada, porque contaminan cualquier estadístico,
cualquier `unique()` y cualquier conteo por elemento.

```python
df = df[df["element"] != "element"].reset_index(drop=True)
```

---

### L2 — Resolver la mezcla de aire y vacío en la longitud de onda

**Hallazgo:** 10 428 filas traen λ medida **en aire** y 7 860 **en vacío**, todas bajo la
misma columna `obs_wl_vac(nm)` (H2).

**Decisión:** reconstruir el medio a partir de la posición de cada bloque en el archivo
original, guardarlo en una columna `medio`, y generar una columna homogénea
`wl_vacio_nm` convirtiendo las de aire a vacío.

**Justificación:** es el problema más grave del dataset y el más silencioso, porque no
produce ningún error ni ningún valor imposible: produce una columna que **parece** homogénea
y no lo es. Dado que la pregunta científica tiene la longitud de onda como variable central
y compara elementos entre sí, mezclar dos convenciones introduciría un sesgo sistemático de
~0,03 % en un subconjunto de las líneas. Aunque la magnitud sea pequeña, **una variable que
mezcla dos definiciones distintas no es una variable**. El índice de refracción del aire
(n ≈ 1,00028) permite unificarlas sin perder ningún dato.

```python
# El medio se deduce de en que bloque del archivo original estaba cada fila.
texto = open(RUTA_LINES, encoding="utf-8").read()
utiles = [l for l in texto.split("\n") if l.strip() and not l.startswith("---")]
cortes = [i for i, l in enumerate(utiles) if l.startswith("element,sp_num")]

medio = []
for j, ini in enumerate(cortes):
    fin = cortes[j + 1] if j + 1 < len(cortes) else len(utiles)
    etiqueta = "aire" if "obs_wl_air" in utiles[ini] else "vacio"
    medio += [etiqueta] * (fin - ini - 1)   # -1 descarta la propia cabecera

df_fix["medio"] = medio

N_AIRE = 1.00028  # indice de refraccion del aire en condiciones estandar
df_fix["wl_vacio_nm"] = np.where(
    df_fix["medio"] == "aire",
    df_fix["obs_wl_nm"] * N_AIRE,
    df_fix["obs_wl_nm"],
)
```

> **Alternativa recomendada para la sustentación:** volver a descargar fijando el parámetro
> `show_av` en una única convención elimina el problema en el origen. Se deja documentada
> aquí la vía por software porque opera sobre el archivo original ya descargado, que es la
> evidencia que exige la rúbrica.

---

### L3 — Decodificar el artefacto de exportación

**Hallazgo:** el envoltorio `="valor"` deja todas las columnas como texto y esconde los
faltantes tras la cadena `=""` (H1).

**Decisión:** quitar el envoltorio y convertir la cadena vacía resultante en `NaN`.

**Justificación:** sin esto, `isnull()` informa 23 640 nulos en vez de 90 149 — un
diagnóstico falso que haría creer que el dataset está casi completo. Es el primer paso
obligatorio: **ninguna otra decisión de limpieza es evaluable hasta que los faltantes sean
visibles.** Nótese que decodificar no altera ningún dato: `="91.23"` y `91.23` son el mismo
valor.

```python
def decodificar(df):
    salida = df.copy()
    for col in salida.columns:
        # No basta comparar con 'object': pandas 3 usa un dtype 'str' propio.
        if pd.api.types.is_numeric_dtype(salida[col]):
            continue
        s = salida[col].astype(str).str.strip()
        s = s.str.replace(r'^="', "", regex=True).str.replace(r'"$', "", regex=True).str.strip()
        salida[col] = s.replace({"": np.nan, "nan": np.nan}).mask(salida[col].isna())
    return salida
```

---

### L4 — Interpretar la notación científica del NIST en vez de descartarla

**Hallazgo:** 28 020 valores en líneas no son convertibles a número por contener `[...]`,
`+x`, `+`, `*` y letras (H sección 3.2).

**Decisión:** **no** aplicar `pd.to_numeric(errors='coerce')` a secas. Para cada símbolo, se
extrae el valor numérico **y** se conserva su significado en una columna booleana aparte.

**Justificación:** esta es la diferencia más importante entre este dataset y el ejemplo de
clase. Allí, `tbd` en `User_Score` era ruido sin contenido y convertirlo en `NaN` era
correcto. Aquí, `[186101.55]` **sí contiene el valor de la energía**: los corchetes informan
que fue interpolada en vez de medida. Aplicar `coerce` destruiría 3 441 energías inferiores y
3 958 superiores perfectamente utilizables, y con ellas una parte sustancial de la base de
evidencia. La bandera permite después decidir si se filtran o no, sin haber perdido el dato.

```python
def extraer_energia(serie):
    s = serie.astype(str)
    interpolada = s.str.contains(r"\[", na=False)     # valor teorico o interpolado
    origen_desconocido = s.str.contains(r"\+[xy]", na=False)  # energia relativa a un origen
    valor = pd.to_numeric(
        s.str.replace(r"[\[\]]", "", regex=True).str.replace(r"\+[xy]", "", regex=True).str.strip(),
        errors="coerce",
    )
    return valor, interpolada, origen_desconocido


df_fix["Ei_cm1"], df_fix["Ei_interpolada"], df_fix["Ei_origen_desconocido"] = \
    extraer_energia(df_fix["Ei(cm-1)"])
df_fix["Ek_cm1"], df_fix["Ek_interpolada"], df_fix["Ek_origen_desconocido"] = \
    extraer_energia(df_fix["Ek(cm-1)"])
```

**`intens` recibe el mismo tratamiento** (3 769 valores con banderas `*`, `a`, `a*`):

```python
df_fix["intens_valor"] = pd.to_numeric(
    df_fix["intens"].astype(str).str.replace(r"[^0-9.eE+-]", "", regex=True), errors="coerce"
)
df_fix["intens_bandera"] = df_fix["intens"].astype(str).str.replace(r"[0-9.]", "", regex=True)
```

**`ritz_wl_vac(nm)`** con sufijo `+` (216 valores): se extrae el número y se marca el límite.

---

### L5 — Convertir J de fracción a número decimal

**Hallazgo:** `J_i` (46,47 %), `J_k` (46,76 %) y `J` de niveles (43,02 %) vienen como
fracciones `3/2`, y hay casos no resueltos (`0,1,2`) y sin determinar (`---`, 52 casos).

**Decisión:** parsear la fracción a decimal; dejar `NaN` **solo** en los no resueltos, con
una bandera que los distinga.

**Justificación:** `pd.to_numeric` convertiría en `NaN` casi la mitad de la columna, cuando
`3/2` es un número perfectamente definido: 1,5. La validación de la exploración confirmó que
`g = 2J + 1` se cumple en el **100 %** de los 5 570 niveles evaluables, lo que prueba que la
conversión es correcta y da además un mecanismo de verificación automática.

```python
def parsear_J(v):
    t = str(v).strip()
    if t in ("---", "nan", ""):
        return np.nan
    if "," in t:          # J no resuelto: varios valores posibles
        return np.nan
    if "/" in t:
        a, b = t.split("/")
        return float(a) / float(b)
    try:
        return float(t)
    except ValueError:
        return np.nan


df_fix["J_i_num"] = df_fix["J_i"].map(parsear_J)
df_fix["J_i_no_resuelto"] = df_fix["J_i"].astype(str).str.contains(",", na=False)

# Verificacion: debe cumplirse g = 2J + 1
assert (df_niv["g"] == 2 * df_niv["J_num"] + 1).all(), "Inconsistencia cuantica"
```

---

### L6 — Proteger los identificadores de la conversión numérica

**Hallazgo:** `ID_i`, `ID_k` y `Level ID` parecen numéricos pero son códigos con ceros a la
izquierda.

**Decisión:** forzarlos a texto de manera explícita y **excluirlos** de cualquier conversión
automática.

**Justificación:** convertir `006002.000001` a `6002.000001` rompe la clave de unión entre
las dos fuentes. Es el error clásico de "la columna parece numérica, la convierto": el
criterio correcto no es si los valores *parsean* como número, sino si **son cantidades sobre
las que tiene sentido calcular**. Sobre un identificador no se puede promediar.

```python
COLUMNAS_IDENTIFICADOR = ["ID_i", "ID_k", "Level ID"]
for c in COLUMNAS_IDENTIFICADOR:
    df_fix[c] = df_fix[c].astype("string")
```

---

### L7 — Normalizar `Type` y `Acc` como categóricas

**Hallazgo:** `Type` está vacío en 17 955 filas (98,17 %), que **por convención del NIST
significa transición permitida E1**, no dato faltante. Sus valores reales son `E2` (167),
`M1` (111), `UT` (37), `M2` (17) y un anómalo `2P` (1 caso). `Acc` usa la escala ordinal del
NIST: `AAA, AA, A+, A, B+, B, B', C+, C, C', D+, D, E`.

**Decisión:** rellenar `Type` con la categoría explícita `E1`; convertir `Acc` en categórica
ordenada; investigar y reclasificar el único `2P`.

**Justificación:** este es el caso análogo al `K-A` obsoleto del ejemplo de clase: una
categoría que hay que entender antes de tocarla. Imputar `Type` con la moda sería
técnicamente lo mismo (la moda es el vacío), pero **rellenar con `E1` documenta el
significado** en vez de esconderlo. Y `Acc` no es texto libre: es una escala ordenada, y
tratarla como categórica ordenada permite después filtrar por calidad mínima del dato.

```python
df_fix["Type"] = df_fix["Type"].fillna("E1")

ESCALA_ACC = ["AAA", "AA", "A+", "A", "B+", "B", "B'", "C+", "C", "C'", "D+", "D", "E"]
df_fix["Acc"] = pd.Categorical(df_fix["Acc"], categories=ESCALA_ACC, ordered=True)
```

---

### L8 — Longitud de onda: recuperar con Ritz en vez de imputar

**Hallazgo:** `obs_wl` falta en el 46,06 % de las líneas, pero `ritz_wl` solo falta en el
1,00 %.

**Decisión:** crear una columna `lambda_nm` que use la longitud de onda observada cuando
exista y la Ritz cuando no, más una bandera `lambda_origen`. **No se imputa ningún valor
estadístico.**

**Justificación — es la decisión de mayor impacto de todo el plan.** La longitud de onda Ritz
no es una estimación estadística: es el valor **calculado a partir de la diferencia de
energía entre los dos niveles**, es decir, física exacta. Usarla como respaldo es
científicamente legítimo, mientras que imputar con la mediana de la columna produciría una
línea espectral inexistente.

El efecto medido es decisivo:

| Base utilizable para la pregunta científica | Líneas | % |
|---|---|---|
| Solo con λ observada y `Aki` | 4 462 | 24,4 % |
| Con λ observada **o Ritz** y `Aki` | **12 603** | **68,9 %** |
| Con alguna λ disponible | **18 288** | **100 %** |

Se **casi triplica** la evidencia disponible sin inventar un solo dato. Además, resuelve de
paso el 46,07 % de líneas que quedaban "sin dato" al clasificarlas por región espectral.

```python
df_fix["lambda_nm"] = df_fix["obs_wl_nm"].fillna(df_fix["ritz_wl_nm"])
df_fix["lambda_origen"] = np.where(df_fix["obs_wl_nm"].notna(), "observada", "ritz")
```

---

### L9 — `Aki`: no imputar, marcar como no disponible

**Hallazgo:** `Aki` falta en 5 685 líneas (31,08 %), y los faltantes se concentran de forma
muy desigual por espectro (Ne II 87,8 % ausente; He I 0,5 %).

**Decisión:** **no imputar**. Se conserva el `NaN` y se añade `tiene_Aki` como bandera
booleana. Los análisis de la relación λ ↔ Aki se harán sobre el subconjunto de 12 603 líneas
que sí lo tienen, declarándolo explícitamente.

**Justificación — aquí este plan se aparta deliberadamente del ejemplo de clase.** En el
ejemplo, imputar `User_Count` con la mediana era razonable porque el objetivo era conservar
filas para un modelo. Aquí, `Aki` **es la variable dependiente de la pregunta científica**:
imputarla equivale a inventar la respuesta. Tres razones concretas:

1. **La distribución lo prohíbe.** `Aki` abarca 35,2 órdenes de magnitud con asimetría 40,16.
   Cualquier medida de centralidad es físicamente arbitraria sobre ese rango.
2. **El ejemplo de clase ya mostró el desenlace.** Allí, imputar con la mediana global
   colapsó los tres cuartiles al mismo valor y dejó la columna inservible. Con 31 % de
   ausentes y una asimetría de 40, el resultado aquí sería peor.
3. **El faltante es informativo.** Que Ne II tenga 87,8 % de `Aki` ausente no es ruido: dice
   que ese ion está menos caracterizado experimentalmente. Imputarlo borraría ese hallazgo,
   que es en sí mismo un resultado del trabajo.

```python
df_fix["tiene_Aki"] = df_fix["Aki_s-1"].notna()
df_pregunta = df_fix[df_fix["tiene_Aki"] & df_fix["lambda_nm"].notna()].copy()
```

---

### L10 — Añadir las variables derivadas del análisis

**Decisión:** crear `log10_Aki`, `region_espectral` y `E_foton_eV`.

**Justificación:** la correlación λ ↔ Aki pasa de **−0,0023 en escala cruda a −0,6805 en
log-log**. Sin la transformación logarítmica la relación que la pregunta científica busca
es sencillamente invisible. No es un adorno: es la condición para poder responderla.

```python
df_fix["log10_Aki"] = np.log10(df_fix["Aki_s-1"].where(df_fix["Aki_s-1"] > 0))

def region(nm):
    if pd.isna(nm):            return "sin dato"
    if nm < 10:                return "Rayos X"
    if nm < 380:               return "Ultravioleta"
    if nm <= 780:              return "Visible"
    if nm <= 1e6:              return "Infrarrojo"
    return "Microondas/Radio"

df_fix["region_espectral"] = df_fix["lambda_nm"].map(region)

# Energia del foton emitido, derivada de la diferencia de niveles (1 eV = 8065.543937 cm-1)
df_fix["E_foton_eV"] = (df_fix["Ek_cm1"] - df_fix["Ei_cm1"]) / 8065.543937
```

---

### L11 — Descartar columnas sin valor informativo

**Decisión:** eliminar del conjunto de trabajo, documentando el motivo:

| Columna | % nulos | Motivo del descarte |
|---|---|---|
| `Lande` | 99,50 % | Prácticamente vacía; además los 29 valores presentes son estimaciones entre paréntesis. Secundaria para la pregunta. |
| `Prefix` / `Suffix` | 78,79 % / 74,03 % | Solo marcan el corchete de energía interpolada, información ya capturada en la bandera de **L4**. Redundantes. |
| `Leading percentages` | 69,38 % | Texto compuesto no estructurado; secundaria. |
| `Unnamed: 26` | 100 % | Artefacto del parseo. |

**Justificación:** el criterio no es solo el porcentaje de nulos, sino **el porcentaje de
nulos combinado con la irrelevancia para la pregunta**. `Ei(cm-1)` también tiene 19 % de
valores problemáticos y no se descarta, porque es crítica. `Prefix`/`Suffix` se descartan
aunque estén menos vacías que `Lande`, porque son redundantes.

**Se conservan** `unc_obs_wl` (57,94 % nulos), `tp_ref` y `line_ref` pese a su alta tasa de
ausencia: documentan la calidad y la procedencia de cada medición, que la rúbrica exige poder
rastrear.

---

### L12 — Duplicados

**Hallazgo:** 0 filas exactamente duplicadas; 70 transiciones con la misma identidad física;
16 niveles con la misma identidad cuántica.

**Decisión:** **no eliminar nada**; marcar los 70 casos con una bandera e investigarlos.

**Justificación:** `drop_duplicates()` no encuentra nada que borrar, porque las filas difieren
en la referencia bibliográfica. Esos 70 casos son **mediciones independientes de la misma
transición**, publicadas por autores distintos — lo cual es información científica valiosa,
no basura. Eliminarlas arbitrariamente descartaría la medición de un laboratorio sin
criterio. La decisión correcta se toma en el modelo relacional (etapa 5), donde una
transición podrá tener varias mediciones asociadas.

```python
clave_fisica = ["element", "sp_num", "lambda_nm", "conf_i", "term_i", "J_i",
                "conf_k", "term_k", "J_k"]
df_fix["medicion_repetida"] = df_fix.duplicated(subset=clave_fisica, keep=False)
```

---

### L13 — Valores atípicos: conservarlos, con justificación física

**Hallazgo:** `Aki` tiene 2 181 outliers por IQR (17,31 %); `intens` 19,63 %; `unc_ritz_wl`
17,33 %.

**Decisión:** **no se elimina ni se convierte en `NaN` ningún outlier** de las variables
críticas. Se documenta su naturaleza.

**Justificación — caso por caso:**

| Variable | Outliers | Veredicto y razón |
|---|---|---|
| `Aki` | 17,31 % | **Conservar.** Son transiciones prohibidas: su mediana de log₁₀(Aki) es −3,31 (M1) frente a +5,69 (E1). El IQR las marca por ser minoría (1,83 %), no por ser erróneas. Eliminarlas borraría toda una clase de fenómeno físico. |
| `ritz_wl` / `obs_wl` | 12,67 % / 12,10 % | **Conservar.** Los máximos (~6 × 10¹⁰ nm) son transiciones de radiofrecuencia reales. El IQR falla porque la distribución abarca del rayo X a las ondas de radio. |
| `intens` | 19,63 % | **Conservar, pero no comparar entre espectros.** La intensidad relativa del NIST usa una escala arbitraria propia de cada espectro; un "atípico" solo lo es respecto a la mezcla de todas las escalas. |
| `unc_ritz_wl` | 17,33 % | **Conservar.** Una incertidumbre grande acompaña a una longitud de onda grande; es coherente, no anómalo. |
| `g_i` / `g_k` | 2,88 % / 4,49 % | **Conservar.** Valores de hasta 3 200 corresponden a niveles de Rydberg con número cuántico principal alto. `g = 2J+1` se cumple al 100 %. |

**El principio:** el método IQR asume una distribución unimodal y de escala acotada. Ninguna
de estas variables la tiene. Aplicarlo aquí como regla automática destruiría física
legítima. Se usa como **detector que obliga a mirar**, no como regla que decide.

Esta es la diferencia sustantiva con el ejemplo de clase: allí los 10 665 usuarios de
`User_Count` eran plausiblemente un error de captura; aquí un `Aki` de 10⁻²⁴ s⁻¹ es una
transición prohibida real.

---

### L14 — Unión de las dos fuentes

**Decisión:** unir por `ID_i`/`ID_k` ↔ `Level ID`, con **doble merge** (nivel inferior y
superior) y sufijos `_inf` / `_sup`. Conservar las 217 líneas huérfanas marcándolas.

**Justificación:** la unión por identificador alcanza **98,81 %** frente al 97,23 % de la
unión por identidad cuántica reconstruida, y además la clave es **única** (0 duplicados sobre
5 752 niveles), por lo que el merge no puede inflar el dataset — verificado: +0 filas. El
doble merge es obligatorio porque una línea espectral **es** un salto entre dos niveles;
unirla a uno solo describiría la mitad del fenómeno.

Las 217 líneas sin pareja (1,19 %) se conservan: son un hallazgo de calidad de datos del
propio NIST (el catálogo de líneas referencia niveles que su catálogo de niveles no expone),
no un fallo del procedimiento.

> **Recordatorio de alcance:** `df_analysis` es una tabla ancha **de diagnóstico**. El modelo
> relacional de la etapa 5 usará tablas normalizadas (`elemento`, `espectro`, `nivel_energia`,
> `linea`) con claves foráneas. **Unir para explorar, separar para modelar.**

---

## 5. Orden de ejecución — y por qué ese orden

El orden no es arbitrario: cada paso habilita al siguiente y ejecutarlos al revés produce
resultados incorrectos.

| # | Paso | Por qué va aquí |
|---|---|---|
| 1 | **L1** Eliminar cabeceras incrustadas | Contaminan todo conteo, `unique()` y estadístico posterior |
| 2 | **L3** Decodificar el artefacto | Hasta hacerlo, los faltantes son invisibles y **ningún diagnóstico es válido** |
| 3 | **L2** Reconstruir el medio (aire/vacío) | Necesita la posición original de las filas, que se pierde si antes se reordena o se filtra |
| 4 | **L4 · L5 · L6** Corregir tipos | Una columna leída como texto **oculta sus propios atípicos**: no se puede detectar un outlier en algo que pandas cree que es una cadena |
| 5 | **L7** Normalizar categóricas | Requiere tipos ya correctos |
| 6 | **L8** Recuperar λ con Ritz | Requiere que ambas columnas sean numéricas (paso 4) |
| 7 | **L13** Diagnosticar atípicos | Solo tiene sentido sobre columnas ya numéricas y ya completadas |
| 8 | **L9** Decidir sobre faltantes | Va **después** de los atípicos: si se decidiera anular algún outlier, ese `NaN` debe entrar al mismo flujo |
| 9 | **L10** Derivar variables | Requiere las columnas base ya limpias |
| 10 | **L11** Descartar columnas | Al final, para no perder información que algún paso anterior pudiera necesitar |
| 11 | **L12 · L14** Duplicados y unión | Requieren las claves ya normalizadas y protegidas |
| 12 | **Verificación** (sección 8) | Cierre obligatorio |

La secuencia **tipos → atípicos → nulos** es la misma del notebook de limpieza de referencia,
y por la misma razón: allí, `User_Score` no podía imputarse hasta resolver el `tbd` que la
volvía `object`, y `User_Count` no podía imputarse hasta tratar sus outliers.

---

## 6. Tabla resumen de estrategia por columna

| Columna | Problema | Estrategia | Tipo final |
|---|---|---|---|
| `element` | 2 filas basura | Eliminar filas (**L1**) | `category` |
| `sp_num` | Texto | Convertir | `int8` |
| `obs_wl_*(nm)` | 46,06 % nulos + mezcla aire/vacío | Unificar medio (**L2**) + respaldo Ritz (**L8**) | `float64` |
| `ritz_wl_*(nm)` | Sufijo `+` en 216 | Extraer valor + bandera | `float64` |
| `unc_obs_wl` / `unc_ritz_wl` | 57,94 % / 27,45 % nulos | **Conservar sin imputar** | `float64` |
| `intens` | 38,14 % con banderas | Separar valor y bandera (**L4**) | `float64` + `category` |
| `Aki(s^-1)` | 31,08 % nulos, 35 órdenes | **No imputar** (**L9**) + `log10_Aki` | `float64` |
| `fik`, `log_gf` | 31,08 % nulos | No imputar (acompañan a `Aki`) | `float64` |
| `Acc` | Escala ordinal como texto | Categórica **ordenada** (**L7**) | `CategoricalDtype` |
| `Ei` / `Ek (cm-1)` | 19,04 % / 21,90 % con `[...]`, `+x` | Extraer valor + 2 banderas (**L4**) | `float64` + `bool` |
| `conf_i` / `conf_k` | Texto, 307 / 862 únicos | Solo `.str.strip()`; ya son consistentes | `category` |
| `term_i` / `term_k` | 2,4 % nulos | Imputar con `"Desconocido"` | `category` |
| `J_i` / `J_k` | 46 % fracciones | Parsear fracción (**L5**) + bandera no resuelto | `float64` |
| `g_i` / `g_k` | Sin problemas | Convertir | `int16` |
| `Type` | 98,17 % vacío = E1 | Rellenar con `"E1"` (**L7**) | `category` |
| `ID_i` / `ID_k` | Parecen numéricos | **Forzar a texto** (**L6**) | `string` |
| `tp_ref` / `line_ref` | 31 % / 44 % nulos | Conservar; `"Sin referencia"` | `category` |
| `Level (eV)` | 1,10 % nulos | Convertir; no imputar | `float64` |
| `Uncertainty (eV)` | 35,87 % nulos | Conservar sin imputar | `float64` |
| `Lande` | **99,50 % nulos** | **Descartar** (**L11**) | — |
| `Prefix` / `Suffix` | 78,79 % / 74,03 %, redundantes | **Descartar** (**L11**) | — |
| `Leading percentages` | 69,38 % nulos, texto compuesto | **Descartar** (**L11**) | — |
| `Level ID` | 0 % nulos, clave de unión | Forzar a texto (**L6**) | `string` |

**Balance:** de 27 columnas en líneas y 13 en niveles, solo **4 se descartan** y en **ninguna
variable crítica se imputa un valor estadístico**. Es una limpieza deliberadamente
conservadora, y la sección siguiente explica por qué.

---

## 7. Sobre la imputación: por qué casi no se usa, y cómo se usaría

El plan original contemplaba media / mediana / moda según la forma de la distribución. Tras
ver los datos reales, ese esquema **casi no aplica**, y conviene justificar el porqué en vez
de aplicarlo mecánicamente.

### 7.1 Por qué no se imputan las variables críticas

Las tres condiciones que hacían razonable imputar en el ejemplo de clase **no se cumplen**
aquí:

| Condición del ejemplo de clase | Situación real en este dataset |
|---|---|
| El faltante es ruido sin significado | El faltante **significa** "el NIST no lo ha medido" |
| La variable es un predictor secundario | `Aki` y λ **son** las variables de la pregunta |
| La distribución tiene una escala acotada | `Aki` abarca **35,2 órdenes de magnitud** |

Y existe una alternativa mejor que imputar: **recuperar el dato desde otra columna
físicamente equivalente** (L8, con λ Ritz). Eso aporta 8 141 líneas adicionales sin inventar
nada — muchas más de las que cualquier imputación podría "rescatar", y con validez física
total.

### 7.2 Si se imputara, sería por espectro y nunca globalmente

Para las variables **auxiliares** donde la imputación sí tenga sentido, la regla es: **agrupar
por espectro, jamás usar el estadístico global.**

**Justificación con los datos medidos:** la cobertura de `Aki` va del **12,2 % en Ne II al
99,5 % en He I**, y en `Ei(cm-1)` He I tiene 99,9 % de ausentes frente al 0,0 % de C I. Los
18 espectros son **poblaciones físicamente distintas**: las propiedades atómicas del
hidrógeno y del neón difieren en órdenes de magnitud. Una mediana global mezclaría esas
poblaciones y produciría un valor que no corresponde a ningún elemento real.

Este es exactamente el error que el notebook de clase cometió y luego corrigió: imputar
`Critic_Score` con la mediana global colapsó los tres cuartiles al mismo valor, y la solución
fue pasar a la mediana **por género**. Aquí la agrupación natural es **por espectro**.

```python
# Patron correcto: mediana POR ESPECTRO, no global.
for espectro in df_fix["espectro"].dropna().unique():
    mascara = df_fix["espectro"] == espectro
    mediana_local = df_fix.loc[mascara, COLUMNA_AUXILIAR].median()
    df_fix.loc[mascara, COLUMNA_AUXILIAR] = \
        df_fix.loc[mascara, COLUMNA_AUXILIAR].fillna(mediana_local)
```

Y **mediana, nunca media**: la asimetría medida es de 40,16 en `Aki`, 87,94 en `fik` y 115,11
en `unc_ritz_wl`. Con colas así, la media está completamente arrastrada por los extremos.

### 7.3 Categóricas

Se imputan con una **categoría explícita** (`"Desconocido"`, `"Sin referencia"`), no con la
moda. Motivo: es el mismo razonamiento por el que el ejemplo de clase rechazó imputar
`Developer` con la moda — habría asignado Nintendo como desarrollador de Call of Duty. Aquí,
imputar `term_i` con el término más frecuente asignaría a una transición un estado cuántico
que no es el suyo. Una categoría explícita preserva la honestidad del dato.

---

## 8. Verificación posterior a la limpieza

Comprobaciones obligatorias al terminar, redactadas como criterios de aceptación:

1. **Las distribuciones no se aplanaron.** Re-ejecutar `describe().T` y confirmar que q1,
   mediana y q3 siguen siendo **distintos entre sí** en las variables críticas. Es la
   comprobación que en el ejemplo de clase reveló que la imputación había arruinado cuatro
   columnas.
2. **No aparecieron atípicos nuevos.** Comparar los boxplots antes/después: el conteo de
   outliers por IQR no debe aumentar respecto a los valores de la sección 3.6.
3. **La física sigue cumpliéndose.** Re-ejecutar las cinco validaciones de la sección 3.5 y
   la identidad `g = 2J + 1`: deben seguir dando **0 violaciones** y **100 %**.
4. **No se perdieron filas.** `len(df_limpio) == 18 288` (18 290 menos las 2 cabeceras). El
   único paso que elimina filas es **L1**.
5. **La unión no duplicó filas.** `len(df_analysis) == len(df_lines_limpio)`.
6. **La base de evidencia creció.** Las líneas con λ y `Aki` deben pasar de 4 462 a **12 603**.
7. **La correlación se mantiene.** Pearson log-log λ ↔ Aki ≈ **−0,68**. Una desviación
   grande indicaría que la limpieza alteró la relación que se quiere estudiar.
8. **Los identificadores sobrevivieron.** `df["ID_i"].str.len().unique()` debe conservar los
   ceros a la izquierda; ningún ID convertido a `float`.

---

## 9. Trazabilidad

Siguiendo el patrón `df_toclean` / `df_aux` / `df_fix` del notebook de referencia:

| DataFrame | Contenido | Se modifica |
|---|---|---|
| `df_lines_raw`, `df_levels_raw` | Tal como salieron del CSV, con artefacto incluido | **Nunca** |
| `df_lines`, `df_levels` | Decodificados (L3), sin limpiar | **Nunca** |
| `df_toclean` | Copia de trabajo donde se aplican L1 … L14 | Sí |
| `df_aux` | Respaldo de los avances no destructivos (tipos, categóricas) | Solo se le añaden avances |
| `df_fix` | Resultado final | Sí |

Reglas:

- Trabajar **siempre sobre `.copy()`**, nunca sobre los originales.
- Cada paso va precedido de una celda markdown que explica **qué problema se detectó** y
  **por qué se eligió esa solución**.
- Tras cada transformación, imprimir el conteo de nulos y de filas para dejar el efecto
  registrado.
- Los archivos de `datos_originales/` **no se sobrescriben jamás**.

---

## 10. Entregables de la etapa de limpieza

| Archivo | Contenido |
|---|---|
| `notebooks/datos_procesados/lineas_limpias.csv` | 18 288 líneas, tipos corregidos, λ unificada, banderas de procedencia |
| `notebooks/datos_procesados/niveles_limpios.csv` | 5 752 niveles, J parseado, IDs preservados |
| `notebooks/datos_procesados/analisis_limpio.csv` | `df_analysis` limpio, doble merge por `Level ID` |
| `notebooks/04_limpieza_datos.ipynb` | Ejecución documentada de L1 … L14 |

Estos archivos son el insumo directo de la **etapa 5: diseño del modelo relacional**, donde
la estructura ancha de `df_analysis` se normalizará en las tablas `elemento`, `espectro`,
`nivel_energia` y `linea` con sus claves foráneas.

---

## 11. Resumen ejecutivo

Este dataset **no está sucio: está codificado**. No contiene un solo valor físicamente
imposible, no tiene filas duplicadas y cumple la identidad cuántica `g = 2J + 1` en el 100 %
de los casos. Sus problemas son de otra naturaleza:

1. Un **envoltorio de exportación** que esconde 80 697 valores ausentes (66 509 en líneas y
   14 188 en niveles).
2. Una **mezcla silenciosa de aire y vacío** en la variable central de la pregunta.
3. Una **notación científica propia** que un `to_numeric` ingenuo destruiría.
4. Faltantes que son **información**, no ruido.

En consecuencia, la limpieza propuesta es **conservadora por diseño**: descarta 4 columnas,
elimina 2 filas y no imputa ni un solo valor en las variables críticas. La ganancia principal
no viene de rellenar huecos, sino de **decodificar correctamente** e interpretar la notación
del NIST: eso por sí solo lleva la base de evidencia de 4 462 a 12 603 líneas.

El principio que atraviesa todo el documento: **cada transformación debe poder justificarse
en términos físicos, no solo estadísticos.** Por eso las transiciones prohibidas se conservan
pese a que el IQR las marca como atípicas, y por eso `Aki` no se imputa pese a que el 31 % de
sus valores falte.

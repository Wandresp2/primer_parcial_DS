# Propuesta de modelo relacional
## Proyecto: Óptica y Fotónica — Primer Parcial
### Base de datos MySQL a partir de los datos limpios del NIST ASD

**Estudiante:** Perez Criollo Andres David
**Entrada:** `notebooks/datos_procesados/` (generado por `04_limpieza_datos.ipynb`)
**Verificación previa:** sección 18 del notebook 04
**Documento hermano:** `docs/RESULTADOS_exploracion_y_limpieza.md`

> Todas las cardinalidades y todas las afirmaciones sobre dependencias funcionales de este
> documento fueron **comprobadas contra los datos limpios reales**, no supuestas.

---

## 1. Punto de partida

Los datos limpios son tres archivos planos:

| Archivo | Filas | Columnas |
|---|---|---|
| `dataset_limpio.csv` | 18 288 | 65 |
| `lineas_limpias.csv` | 18 288 | 47 |
| `niveles_limpios.csv` | 5 752 | 14 |

Cargar cualquiera de ellos como **una sola tabla** sería un error, y el enunciado lo penaliza
de forma explícita. En `dataset_limpio.csv`, por ejemplo, el símbolo `C` del carbono se repite
en 3 707 filas, la configuración electrónica de un nivel se repite una vez por cada línea que
lo usa, y las referencias bibliográficas vienen como listas separadas por comas dentro de una
celda.

El objetivo de este modelo es **eliminar esa redundancia y garantizar la integridad
referencial**, conservando toda la información.

### Qué entidades hay en el fenómeno físico

Antes de pensar en tablas conviene identificar los objetos reales:

- Un **elemento** químico (hidrógeno, helio…).
- Un **espectro**: el elemento en un estado de ionización concreto. `Ne I` (neón neutro) y
  `Ne II` (neón ionizado) son objetos distintos, con niveles y líneas propios.
- Un **nivel de energía**: un escalón interno del átomo.
- Una **línea espectral**: el salto de un electrón **entre dos niveles**, que emite luz.
- Una **referencia bibliográfica**: la publicación de donde salió cada medición.
- Dos **catálogos** de códigos: el tipo de transición y la escala de exactitud del NIST.

Esa lista es, directamente, el modelo relacional.

---

## 2. Las nueve tablas

### 2.1 Catálogos

#### `elemento` — 10 filas

| Atributo | Tipo MySQL | Restricción | Descripción |
|---|---|---|---|
| `id_elemento` | `TINYINT UNSIGNED` | **PK** | Identificador |
| `simbolo` | `VARCHAR(3)` | `NOT NULL`, `UNIQUE` | H, He, Li, Be, B, C, N, O, F, Ne |
| `nombre` | `VARCHAR(20)` | `NOT NULL` | Hidrógeno, Helio, … |
| `numero_atomico` | `TINYINT UNSIGNED` | `NOT NULL`, `UNIQUE` | 1 … 10 |

#### `tipo_transicion` — 5 filas

| Atributo | Tipo MySQL | Restricción | Descripción |
|---|---|---|---|
| `codigo` | `VARCHAR(4)` | **PK** | `E1`, `E2`, `M1`, `M2`, `UT` |
| `nombre` | `VARCHAR(40)` | `NOT NULL` | Dipolo eléctrico, cuadrupolo eléctrico… |
| `es_permitida` | `BOOLEAN` | `NOT NULL` | `TRUE` solo para `E1` |
| `descripcion` | `VARCHAR(255)` | | Significado físico |

> `UT` significa *unclassified transition*: el NIST no determinó el tipo.

#### `exactitud` — 13 filas

| Atributo | Tipo MySQL | Restricción | Descripción |
|---|---|---|---|
| `codigo` | `VARCHAR(3)` | **PK** | `AAA`, `AA`, `A+`, `A`, `B+`, `B`, `B'`, `C+`, `C`, `C'`, `D+`, `D`, `E` |
| `orden` | `TINYINT UNSIGNED` | `NOT NULL`, `UNIQUE` | 1 = mejor … 13 = peor |
| `tolerancia_max_pct` | `DECIMAL(5,2)` | | Error máximo que garantiza el NIST |
| `descripcion` | `VARCHAR(100)` | | |

> El atributo `orden` es la razón de ser de esta tabla: convierte un código de texto en una
> **escala ordenada**, que permite consultas del tipo *"solo líneas con exactitud mejor que B"*.
> Esa semántica no está en el archivo plano.

#### `referencia` — 377 filas

| Atributo | Tipo MySQL | Restricción | Descripción |
|---|---|---|---|
| `codigo` | `VARCHAR(20)` | **PK** | `L22715`, `T8637`, … |
| `tipo_fuente` | `ENUM('nivel','linea','probabilidad')` | | De qué catálogo procede |

### 2.2 Entidades principales

#### `espectro` — 18 filas

| Atributo | Tipo MySQL | Restricción | Descripción |
|---|---|---|---|
| `id_espectro` | `TINYINT UNSIGNED` | **PK** | |
| `id_elemento` | `TINYINT UNSIGNED` | **FK** → `elemento`, `NOT NULL` | |
| `estado_ionizacion` | `TINYINT UNSIGNED` | `NOT NULL` | 1 = neutro, 2 = una vez ionizado |
| `notacion` | `VARCHAR(8)` | `NOT NULL`, `UNIQUE` | `H I`, `Ne II`, … |
| | | `UNIQUE (id_elemento, estado_ionizacion)` | |

#### `nivel_energia` — 5 752 filas

| Atributo | Tipo MySQL | Restricción | Descripción |
|---|---|---|---|
| `id_nivel` | `VARCHAR(20)` | **PK** | Identificador interno del NIST (`006002.000001`) |
| `id_espectro` | `TINYINT UNSIGNED` | **FK** → `espectro`, `NOT NULL` | |
| `configuracion` | `VARCHAR(80)` | | Configuración electrónica (`2s2.2p2.(3P).3d`) |
| `termino` | `VARCHAR(20)` | | Término espectroscópico (`2P*`, `3D`) |
| `j_valor` | `DECIMAL(4,1)` | | Momento angular total (1.5 para `3/2`) |
| `j_texto` | `VARCHAR(20)` | | Valor original, incluidos los no resueltos |
| `j_resuelto` | `BOOLEAN` | | `FALSE` si el NIST no determinó un único J |
| `g` | `SMALLINT UNSIGNED` | `CHECK (j_valor IS NULL OR g = 2*j_valor+1)` | Degeneración |
| `energia_ev` | `DECIMAL(18,9)` | | Energía del nivel |
| `energia_interpolada` | `BOOLEAN` | `NOT NULL` | La energía es calculada, no medida |
| `incertidumbre_ev` | `DECIMAL(18,12)` | | |

> **Clave primaria natural.** Se usa el identificador del propio NIST en vez de inventar uno
> autoincremental, porque ya es único (verificado: **0 duplicados, 0 nulos** sobre 5 752 filas)
> y mantiene la trazabilidad con la fuente oficial. Es `VARCHAR` y no numérico: convertirlo a
> número le borraría los ceros a la izquierda.

#### `linea_espectral` — 18 288 filas

| Atributo | Tipo MySQL | Restricción | Descripción |
|---|---|---|---|
| `id_linea` | `INT UNSIGNED AUTO_INCREMENT` | **PK** | |
| `id_espectro` | `TINYINT UNSIGNED` | **FK** → `espectro`, `NOT NULL` | |
| `id_nivel_inferior` | `VARCHAR(20)` | **FK** → `nivel_energia`, **NULL** | |
| `id_nivel_superior` | `VARCHAR(20)` | **FK** → `nivel_energia`, **NULL** | |
| `codigo_tipo_transicion` | `VARCHAR(4)` | **FK** → `tipo_transicion`, `NOT NULL` | |
| `codigo_exactitud` | `VARCHAR(3)` | **FK** → `exactitud`, **NULL** | Nulo en las 5 685 líneas sin `Aki` |
| `longitud_onda_nm` | `DECIMAL(18,6)` | `CHECK (longitud_onda_nm > 0)` | Valor definitivo |
| `longitud_onda_origen` | `ENUM('observada','ritz')` | `NOT NULL` | De dónde salió |
| `medio` | `ENUM('aire','vacio')` | `NOT NULL` | Medio de la medición |
| `longitud_onda_obs_nm` | `DECIMAL(18,6)` | | Medida en laboratorio |
| `longitud_onda_ritz_nm` | `DECIMAL(18,6)` | | Calculada de los niveles |
| `ritz_es_limite` | `BOOLEAN` | | El valor Ritz es un límite |
| `incertidumbre_obs_nm` | `DECIMAL(18,12)` | | |
| `incertidumbre_ritz_nm` | `DECIMAL(18,12)` | | |
| `aki_s1` | `DOUBLE` | `CHECK (aki_s1 IS NULL OR aki_s1 > 0)` | Coeficiente de Einstein |
| `fuerza_oscilador_fik` | `DOUBLE` | | |
| `log_gf` | `DECIMAL(10,5)` | | **Se almacena** — ver sección 6.3 |
| `intensidad_valor` | `DOUBLE` | | Escala arbitraria por espectro |
| `intensidad_bandera` | `VARCHAR(8)` | | Bandera de calidad de la línea |
| `energia_inferior_cm1` | `DECIMAL(18,6)` | | |
| `energia_superior_cm1` | `DECIMAL(18,6)` | `CHECK (energia_superior_cm1 > energia_inferior_cm1)` | |
| `energia_inferior_interpolada` | `BOOLEAN` | | |
| `energia_superior_interpolada` | `BOOLEAN` | | |
| `energia_inferior_origen_desconocido` | `BOOLEAN` | | |
| `energia_superior_origen_desconocido` | `BOOLEAN` | | |
| `medicion_repetida` | `BOOLEAN` | | La transición aparece medida más de una vez |

**Por qué `DOUBLE` y no `DECIMAL` para `aki_s1`:** abarca 35 órdenes de magnitud (de 4,24 × 10⁻²⁴
a 7,00 × 10¹¹). Ningún `DECIMAL` de precisión razonable lo cubre.

**Por qué las claves foráneas de nivel son nulables:** 215 líneas (1,18 %) no traen
identificador de nivel en el catálogo del NIST. Verificado: de las que sí lo traen,
**0 son huérfanas**. La nulabilidad refleja un hueco real de la fuente, no un defecto del
modelo.

### 2.3 Tablas puente (relaciones N:M)

#### `linea_referencia` — ~24 757 filas

| Atributo | Tipo MySQL | Restricción |
|---|---|---|
| `id_linea` | `INT UNSIGNED` | **FK** → `linea_espectral` |
| `codigo_referencia` | `VARCHAR(20)` | **FK** → `referencia` |
| `rol` | `ENUM('probabilidad','longitud_onda')` | |
| | | **PK (`id_linea`, `codigo_referencia`, `rol`)** |

Desglose verificado: 13 986 filas con rol `probabilidad` y 10 771 con rol `longitud_onda`.

> El atributo `rol` forma parte de la clave primaria porque **la misma publicación puede ser
> fuente de la longitud de onda y de la probabilidad de la misma línea**, y son dos hechos
> distintos que hay que poder distinguir.

#### `nivel_referencia` — 3 592 filas

| Atributo | Tipo MySQL | Restricción |
|---|---|---|
| `id_nivel` | `VARCHAR(20)` | **FK** → `nivel_energia` |
| `codigo_referencia` | `VARCHAR(20)` | **FK** → `referencia` |
| | | **PK (`id_nivel`, `codigo_referencia`)** |

---

## 3. Relaciones y cardinalidades

```
                 ┌──────────────┐
                 │  elemento    │  10
                 └──────┬───────┘
                        │ 1
                        │
                        │ N
                 ┌──────┴───────┐
                 │  espectro    │  18
                 └──┬────────┬──┘
               1    │        │    1
                    │        │
               N    │        │    N
        ┌───────────┴──┐  ┌──┴──────────────┐
        │nivel_energia │  │ linea_espectral │ 18 288
        │    5 752     │  └──┬───────┬────┬─┘
        └──┬────────┬──┘     │       │    │
           │        │        │       │    │  N        ┌──────────────────┐
           │        │ 1      │ N     │    └───────────┤ tipo_transicion  │ 5
           │        └────────┘       │    │  N        └──────────────────┘
           │         (dos veces:     │    └───────────┤    exactitud     │ 13
           │      inferior/superior) │                └──────────────────┘
           │ N                       │ N
     ┌─────┴──────────┐        ┌─────┴────────────┐
     │nivel_referencia│        │ linea_referencia │ 24 757
     │     3 592      │        └─────┬────────────┘
     └─────┬──────────┘              │ N
           │ N                       │
           │        ┌────────────────┴──┐
           └────────┤    referencia     │ 377
                    └───────────────────┘
```

### Tabla de relaciones

| # | Desde | Hacia | Cardinalidad | Significado |
|---|---|---|---|---|
| 1 | `elemento` | `espectro` | **1:N** | Un elemento tiene varios estados de ionización |
| 2 | `espectro` | `nivel_energia` | **1:N** | Un espectro tiene muchos niveles de energía |
| 3 | `espectro` | `linea_espectral` | **1:N** | Un espectro tiene muchas líneas |
| 4 | `nivel_energia` | `linea_espectral` | **1:N** | Un nivel es el **origen** de muchas líneas |
| 5 | `nivel_energia` | `linea_espectral` | **1:N** | Un nivel es el **destino** de muchas líneas |
| 6 | `tipo_transicion` | `linea_espectral` | **1:N** | Un tipo clasifica muchas líneas |
| 7 | `exactitud` | `linea_espectral` | **1:N** | Un grado de exactitud califica muchas líneas |
| 8 | `linea_espectral` | `referencia` | **N:M** | Vía `linea_referencia` |
| 9 | `nivel_energia` | `referencia` | **N:M** | Vía `nivel_referencia` |

### Las relaciones 4 y 5: dos caminos hacia la misma tabla

Es la particularidad más característica de este modelo. **Una línea espectral no "pertenece" a
un nivel: es el salto entre dos.** Por eso `linea_espectral` tiene **dos claves foráneas
distintas apuntando a `nivel_energia`**: `id_nivel_inferior` (de dónde sale el electrón) e
`id_nivel_superior` (de dónde cae).

Modelar solo una de las dos describiría la mitad del fenómeno. Y en SQL obliga a hacer
**dos `JOIN` a la misma tabla con alias distintos**, que es exactamente el tipo de consulta
avanzada que el enunciado pide.

### Sobre las relaciones 1:1

**No hay ninguna, y es deliberado.** Una relación 1:1 significa partir una entidad en dos
tablas, y solo se justifica cuando hay atributos muy voluminosos de uso poco frecuente, o
cuando distintos subconjuntos de atributos tienen permisos de acceso distintos. Aquí no ocurre
ninguna de las dos cosas: todos los atributos de una línea describen esa línea y se consultan
juntos. Introducir una 1:1 solo añadiría un `JOIN` sin ganancia.

---

## 4. Cumplimiento de la Primera Forma Normal (1FN)

> **Regla:** todos los valores deben ser **atómicos** — una celda, un valor. No se admiten
> listas ni grupos repetidos.

### La violación que hay que corregir

Los datos limpios **violan la 1FN en tres columnas**, y está medido:

| Columna | Valores que son listas, no valores atómicos |
|---|---|
| `ref_probabilidad` | **1 345** |
| `ref_longitud_onda` | **359** |
| `referencia` (niveles) | **76** |

Un valor real de `ref_probabilidad` es, por ejemplo:

```
L22715c200,L20736
```

Eso no es una referencia: son dos. Guardarlo así impide buscar todas las líneas de una
publicación concreta sin recurrir a un `LIKE '%...%'` — lento, propenso a falsos positivos
(`L2073` casaría con `L20736`) e imposible de proteger con una clave foránea.

### La corrección

Cada elemento de la lista pasa a ser **una fila** en la tabla puente correspondiente:

**Antes (viola 1FN):**

| id_linea | ref_probabilidad |
|---|---|
| 1 | `L22715c200,L20736` |

**Después (cumple 1FN):**

| id_linea | codigo_referencia | rol |
|---|---|---|
| 1 | `L22715c200` | probabilidad |
| 1 | `L20736` | probabilidad |

Esta descomposición es la que genera las 24 757 filas de `linea_referencia` y las 3 592 de
`nivel_referencia`, sobre un catálogo de **377 referencias únicas**.

### Otras comprobaciones de 1FN

- **No hay grupos repetidos de columnas.** El caso `conf_i / term_i / J_i` frente a
  `conf_k / term_k / J_k` en el archivo plano *parece* un grupo repetido, pero desaparece al
  normalizar: esos atributos ya no viven en la línea, sino en `nivel_energia`, y la línea solo
  guarda dos claves foráneas.
- **Todas las columnas tienen un único tipo.** La limpieza (L4 y L5) separó los valores
  mezclados: `500*` se dividió en `intensidad_valor` (500) e `intensidad_bandera` (`*`), y
  `[186101.55]` en `energia_inferior_cm1` más `energia_inferior_interpolada`.
- **Cada tabla tiene clave primaria.** Verificado: `id_nivel` e `id_linea` tienen 0 duplicados
  y 0 nulos.

---

## 5. Cumplimiento de la Segunda Forma Normal (2FN)

> **Regla:** estando en 1FN, ningún atributo no clave puede depender **solo de una parte** de
> una clave primaria compuesta.

Solo dos tablas tienen clave compuesta, y el análisis es inmediato:

| Tabla | Clave compuesta | Atributos no clave | ¿Puede haber dependencia parcial? |
|---|---|---|---|
| `linea_referencia` | (`id_linea`, `codigo_referencia`, `rol`) | **ninguno** | **No** — sin atributos no clave no hay nada que pueda depender parcialmente |
| `nivel_referencia` | (`id_nivel`, `codigo_referencia`) | **ninguno** | **No** — mismo argumento |

Las otras siete tablas tienen **clave primaria simple** (un solo atributo), y por definición
una clave de un atributo no admite dependencias parciales. **Las nueve tablas están en 2FN.**

### Un caso que sí habría violado 2FN

Si en `linea_referencia` se hubiese guardado, por comodidad, el año de publicación de la
referencia:

```
linea_referencia(id_linea, codigo_referencia, rol, anio_publicacion)
```

`anio_publicacion` dependería **solo de `codigo_referencia`**, que es una parte de la clave.
Eso es una dependencia parcial y violaría 2FN. Por eso ese atributo, si se necesita, va en la
tabla `referencia`.

---

## 6. Cumplimiento de la Tercera Forma Normal (3FN)

> **Regla:** estando en 2FN, ningún atributo no clave puede depender de **otro atributo no
> clave** (dependencia transitiva). Todo debe depender de la clave, de toda la clave y de nada
> más que la clave.

Esta es la sección donde el modelo toma sus decisiones más finas, y **todas están respaldadas
por comprobaciones sobre los datos reales**.

### 6.1 Atributos derivados: se calculan, no se almacenan

El archivo `dataset_limpio.csv` incluye cuatro columnas que son **función de otras columnas no
clave**. Almacenarlas en `linea_espectral` sería una dependencia transitiva y una fuente de
inconsistencias (si alguien corrige la longitud de onda y olvida recalcular la región, la
tabla queda mintiendo).

| Atributo derivado | Depende de | Decisión |
|---|---|---|
| `region_espectral` | `longitud_onda_nm` | **No se almacena** |
| `longitud_onda_vacio_nm` | `longitud_onda_nm`, `medio` | **No se almacena** |
| `log10_aki` | `aki_s1` | **No se almacena** |
| `energia_foton_ev` | `energia_superior_cm1`, `energia_inferior_cm1` | **No se almacena** |
| `tiene_aki` | `aki_s1` | **No se almacena** (`aki_s1 IS NOT NULL` lo resuelve) |

Se exponen mediante una **vista**, que los calcula al vuelo y no puede desincronizarse:

```sql
CREATE OR REPLACE VIEW v_linea_analisis AS
SELECT
    l.id_linea,
    e.notacion                         AS espectro,
    el.simbolo                         AS elemento,
    l.longitud_onda_nm,
    -- Homogeneizacion al vacio (n del aire = 1.00028)
    CASE WHEN l.medio = 'aire'
         THEN l.longitud_onda_nm * 1.00028
         ELSE l.longitud_onda_nm END   AS longitud_onda_vacio_nm,
    -- Region del espectro electromagnetico
    CASE
        WHEN l.longitud_onda_nm <   10 THEN 'Rayos X'
        WHEN l.longitud_onda_nm <  380 THEN 'Ultravioleta'
        WHEN l.longitud_onda_nm <= 780 THEN 'Visible'
        WHEN l.longitud_onda_nm <= 1e6 THEN 'Infrarrojo'
        ELSE 'Microondas/Radio'
    END                                AS region_espectral,
    l.aki_s1,
    LOG10(l.aki_s1)                    AS log10_aki,
    (l.energia_superior_cm1 - l.energia_inferior_cm1) / 8065.543937 AS energia_foton_ev,
    l.codigo_tipo_transicion,
    t.es_permitida
FROM linea_espectral l
JOIN espectro        e  ON e.id_espectro = l.id_espectro
JOIN elemento        el ON el.id_elemento = e.id_elemento
JOIN tipo_transicion t  ON t.codigo = l.codigo_tipo_transicion;
```

### 6.2 El caso de `g` y `j_valor`: una excepción documentada

La exploración demostró que **`g = 2J + 1` se cumple en el 100 %** de los 5 570 niveles donde
ambos valores existen. Eso es una dependencia funcional `j_valor → g`, y la 3FN pediría
eliminar `g` y derivarla.

**Pero hay un obstáculo medido: 130 niveles tienen `g` documentado y `J` sin resolver.** El
NIST no determinó un valor único de J (aparece como `---`, `0,1,2` o incluso `1/2 or 3/2`)
pero sí conoce la degeneración.

| Opción | Consecuencia |
|---|---|
| Derivar `g` como columna generada | Se **pierden 130 registros** de información real |
| Almacenar ambos sin más | Dependencia transitiva sin control: los datos pueden divergir |
| **Almacenar ambos con `CHECK`** ← elegida | Se conserva todo y la dependencia queda **forzada por el motor** |

```sql
g SMALLINT UNSIGNED,
CONSTRAINT chk_degeneracion
    CHECK (j_valor IS NULL OR g = 2 * j_valor + 1)
```

Es una **denormalización consciente y acotada**: la restricción `CHECK` hace imposible que `g`
y `j_valor` se contradigan, que es exactamente el riesgo que la 3FN busca evitar. Se documenta
como excepción justificada, no se esconde.

### 6.3 Una dependencia que parecía existir y no existe

Físicamente, `log(gf)` debería poder calcularse como `log10(g_i × f_ik)`. Si fuese cierto,
`log_gf` sería un atributo derivado y habría que eliminarlo por 3FN.

**Se comprobó contra los datos antes de decidir:**

| Comprobación | Resultado |
|---|---|
| Casos evaluables | 12 603 |
| Coinciden dentro de 0,01 | **92,84 %** |
| Diferencia máxima | **10,96** |

La relación **no se cumple** en el 7,16 % de los casos, con desviaciones enormes. Por lo tanto
`log_gf` **no es derivable** y **debe almacenarse**.

> Este es el hallazgo metodológicamente más importante del diseño: era una dependencia
> plausible, razonable y **falsa**. Haberla asumido sin verificar habría producido un esquema
> que pierde datos de forma silenciosa. **Toda dependencia funcional se verifica contra los
> datos antes de usarla como argumento de normalización.**

### 6.4 `espectro.notacion`: por qué sigue cumpliendo 3FN

`notacion` (`Ne II`) se obtiene concatenando el símbolo del elemento con el estado de
ionización en numeración romana. Parece una dependencia transitiva.

No lo es: depende de (`id_elemento`, `estado_ionizacion`), que es una **clave candidata** de
`espectro` — está declarada `UNIQUE`. La 3FN admite que un atributo dependa de una clave
candidata; solo prohíbe que dependa de atributos **no clave**. Se conserva porque aparece en
casi todas las consultas y evita una concatenación repetida.

### 6.5 `linea_espectral.id_espectro`: por qué se conserva

El espectro de una línea coincide con el de sus niveles. Verificado: **18 073 de 18 073 casos,
el 100 %**. Eso sugeriría que `id_espectro` es derivable vía `id_nivel_inferior` y podría
eliminarse.

**No se elimina, por una razón concreta:** las 215 líneas sin identificador de nivel tendrían
su espectro en `NULL`, y se perdería el elemento al que pertenecen — que es una de las
variables centrales de la pregunta científica. La dependencia se rompe justo donde las claves
foráneas son nulas, así que no es una dependencia transitiva válida sobre toda la relación.

El 100 % de coherencia se preserva como **restricción de integridad verificable**, no como
motivo de eliminación.

### 6.6 Revisión tabla por tabla

| Tabla | ¿Dependencias transitivas? | Estado |
|---|---|---|
| `elemento` | `simbolo`, `nombre` y `numero_atomico` dependen solo de la PK (y son claves candidatas entre sí) | **3FN** |
| `tipo_transicion` | Todos los atributos dependen del `codigo` | **3FN** |
| `exactitud` | `orden` y `tolerancia_max_pct` dependen del `codigo` | **3FN** |
| `referencia` | `tipo_fuente` depende del `codigo` | **3FN** |
| `espectro` | `notacion` depende de una clave candidata (§6.4) | **3FN** |
| `nivel_energia` | `g` ← `j_valor` controlada por `CHECK` (§6.2) | **3FN con excepción documentada** |
| `linea_espectral` | Derivados sacados a la vista (§6.1); `log_gf` verificado como no derivable (§6.3) | **3FN** |
| `linea_referencia` | Sin atributos no clave | **3FN** |
| `nivel_referencia` | Sin atributos no clave | **3FN** |

---

## 7. Integridad verificada antes de implementar

Comprobaciones de la sección 18 del notebook 04, sobre los datos limpios reales:

| Comprobación | Resultado |
|---|---|
| `nivel_energia.id_nivel` único y no nulo | **0 duplicados, 0 nulos** → PK válida |
| `linea_espectral.id_linea` único y no nulo | **0 duplicados, 0 nulos** → PK válida |
| FK `id_nivel_inferior` huérfanas | **0** (215 nulas, 1,18 %) |
| FK `id_nivel_superior` huérfanas | **0** (215 nulas, 1,18 %) |
| Espectro de la línea = espectro de sus niveles | **18 073 / 18 073 (100 %)** |
| Líneas sin tipo de transición | **0** → la FK puede ser `NOT NULL` |
| Niveles sin espectro | **0** → la FK puede ser `NOT NULL` |

**La base de datos se puede construir con integridad referencial estricta y sin perder una
sola fila.**

---

## 8. Orden de carga (ETL)

Las claves foráneas imponen el orden: nunca se inserta una fila cuya referencia aún no exista.

```
1. elemento          (10)       ─┐
2. tipo_transicion   (5)         │ catálogos: sin dependencias
3. exactitud         (13)        │
4. referencia        (377)      ─┘
5. espectro          (18)          depende de elemento
6. nivel_energia     (5 752)       depende de espectro
7. linea_espectral   (18 288)      depende de espectro, nivel_energia, tipo_transicion, exactitud
8. nivel_referencia  (3 592)       depende de nivel_energia y referencia
9. linea_referencia  (24 757)      depende de linea_espectral y referencia
```

**Total: 52 812 filas** repartidas en 9 tablas, frente a las 18 288 filas × 65 columnas de una
única tabla plana.

El proceso será automatizado en un notebook `05_etl_carga_mysql.ipynb` que lee los CSV de
`datos_procesados/`, construye cada tabla y la inserta con SQLAlchemy. **No habrá inserción
manual de registros**, como exige el enunciado.

---

## 9. Qué consultas habilita este modelo

Cada tabla existe porque hace posible una pregunta que el archivo plano no responde bien:

| Pregunta científica | Cómo la resuelve el modelo |
|---|---|
| ¿Cómo se distribuyen las líneas por región del espectro, y por elemento? | `JOIN` de `linea_espectral` con `espectro` y `elemento`, agrupando por la región calculada en `v_linea_analisis` |
| ¿Qué relación hay entre `Aki` y la longitud de onda **en cada elemento**? | Correlación sobre `log10_aki` agrupando por elemento |
| ¿Las transiciones prohibidas tienen `Aki` menor? | `JOIN` con `tipo_transicion` filtrando por `es_permitida` |
| ¿Qué salto de energía produce cada línea? | **Doble `JOIN`** a `nivel_energia` con alias `inf` y `sup` |
| ¿Qué elementos están mejor caracterizados experimentalmente? | Proporción de `aki_s1 IS NOT NULL` por espectro |
| ¿Qué publicación aportó más mediciones? | `JOIN` con `linea_referencia` agrupando por referencia |
| ¿Solo líneas de alta calidad? | `JOIN` con `exactitud` filtrando por `orden <= 4` |

Las dos últimas son **imposibles sin normalizar**: la primera requiere que las referencias
sean atómicas (1FN) y la segunda requiere que la escala de exactitud tenga un orden, que no
existe en el archivo plano.

---

## 10. Resumen

| Aspecto | Resultado |
|---|---|
| Tablas | **9** (4 catálogos, 3 entidades, 2 puente) |
| Relaciones | **9** (7 de tipo 1:N, 2 de tipo N:M, 0 de tipo 1:1) |
| Forma normal alcanzada | **3FN**, con una excepción documentada y forzada por `CHECK` |
| Violaciones de 1FN corregidas | **1 780** celdas con listas → 28 349 filas atómicas |
| Claves foráneas huérfanas | **0** |
| Filas totales | 52 812 |
| Vistas | 1 (`v_linea_analisis`, para los atributos derivados) |

**Siguiente paso:** escribir el `schema.sql` que crea estas 9 tablas con sus restricciones,
construir el diagrama entidad-relación en DBeaver y desarrollar el ETL que las puebla desde
`datos_procesados/`.

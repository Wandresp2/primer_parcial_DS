"""
Interfaz Streamlit — Óptica y Fotónica (NIST ASD → MySQL).
Fase 6: 7 secciones + filtros + Plotly.
Creado por: Andres David Perez
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import mysql_config, ping, read_sql  # noqa: E402

st.set_page_config(
    page_title="Óptica y Fotónica · NIST ASD",
    page_icon="🔬",
    layout="wide",
)

SECCIONES = [
    "1. Inventario",
    "2. Distribución espectral",
    "3. Cobertura Aki",
    "4. Relación λ–Aki",
    "5. Tipos de transición",
    "6. Explorador de líneas",
    "7. Respuesta científica",
]

ORDEN_REGION = [
    "Rayos X",
    "Ultravioleta",
    "Visible",
    "Infrarrojo",
    "Microondas/Radio",
]


# ---------------------------------------------------------------------------
# Filtros / datos
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def catalogos() -> dict[str, list]:
    elementos = read_sql(
        "SELECT simbolo FROM elemento ORDER BY numero_atomico"
    )["simbolo"].tolist()
    espectros = read_sql(
        "SELECT notacion FROM espectro ORDER BY id_espectro"
    )["notacion"].tolist()
    tipos = read_sql(
        "SELECT codigo FROM tipo_transicion ORDER BY codigo"
    )["codigo"].tolist()
    exactitudes = read_sql(
        "SELECT codigo FROM exactitud ORDER BY orden"
    )["codigo"].tolist()
    regiones = read_sql(
        "SELECT DISTINCT region_espectral FROM v_linea_analisis ORDER BY region_espectral"
    )["region_espectral"].tolist()
    return {
        "elementos": elementos,
        "espectros": espectros,
        "tipos": tipos,
        "exactitudes": exactitudes,
        "regiones": regiones,
    }


def where_clause(filtros: dict) -> tuple[str, dict]:
    clauses = ["1=1"]
    params: dict = {}
    if filtros.get("elementos"):
        clauses.append("elemento IN :elementos")
        params["elementos"] = tuple(filtros["elementos"])
    if filtros.get("espectros"):
        clauses.append("espectro IN :espectros")
        params["espectros"] = tuple(filtros["espectros"])
    if filtros.get("regiones"):
        clauses.append("region_espectral IN :regiones")
        params["regiones"] = tuple(filtros["regiones"])
    if filtros.get("tipos"):
        clauses.append("codigo_tipo_transicion IN :tipos")
        params["tipos"] = tuple(filtros["tipos"])
    if filtros.get("exactitudes"):
        clauses.append("codigo_exactitud IN :exactitudes")
        params["exactitudes"] = tuple(filtros["exactitudes"])
    if filtros.get("solo_aki"):
        clauses.append("aki_s1 IS NOT NULL")
    if filtros.get("alta_exactitud"):
        clauses.append("orden_exactitud IS NOT NULL AND orden_exactitud <= 4")
    return " AND ".join(clauses), params


@st.cache_data(ttl=120, show_spinner="Consultando MySQL...")
def query_vista(where_sql: str, params: dict) -> pd.DataFrame:
    sql = f"""
    SELECT id_linea, elemento, nombre_elemento, espectro, region_espectral,
           longitud_onda_nm, longitud_onda_vacio_nm, aki_s1, log10_aki,
           energia_foton_ev, codigo_tipo_transicion, es_permitida,
           codigo_exactitud, orden_exactitud
    FROM v_linea_analisis
    WHERE {where_sql}
    """
    return read_sql(sql, params)


# ---------------------------------------------------------------------------
# Secciones
# ---------------------------------------------------------------------------

def seccion_inventario(df: pd.DataFrame) -> None:
    st.header("Inventario de la base")
    st.caption("Conteos globales leídos desde MySQL (`optica_y_fotonica`).")

    counts = read_sql(
        """
        SELECT 'elemento' AS tabla, COUNT(*) AS n FROM elemento
        UNION ALL SELECT 'espectro', COUNT(*) FROM espectro
        UNION ALL SELECT 'nivel_energia', COUNT(*) FROM nivel_energia
        UNION ALL SELECT 'linea_espectral', COUNT(*) FROM linea_espectral
        UNION ALL SELECT 'referencia', COUNT(*) FROM referencia
        UNION ALL SELECT 'linea_referencia', COUNT(*) FROM linea_referencia
        UNION ALL SELECT 'nivel_referencia', COUNT(*) FROM nivel_referencia
        """
    )
    rango = read_sql(
        """
        SELECT MIN(longitud_onda_nm) AS lambda_min,
               MAX(longitud_onda_nm) AS lambda_max,
               SUM(aki_s1 IS NOT NULL) AS con_aki,
               COUNT(*) AS total
        FROM linea_espectral
        """
    ).iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    mapa = dict(zip(counts["tabla"], counts["n"]))
    c1.metric("Elementos", f"{mapa.get('elemento', 0):,}")
    c2.metric("Espectros", f"{mapa.get('espectro', 0):,}")
    c3.metric("Niveles", f"{mapa.get('nivel_energia', 0):,}")
    c4.metric("Líneas", f"{mapa.get('linea_espectral', 0):,}")

    c5, c6, c7 = st.columns(3)
    c5.metric("λ mínima (nm)", f"{rango['lambda_min']:.4g}")
    c6.metric("λ máxima (nm)", f"{rango['lambda_max']:.4g}")
    pct = 100 * float(rango["con_aki"]) / float(rango["total"])
    c7.metric("Líneas con Aki", f"{int(rango['con_aki']):,} ({pct:.1f}%)")

    st.subheader("Filas según filtros actuales")
    st.write(f"**{len(df):,}** líneas en la vista filtrada.")
    st.dataframe(counts, hide_index=True, use_container_width=True)


def seccion_distribucion(df: pd.DataFrame) -> None:
    st.header("Distribución por región espectral")
    st.caption(
        "Primera mitad de la pregunta científica: cómo se distribuyen las líneas "
        "tabuladas a lo largo del espectro (todas las líneas, con o sin Aki)."
    )
    if df.empty:
        st.warning("Sin filas con los filtros actuales.")
        return

    dist = (
        df.groupby("region_espectral", as_index=False)
        .size()
        .rename(columns={"size": "lineas"})
    )
    dist["pct"] = 100 * dist["lineas"] / dist["lineas"].sum()
    dist["region_espectral"] = pd.Categorical(
        dist["region_espectral"], categories=ORDEN_REGION, ordered=True
    )
    dist = dist.sort_values("region_espectral")

    fig = px.bar(
        dist,
        x="region_espectral",
        y="lineas",
        text=dist["pct"].map(lambda x: f"{x:.1f}%"),
        labels={"region_espectral": "Región", "lineas": "Número de líneas"},
        title="Líneas por región espectral (filtro activo)",
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(dist, hide_index=True, use_container_width=True)

    visible = dist.loc[dist["region_espectral"] == "Visible", "pct"]
    if len(visible):
        st.info(
            f"Visible ≈ **{float(visible.iloc[0]):.1f}%** del subconjunto filtrado. "
            "IR+UV suelen concentrar la mayoría del catálogo NIST H–Ne."
        )


def seccion_cobertura(df: pd.DataFrame) -> None:
    st.header("Cobertura de Aki por espectro")
    st.caption(
        "Sin cobertura comparable no se puede interpretar la correlación λ–Aki "
        "«en cada elemento»."
    )
    cov = read_sql(
        """
        SELECT e.notacion AS espectro,
               el.simbolo AS elemento,
               COUNT(*) AS lineas,
               SUM(l.aki_s1 IS NOT NULL) AS con_aki,
               ROUND(100 * SUM(l.aki_s1 IS NOT NULL) / COUNT(*), 1) AS pct_aki
        FROM linea_espectral l
        JOIN espectro e ON e.id_espectro = l.id_espectro
        JOIN elemento el ON el.id_elemento = e.id_elemento
        GROUP BY e.notacion, el.simbolo, e.id_espectro
        ORDER BY pct_aki ASC, e.id_espectro
        """
    )
    fig = px.bar(
        cov,
        x="espectro",
        y="pct_aki",
        color="elemento",
        labels={"pct_aki": "% líneas con Aki", "espectro": "Espectro"},
        title="Cobertura de Aki (menor → peor documentado)",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(cov, hide_index=True, use_container_width=True)
    peores = cov.nsmallest(3, "pct_aki")
    st.warning(
        "Espectros con menor cobertura: "
        + ", ".join(f"{r.espectro} ({r.pct_aki}%)" for r in peores.itertuples())
    )


def seccion_lambda_aki(df: pd.DataFrame) -> None:
    st.header("Relación longitud de onda – Aki")
    st.caption(
        "Segunda mitad de la pregunta: relación en escala log-log "
        r"($\log_{10}\lambda$ vs $\log_{10}A_{ki}$), por elemento."
    )
    sub = df.dropna(subset=["longitud_onda_nm", "aki_s1", "log10_aki"]).copy()
    sub = sub[(sub["longitud_onda_nm"] > 0) & (sub["aki_s1"] > 0)]
    if sub.empty:
        st.warning("No hay filas con λ y Aki bajo los filtros actuales.")
        return

    sub["log10_lambda"] = np.log10(sub["longitud_onda_nm"])

    # Métricas globales
    r_lin = float(sub["longitud_onda_nm"].corr(sub["aki_s1"], method="pearson"))
    r_log = float(sub["log10_lambda"].corr(sub["log10_aki"], method="pearson"))
    rho = float(sub["log10_lambda"].corr(sub["log10_aki"], method="spearman"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("n (con Aki)", f"{len(sub):,}")
    c2.metric("Pearson λ–Aki (lineal)", f"{r_lin:.4f}")
    c3.metric("Pearson log-log", f"{r_log:.4f}")
    c4.metric("Spearman log-log", f"{rho:.4f}")

    fig = px.scatter(
        sub.sample(n=min(len(sub), 4000), random_state=42),
        x="longitud_onda_nm",
        y="aki_s1",
        color="elemento",
        log_x=True,
        log_y=True,
        opacity=0.45,
        labels={
            "longitud_onda_nm": "λ (nm, log)",
            "aki_s1": "Aki (s⁻¹, log)",
        },
        title="Scatter log-log λ vs Aki (muestra ≤ 4000 puntos)",
        hover_data=["espectro", "region_espectral", "codigo_exactitud"],
    )
    st.plotly_chart(fig, use_container_width=True)

    filas = []
    for el, g in sub.groupby("elemento"):
        if len(g) < 5:
            continue
        lx = np.log10(g["longitud_onda_nm"])
        pr = float(lx.corr(g["log10_aki"], method="pearson"))
        sr = float(lx.corr(g["log10_aki"], method="spearman"))
        filas.append(
            {
                "elemento": el,
                "n": len(g),
                "pearson_loglog": pr,
                "spearman_loglog": sr,
            }
        )
    por_el = pd.DataFrame(filas).sort_values("pearson_loglog")
    st.subheader("Correlación log-log por elemento")
    st.dataframe(por_el, hide_index=True, use_container_width=True)
    if not por_el.empty:
        neg = (por_el["pearson_loglog"] < 0).sum()
        st.success(
            f"**{neg}/{len(por_el)}** elementos con Pearson log-log negativo "
            "en el subconjunto filtrado."
        )


def seccion_tipos(df: pd.DataFrame) -> None:
    st.header("Tipos de transición")
    st.caption(
        "Aki bajo no implica error: E2/M1 son prohibidas y viven órdenes de "
        "magnitud por debajo de E1."
    )
    sub = df.dropna(subset=["log10_aki"]).copy()
    if sub.empty:
        st.warning("Sin Aki en el filtro actual.")
        return

    resumen = (
        sub.groupby("codigo_tipo_transicion")
        .agg(
            n=("log10_aki", "size"),
            log10_aki_mediana=("log10_aki", "median"),
            permitida=("es_permitida", "first"),
        )
        .reset_index()
        .sort_values("log10_aki_mediana", ascending=False)
    )
    fig = px.box(
        sub,
        x="codigo_tipo_transicion",
        y="log10_aki",
        color="es_permitida",
        labels={
            "codigo_tipo_transicion": "Tipo",
            "log10_aki": "log₁₀(Aki)",
            "es_permitida": "Permitida",
        },
        title="Distribución de log₁₀(Aki) por tipo de transición",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(resumen, hide_index=True, use_container_width=True)


def seccion_explorador(df: pd.DataFrame) -> None:
    st.header("Explorador de líneas")
    st.caption("Tabla filtrable (vista `v_linea_analisis` + detalle de niveles).")

    max_rows = st.slider("Máximo de filas a mostrar", 50, 2000, 300, 50)
    if df.empty:
        st.warning("Sin filas.")
        return

    ids = tuple(df["id_linea"].head(max_rows).astype(int).tolist())
    if not ids:
        st.warning("Sin IDs.")
        return

    detalle = read_sql(
        """
        SELECT l.id_linea, el.simbolo AS elemento, e.notacion AS espectro,
               l.longitud_onda_nm, l.aki_s1, l.codigo_tipo_transicion,
               l.codigo_exactitud, l.medio, l.longitud_onda_origen,
               ni.configuracion AS config_inf, ni.termino AS term_inf,
               ns.configuracion AS config_sup, ns.termino AS term_sup
        FROM linea_espectral l
        JOIN espectro e ON e.id_espectro = l.id_espectro
        JOIN elemento el ON el.id_elemento = e.id_elemento
        LEFT JOIN nivel_energia ni ON ni.id_nivel = l.id_nivel_inferior
        LEFT JOIN nivel_energia ns ON ns.id_nivel = l.id_nivel_superior
        WHERE l.id_linea IN :ids
        ORDER BY l.longitud_onda_nm
        """,
        {"ids": ids},
    )
    st.dataframe(detalle, hide_index=True, use_container_width=True)
    st.download_button(
        "Descargar CSV (filas mostradas)",
        detalle.to_csv(index=False).encode("utf-8"),
        file_name="lineas_filtradas.csv",
        mime="text/csv",
    )


def seccion_respuesta(df: pd.DataFrame) -> None:
    st.header("Respuesta científica")
    st.markdown(
        """
> **Pregunta:** ¿Cómo se distribuyen las líneas espectrales de H a Ne a lo largo
> del espectro electromagnético, y qué relación existe entre el coeficiente de
> Einstein Aki y la longitud de onda de emisión **en cada elemento**?
"""
    )

    dist = read_sql(
        """
        SELECT region_espectral, COUNT(*) AS lineas
        FROM v_linea_analisis
        GROUP BY region_espectral
        """
    )
    total = int(dist["lineas"].sum())
    dist["pct"] = 100 * dist["lineas"] / total

    sub = read_sql(
        """
        SELECT elemento, longitud_onda_nm, log10_aki
        FROM v_linea_analisis
        WHERE aki_s1 IS NOT NULL AND longitud_onda_nm > 0
        """
    )
    sub["log10_lambda"] = np.log10(sub["longitud_onda_nm"])
    r_log = float(sub["log10_lambda"].corr(sub["log10_aki"], method="pearson"))
    rho = float(sub["log10_lambda"].corr(sub["log10_aki"], method="spearman"))

    por_el = []
    for el, g in sub.groupby("elemento"):
        if len(g) < 5:
            continue
        pr = float(g["log10_lambda"].corr(g["log10_aki"], method="pearson"))
        por_el.append((el, pr, len(g)))
    neg = sum(1 for _, pr, _ in por_el if pr < 0)

    alta = read_sql(
        """
        SELECT longitud_onda_nm, log10_aki
        FROM v_linea_analisis
        WHERE aki_s1 IS NOT NULL AND orden_exactitud IS NOT NULL
          AND orden_exactitud <= 4 AND longitud_onda_nm > 0
        """
    )
    if len(alta) >= 5:
        r_alta = float(
            np.log10(alta["longitud_onda_nm"]).corr(
                alta["log10_aki"], method="pearson"
            )
        )
    else:
        r_alta = float("nan")

    st.subheader("1) Distribución espectral (todas las líneas)")
    st.dataframe(
        dist.sort_values("lineas", ascending=False),
        hide_index=True,
        use_container_width=True,
    )
    vis = dist.loc[dist["region_espectral"] == "Visible", "pct"]
    st.markdown(
        f"- Catálogo completo: **{total:,}** líneas.\n"
        f"- Visible ≈ **{float(vis.iloc[0]) if len(vis) else 0:.1f}%**; "
        "la mayoría tabulado está fuera del visible (IR/UV).\n"
        "- Esto cuenta **transiciones distintas documentadas**, no potencia luminosa."
    )

    st.subheader("2) Relación λ–Aki (solo con Aki medido)")
    st.markdown(
        f"- Muestra con Aki: **{len(sub):,}** líneas.\n"
        f"- Pearson log-log global: **{r_log:.3f}**; Spearman: **{rho:.3f}**.\n"
        f"- En lineal, la correlación colapsa (~0): hay que usar escala log-log.\n"
        f"- **{neg}/{len(por_el)}** elementos con Pearson log-log negativo.\n"
        f"- Subconjunto alta exactitud (AAA–A): Pearson log-log **{r_alta:.3f}** "
        f"(n={len(alta):,}).\n"
        "- Aki es tasa de Einstein (s⁻¹), no una probabilidad en [0, 1].\n"
        "- Las transiciones prohibidas (E2/M1) tienen Aki típico mucho menor; "
        "no se eliminan como «outliers»."
    )

    st.subheader("Cierre")
    st.success(
        "Las líneas H–Ne del NIST se concentran fuera del visible; "
        "en escala log-log aparece una relación negativa entre λ y Aki, "
        "consistente en todos los elementos, con fuerza modulada por la "
        "cobertura experimental de Aki en cada espectro."
    )
    st.caption(
        "Métricas recalculadas en vivo desde MySQL. Narrativa alineada al "
        "notebook 05 / docs/05_consultas_analisis_cientifico.md."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.title("Óptica y Fotónica — NIST ASD")
    st.caption("Catálogo atómico H–Ne · MySQL · Streamlit")

    ok, detail = ping()
    if not ok:
        st.error(f"No hay conexión a MySQL: {detail}")
        st.stop()

    cats = catalogos()
    cfg = mysql_config()

    with st.sidebar:
        st.markdown("### Navegación analítica")
        seccion = st.radio("Sección", SECCIONES, index=0)
        st.markdown("---")
        st.markdown("### Filtros globales")
        elementos = st.multiselect("Elemento", cats["elementos"], default=[])
        espectros = st.multiselect("Espectro", cats["espectros"], default=[])
        regiones = st.multiselect("Región", cats["regiones"], default=[])
        tipos = st.multiselect("Tipo transición", cats["tipos"], default=[])
        exactitudes = st.multiselect("Exactitud Acc", cats["exactitudes"], default=[])
        solo_aki = st.checkbox("Solo líneas con Aki", value=False)
        alta_ex = st.checkbox("Solo exactitud AAA–A", value=False)
        st.markdown("---")
        st.caption(f"DB `{cfg['database']}` @ `{cfg['host']}`")
        st.success(detail)
        st.markdown("Creado por: **Andres David Perez**")

    filtros = {
        "elementos": elementos or None,
        "espectros": espectros or None,
        "regiones": regiones or None,
        "tipos": tipos or None,
        "exactitudes": exactitudes or None,
        "solo_aki": solo_aki,
        "alta_exactitud": alta_ex,
    }
    # Limpiar None vacíos para cache key estable
    filtros = {k: v for k, v in filtros.items() if v not in (None, False, [])}
    if solo_aki:
        filtros["solo_aki"] = True
    if alta_ex:
        filtros["alta_exactitud"] = True

    where_sql, params = where_clause(
        {
            "elementos": elementos,
            "espectros": espectros,
            "regiones": regiones,
            "tipos": tipos,
            "exactitudes": exactitudes,
            "solo_aki": solo_aki,
            "alta_exactitud": alta_ex,
        }
    )
    df = query_vista(where_sql, params)

    if seccion.startswith("1."):
        seccion_inventario(df)
    elif seccion.startswith("2."):
        seccion_distribucion(df)
    elif seccion.startswith("3."):
        seccion_cobertura(df)
    elif seccion.startswith("4."):
        seccion_lambda_aki(df)
    elif seccion.startswith("5."):
        seccion_tipos(df)
    elif seccion.startswith("6."):
        seccion_explorador(df)
    else:
        seccion_respuesta(df)


if __name__ == "__main__":
    main()

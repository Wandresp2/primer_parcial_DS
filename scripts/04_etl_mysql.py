#!/usr/bin/env python3
"""
Fase 4 — ETL MySQL (DDL sql/schema.sql + DML desde data/procesados/).

Prerrequisitos:
  - data/procesados/lineas_limpias.csv y niveles_limpios.csv (Fase 3)
  - sql/schema.sql aplicado (este script puede aplicarlo si APPLY_SCHEMA=1)

No crea DDL propio: solo vacía y carga las 9 tablas.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import text

ROOT = Path(__file__).resolve().parent.parent
DIR_PROCESADOS = ROOT / "data" / "procesados"
SCHEMA_SQL = ROOT / "sql" / "schema.sql"

RUTA_LINEAS = DIR_PROCESADOS / "lineas_limpias.csv"
RUTA_NIVELES = DIR_PROCESADOS / "niveles_limpios.csv"

DB_USER = os.environ.get("MYSQL_USER", "root")
DB_PASS = os.environ.get(
    "MYSQL_PASSWORD", os.environ.get("MYSQL_ROOT_PASSWORD", "root")
)
DB_HOST = os.environ.get("MYSQL_HOST", "mysql")
DB_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
DB_NAME = os.environ.get("MYSQL_DATABASE", "optica_y_fotonica")
APPLY_SCHEMA = os.environ.get("APPLY_SCHEMA", "1") not in ("0", "false", "False")

TABLAS_ESPERADAS = [
    "elemento",
    "tipo_transicion",
    "exactitud",
    "referencia",
    "espectro",
    "nivel_energia",
    "linea_espectral",
    "linea_referencia",
    "nivel_referencia",
]

ORDEN_CARGA = list(TABLAS_ESPERADAS)

NOMBRES = {
    "H": "Hidrogeno",
    "He": "Helio",
    "Li": "Litio",
    "Be": "Berilio",
    "B": "Boro",
    "C": "Carbono",
    "N": "Nitrogeno",
    "O": "Oxigeno",
    "F": "Fluor",
    "Ne": "Neon",
}
NUM_ATOMICO = {
    "H": 1,
    "He": 2,
    "Li": 3,
    "Be": 4,
    "B": 5,
    "C": 6,
    "N": 7,
    "O": 8,
    "F": 9,
    "Ne": 10,
}

TIPOS = {
    "E1": ("Dipolo electrico", True, "Transicion permitida, la mas comun y brillante"),
    "E2": ("Cuadrupolo electrico", False, "Transicion prohibida"),
    "M1": ("Dipolo magnetico", False, "Transicion prohibida"),
    "M2": ("Cuadrupolo magnetico", False, "Transicion prohibida"),
    "UT": ("Sin clasificar", False, "Tipo no determinado por el NIST"),
}

ESCALA_ACC = ["AAA", "AA", "A+", "A", "B+", "B", "B'", "C+", "C", "C'", "D+", "D", "E"]
TOLERANCIA = [0.3, 1, 2, 3, 7, 10, 10, 18, 25, 25, 40, 50, 50]

ESPERADOS = {
    "elemento": 10,
    "tipo_transicion": 5,
    "exactitud": 13,
    "espectro": 18,
    "nivel_energia": 5752,
    "linea_espectral": 18288,
}


def wait_mysql(max_attempts: int = 40, sleep_s: float = 3.0) -> None:
    url = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/"
    engine = sa.create_engine(url, pool_pre_ping=True)
    last: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"MySQL disponible en {DB_HOST}:{DB_PORT} (intento {attempt})")
            engine.dispose()
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"  Esperando MySQL... ({attempt}/{max_attempts})")
            time.sleep(sleep_s)
    raise RuntimeError(f"MySQL no respondio a tiempo: {last}")


def apply_schema() -> None:
    if not SCHEMA_SQL.is_file():
        raise FileNotFoundError(f"No existe {SCHEMA_SQL}")
    print(f"Aplicando schema: {SCHEMA_SQL}")
    cmd = [
        "mysql",
        f"-h{DB_HOST}",
        f"-P{DB_PORT}",
        f"-u{DB_USER}",
        f"-p{DB_PASS}",
        "--skip-ssl",
    ]
    with SCHEMA_SQL.open("rb") as fh:
        proc = subprocess.run(cmd, stdin=fh, capture_output=True)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"Fallo al aplicar schema.sql:\n{err}")
    print("Schema aplicado OK")


def connect_db() -> sa.Engine:
    url = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = sa.create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        version = conn.execute(text("SELECT VERSION()")).scalar()
        db = conn.execute(text("SELECT DATABASE()")).scalar()
    print(f"Conectado a MySQL {version} | base={db}")
    inspector = sa.inspect(engine)
    existentes = set(inspector.get_table_names())
    faltan = [t for t in TABLAS_ESPERADAS if t not in existentes]
    if faltan:
        raise RuntimeError(f"Faltan tablas tras schema: {faltan}")
    return engine


def expandir_referencias(serie: pd.Series, tipo_fuente: str) -> list[tuple[str, str]]:
    filas: list[tuple[str, str]] = []
    for v in serie.dropna().astype(str):
        for token in v.split(","):
            token = token.strip()
            if token:
                filas.append((token, tipo_fuente))
    return filas


def construir_puente_lineas(
    df: pd.DataFrame, col_id: str, col_ref: str, rol: str
) -> pd.DataFrame:
    filas = []
    sub = df[[col_id, col_ref]].dropna(subset=[col_ref])
    for id_linea, refs_txt in zip(sub[col_id], sub[col_ref].astype(str)):
        for token in refs_txt.split(","):
            token = token.strip()
            if token:
                filas.append((id_linea, token, rol))
    return pd.DataFrame(filas, columns=["id_linea", "codigo_referencia", "rol"])


def construir_puente_niveles(df: pd.DataFrame, col_id: str, col_ref: str) -> pd.DataFrame:
    filas = []
    sub = df[[col_id, col_ref]].dropna(subset=[col_ref])
    for id_nivel, refs_txt in zip(sub[col_id], sub[col_ref].astype(str)):
        for token in refs_txt.split(","):
            token = token.strip()
            if token:
                filas.append((id_nivel, token))
    return pd.DataFrame(filas, columns=["id_nivel", "codigo_referencia"])


def nan_to_none(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    return out.astype(object).where(pd.notnull(out), None)


def build_tables(df_lineas: pd.DataFrame, df_niveles: pd.DataFrame) -> dict[str, pd.DataFrame]:
    simbolos = sorted(df_lineas["elemento"].dropna().unique(), key=lambda s: NUM_ATOMICO[s])
    t_elemento = pd.DataFrame(
        {
            "id_elemento": range(1, len(simbolos) + 1),
            "simbolo": simbolos,
            "nombre": [NOMBRES[s] for s in simbolos],
            "numero_atomico": [NUM_ATOMICO[s] for s in simbolos],
        }
    )
    map_elemento = dict(zip(t_elemento["simbolo"], t_elemento["id_elemento"]))

    t_tipo_transicion = pd.DataFrame(
        [
            {"codigo": c, "nombre": n, "es_permitida": p, "descripcion": d}
            for c, (n, p, d) in TIPOS.items()
        ]
    )

    t_exactitud = pd.DataFrame(
        {
            "codigo": ESCALA_ACC,
            "orden": range(1, len(ESCALA_ACC) + 1),
            "tolerancia_max_pct": TOLERANCIA,
            "descripcion": [f"Incertidumbre estimada hasta {t}%" for t in TOLERANCIA],
        }
    )

    refs = (
        expandir_referencias(df_lineas["ref_probabilidad"], "probabilidad")
        + expandir_referencias(df_lineas["ref_longitud_onda"], "linea")
        + expandir_referencias(df_niveles["referencia"], "nivel")
    )
    t_referencia = (
        pd.DataFrame(refs, columns=["codigo", "tipo_fuente"])
        .drop_duplicates(subset="codigo", keep="first")
        .reset_index(drop=True)
    )

    espectros = sorted(
        df_lineas["espectro"].dropna().unique(),
        key=lambda e: (NUM_ATOMICO[e.split()[0]], e.split()[1]),
    )
    t_espectro = pd.DataFrame(
        {
            "id_espectro": range(1, len(espectros) + 1),
            "notacion": espectros,
        }
    )
    t_espectro["id_elemento"] = t_espectro["notacion"].str.split().str[0].map(map_elemento)
    t_espectro["estado_ionizacion"] = (
        t_espectro["notacion"].str.split().str[1].map({"I": 1, "II": 2})
    )
    t_espectro = t_espectro[
        ["id_espectro", "id_elemento", "estado_ionizacion", "notacion"]
    ]
    map_espectro = dict(zip(t_espectro["notacion"], t_espectro["id_espectro"]))

    t_nivel_energia = df_niveles.copy()
    t_nivel_energia["id_espectro"] = t_nivel_energia["espectro"].map(map_espectro)
    t_nivel_energia = t_nivel_energia[
        [
            "id_nivel",
            "id_espectro",
            "configuracion",
            "termino",
            "j_valor",
            "j_texto",
            "j_resuelto",
            "g",
            "energia_ev",
            "energia_interpolada",
            "incertidumbre_ev",
        ]
    ].dropna(subset=["id_nivel"])
    t_nivel_energia["g"] = t_nivel_energia["g"].astype("Int64")
    assert t_nivel_energia["id_nivel"].is_unique

    niveles_validos = set(t_nivel_energia["id_nivel"])
    t_linea = df_lineas.copy()
    t_linea["id_espectro"] = t_linea["espectro"].map(map_espectro)
    t_linea["codigo_tipo_transicion"] = t_linea["tipo_transicion"]
    t_linea["codigo_exactitud"] = t_linea["exactitud"].astype(object).where(
        t_linea["exactitud"].notna(), None
    )
    t_linea.loc[
        ~t_linea["id_nivel_inferior"].isin(niveles_validos), "id_nivel_inferior"
    ] = None
    t_linea.loc[
        ~t_linea["id_nivel_superior"].isin(niveles_validos), "id_nivel_superior"
    ] = None

    columnas_linea = [
        "id_linea",
        "id_espectro",
        "id_nivel_inferior",
        "id_nivel_superior",
        "codigo_tipo_transicion",
        "codigo_exactitud",
        "longitud_onda_nm",
        "longitud_onda_origen",
        "medio",
        "longitud_onda_obs_nm",
        "longitud_onda_ritz_nm",
        "ritz_es_limite",
        "incertidumbre_obs_nm",
        "incertidumbre_ritz_nm",
        "aki_s1",
        "fuerza_oscilador_fik",
        "log_gf",
        "intensidad_valor",
        "intensidad_bandera",
        "energia_inferior_cm1",
        "energia_superior_cm1",
        "energia_inferior_interpolada",
        "energia_superior_interpolada",
        "energia_inferior_origen_desconocido",
        "energia_superior_origen_desconocido",
        "medicion_repetida",
    ]
    t_linea_espectral = t_linea[columnas_linea].copy()
    t_linea_espectral["tp_ref"] = t_linea["ref_probabilidad"].values
    t_linea_espectral["line_ref"] = t_linea["ref_longitud_onda"].values
    assert t_linea_espectral["longitud_onda_nm"].notna().all()

    t_linea_referencia = pd.concat(
        [
            construir_puente_lineas(t_linea_espectral, "id_linea", "tp_ref", "probabilidad"),
            construir_puente_lineas(t_linea_espectral, "id_linea", "line_ref", "longitud_onda"),
        ],
        ignore_index=True,
    ).drop_duplicates()
    t_linea_referencia = t_linea_referencia[
        t_linea_referencia["codigo_referencia"].isin(t_referencia["codigo"])
    ].reset_index(drop=True)
    t_linea_espectral = t_linea_espectral.drop(columns=["tp_ref", "line_ref"])

    t_nivel_referencia = construir_puente_niveles(
        df_niveles, "id_nivel", "referencia"
    ).drop_duplicates()
    t_nivel_referencia = t_nivel_referencia[
        t_nivel_referencia["codigo_referencia"].isin(t_referencia["codigo"])
        & t_nivel_referencia["id_nivel"].isin(t_nivel_energia["id_nivel"])
    ].reset_index(drop=True)

    tablas = {
        "elemento": t_elemento,
        "tipo_transicion": t_tipo_transicion,
        "exactitud": t_exactitud,
        "referencia": t_referencia,
        "espectro": t_espectro,
        "nivel_energia": t_nivel_energia,
        "linea_espectral": t_linea_espectral,
        "linea_referencia": t_linea_referencia,
        "nivel_referencia": t_nivel_referencia,
    }

    print("=== Tablas a cargar ===")
    for nombre, df in tablas.items():
        print(f"  {nombre:<20} {len(df):>8,} filas x {df.shape[1]:>2} cols")

    # Integridad previa
    assert (
        ~t_espectro["id_elemento"].isin(t_elemento["id_elemento"])
    ).sum() == 0
    assert (
        ~t_nivel_energia["id_espectro"].isin(t_espectro["id_espectro"])
    ).sum() == 0
    assert (
        ~t_linea_espectral["id_espectro"].isin(t_espectro["id_espectro"])
    ).sum() == 0
    assert (
        t_linea_espectral["id_nivel_inferior"].notna()
        & ~t_linea_espectral["id_nivel_inferior"].isin(t_nivel_energia["id_nivel"])
    ).sum() == 0
    assert (
        t_linea_espectral["id_nivel_superior"].notna()
        & ~t_linea_espectral["id_nivel_superior"].isin(t_nivel_energia["id_nivel"])
    ).sum() == 0
    print("Integridad previa OK (0 FK huerfanas)")
    return tablas


def load_tables(engine: sa.Engine, tablas: dict[str, pd.DataFrame]) -> None:
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for tabla in reversed(ORDEN_CARGA):
            conn.execute(text(f"TRUNCATE TABLE {tabla}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    print("Tablas vaciadas")

    inicio = time.time()
    with engine.begin() as conn:
        for tabla in ORDEN_CARGA:
            df = nan_to_none(tablas[tabla])
            df.to_sql(
                tabla,
                con=conn,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=2000,
            )
            print(f"  Cargada '{tabla}': {len(tablas[tabla]):,} filas")
    print(f"Carga completa en {time.time() - inicio:.1f}s")


def verify(engine: sa.Engine, tablas: dict[str, pd.DataFrame]) -> None:
    print("=== Conteos MySQL vs Python ===")
    with engine.connect() as conn:
        for tabla in ORDEN_CARGA:
            n_bd = conn.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()
            n_py = len(tablas[tabla])
            marca = "OK" if n_bd == n_py else "DIFF"
            print(f"  [{marca}] {tabla:<20} MySQL={n_bd:>8,}  Python={n_py:>8,}")
            if n_bd != n_py:
                raise RuntimeError(f"Discrepancia en {tabla}")
            if tabla in ESPERADOS and n_bd != ESPERADOS[tabla]:
                raise RuntimeError(
                    f"{tabla}: esperado {ESPERADOS[tabla]}, got {n_bd}"
                )

    consultas = {
        "espectro -> elemento": (
            "SELECT COUNT(*) FROM espectro e "
            "LEFT JOIN elemento el ON e.id_elemento=el.id_elemento "
            "WHERE el.id_elemento IS NULL"
        ),
        "nivel -> espectro": (
            "SELECT COUNT(*) FROM nivel_energia n "
            "LEFT JOIN espectro e ON n.id_espectro=e.id_espectro "
            "WHERE e.id_espectro IS NULL"
        ),
        "linea -> nivel_inf": (
            "SELECT COUNT(*) FROM linea_espectral l "
            "LEFT JOIN nivel_energia n ON l.id_nivel_inferior=n.id_nivel "
            "WHERE l.id_nivel_inferior IS NOT NULL AND n.id_nivel IS NULL"
        ),
        "linea -> nivel_sup": (
            "SELECT COUNT(*) FROM linea_espectral l "
            "LEFT JOIN nivel_energia n ON l.id_nivel_superior=n.id_nivel "
            "WHERE l.id_nivel_superior IS NOT NULL AND n.id_nivel IS NULL"
        ),
    }
    print("=== FK huerfanas en MySQL ===")
    with engine.connect() as conn:
        for etiqueta, sql in consultas.items():
            n = conn.execute(text(sql)).scalar()
            print(f"  [{('OK' if n == 0 else 'FAIL')}] {etiqueta}: {n}")
            if n != 0:
                raise RuntimeError(f"FK huerfanas en {etiqueta}: {n}")

    with engine.connect() as conn:
        n_vista = conn.execute(
            text("SELECT COUNT(*) FROM v_linea_analisis")
        ).scalar()
    print(f"Vista v_linea_analisis: {n_vista:,} filas")
    if n_vista != 18288:
        raise RuntimeError(f"Vista esperaba 18288 filas, got {n_vista}")


def export_tabla_csvs(tablas: dict[str, pd.DataFrame]) -> None:
    DIR_PROCESADOS.mkdir(parents=True, exist_ok=True)
    for nombre, df in tablas.items():
        path = DIR_PROCESADOS / f"tabla_{nombre}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
    print(f"Exportados tabla_*.csv en {DIR_PROCESADOS}")


def main() -> int:
    print("Fase 4 — ETL MySQL")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Host={DB_HOST} DB={DB_NAME} APPLY_SCHEMA={APPLY_SCHEMA}")

    if not RUTA_LINEAS.is_file() or not RUTA_NIVELES.is_file():
        print(
            f"ERROR: faltan CSV procesados.\n  {RUTA_LINEAS}\n  {RUTA_NIVELES}",
            file=sys.stderr,
        )
        return 1

    try:
        wait_mysql()
        if APPLY_SCHEMA:
            apply_schema()
        engine = connect_db()

        df_lineas = pd.read_csv(RUTA_LINEAS, low_memory=False)
        df_niveles = pd.read_csv(RUTA_NIVELES, low_memory=False)
        # IDs de nivel como texto (ceros a la izquierda)
        for col in ("id_nivel_inferior", "id_nivel_superior"):
            if col in df_lineas.columns:
                df_lineas[col] = df_lineas[col].astype("string")
        df_niveles["id_nivel"] = df_niveles["id_nivel"].astype("string")

        print(f"Leidas lineas={len(df_lineas):,} niveles={len(df_niveles):,}")
        tablas = build_tables(df_lineas, df_niveles)
        load_tables(engine, tablas)
        verify(engine, tablas)
        export_tabla_csvs(tablas)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR FATAL: {exc}", file=sys.stderr)
        return 1

    total = sum(len(df) for df in tablas.values())
    print("=" * 60)
    print(f"ETL COMPLETO — {total:,} filas en MySQL")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

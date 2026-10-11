#!/usr/bin/env python3
"""
Fase 2 — Descarga de datos iniciales desde NIST ASD.

Descarga NIST ASD (equivalente histórico al notebook 01):
  - Parte A: líneas espectrales (lines1.pl) → data/originales/nist_lines_H_Ne_original.csv
  - Parte B: niveles (energy1.pl, 18 espectros) → data/originales/niveles/ + consolidado

Los CSV se guardan crudos (sin modificar el texto del NIST).
Exit code ≠ 0 si falla la descarga o faltan espectros.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DIR_ORIGINALES = ROOT / "data" / "originales"
DIR_NIVELES = DIR_ORIGINALES / "niveles"

URL_LINES = "http://physics.nist.gov/cgi-bin/ASD/lines1.pl"
URL_LEVELS = "http://physics.nist.gov/cgi-bin/ASD/energy1.pl"

ESPECTRA_STR = (
    "H I;He I;Li I;Li II;Be I;Be II;B I;B II;C I;C II;"
    "N I;N II;O I;O II;F I;F II;Ne I;Ne II"
)
ESPECTRA_LIST = [
    "H I",
    "He I",
    "Li I",
    "Li II",
    "Be I",
    "Be II",
    "B I",
    "B II",
    "C I",
    "C II",
    "N I",
    "N II",
    "O I",
    "O II",
    "F I",
    "F II",
    "Ne I",
    "Ne II",
]

PARAMETROS_LINES = {
    "spectra": ESPECTRA_STR,
    "low_w": "",
    "upp_w": "",
    "unit": 1,
    "format": 2,
    "line_out": 0,
    "en_unit": 0,
    "output": 0,
    "show_obs_wl": 1,
    "show_calc_wl": 1,
    "unc_out": 1,
    "order_out": 0,
    "show_av": 2,
    "A_out": 0,
    "intens_out": "on",
    "allowed_out": 1,
    "forbid_out": 1,
    "conf_out": "on",
    "term_out": "on",
    "enrg_out": "on",
    "J_out": "on",
    # Campos que el notebook/limpieza esperan (nombres actuales del formulario).
    "g_out": "on",
    "f_out": "on",
    "loggf_out": "on",
    "ids_out": "on",
    "bibrefs": 1,
    "submit": "Retrieve Data",
    "de": 0,
    "plot_out": 0,
    "I_scale_type": 1,
    "page_size": 15,
    "tsb_value": 0,
    "min_str": "",
    "max_str": "",
    "max_low_enrg": "",
    "max_upp_enrg": "",
    "min_accur": "",
    "min_intens": "",
}

# Nombres del formulario actual NIST ASD Levels (energy1.pl).
# Los show_* del notebook 01 ya no son válidos → "Unknown parameter".
PARAMETROS_LEVELS_BASE = {
    "units": "1",
    "format": "2",
    "output": "0",
    "page_size": "15",
    "multiplet_ordered": "0",
    "conf_out": "on",
    "term_out": "on",
    "j_out": "on",
    "g_out": "on",
    "unc_out": "1",
    "ids_out": "on",
    "lande_out": "on",
    "perc_out": "on",
    "biblio": "1",
    "level_out": "on",
    "submit": "Retrieve Data",
}

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) OpticaPipeline/1.0",
}

MAX_RETRIES = 3
RETRY_SLEEP_S = 5
LEVEL_PAUSE_S = 1
LINES_TIMEOUT_S = 120
LEVELS_TIMEOUT_S = 60


def _es_csv_util(texto: str) -> bool:
    head = texto.lstrip()[:2000]
    if not head or head.startswith("<!") or head.startswith("<html"):
        return False
    if "Unknown parameter" in texto or "Cloudflare" in texto:
        return False
    return "," in head.split("\n", 1)[0]


def _http_get(url: str, params: dict, timeout: int, label: str) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  GET {label} (intento {attempt}/{MAX_RETRIES})...")
            response = requests.get(
                url, params=params, headers=REQUEST_HEADERS, timeout=timeout
            )
            if response.status_code == 200 and _es_csv_util(response.text):
                return response
            snip = response.text.lstrip()[:120].replace("\n", " ")
            print(
                f"  Respuesta no usable (HTTP {response.status_code}, "
                f"{len(response.text)} chars, head={snip!r}). "
                f"Reintento en {RETRY_SLEEP_S}s..."
            )
        except requests.RequestException as exc:
            last_error = exc
            print(f"  Error de red: {exc}. Reintento en {RETRY_SLEEP_S}s...")
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_SLEEP_S)
    raise RuntimeError(f"Fallo al descargar {label} tras {MAX_RETRIES} intentos: {last_error}")


def parsear_respuesta_nist(texto_respuesta: str, nombre_espectro: str) -> pd.DataFrame | None:
    try:
        lineas = texto_respuesta.split("\n")
        lineas_utiles = [
            linea for linea in lineas if linea.strip() and not linea.startswith("---")
        ]
        texto_limpio = "\n".join(lineas_utiles)
        df = pd.read_csv(
            StringIO(texto_limpio),
            sep=",",
            low_memory=False,
            on_bad_lines="warn",
        )
        df.insert(0, "espectro", nombre_espectro)
        return df
    except Exception as exc:  # noqa: BLE001
        print(f"  ERROR al parsear {nombre_espectro}: {exc}")
        return None


def asegurar_carpetas() -> None:
    DIR_ORIGINALES.mkdir(parents=True, exist_ok=True)
    DIR_NIVELES.mkdir(parents=True, exist_ok=True)
    print(f"Carpetas listas:\n  {DIR_ORIGINALES}\n  {DIR_NIVELES}")


def descargar_lineas() -> Path:
    print("\n" + "=" * 60)
    print("PARTE A — Líneas espectrales (lines1.pl)")
    print("=" * 60)
    print(f"Espectros: {ESPECTRA_STR}")
    print(f"Total: {len(ESPECTRA_LIST)}")

    response = _http_get(
        URL_LINES, PARAMETROS_LINES, LINES_TIMEOUT_S, "líneas espectrales H–Ne"
    )
    out_path = DIR_ORIGINALES / "nist_lines_H_Ne_original.csv"
    out_path.write_text(response.text, encoding="utf-8")

    print(f"Guardado: {out_path} ({out_path.stat().st_size:,} bytes)")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return out_path


def descargar_niveles() -> Path:
    print("\n" + "=" * 60)
    print("PARTE B — Niveles de energía (energy1.pl)")
    print("=" * 60)

    lista_dfs: list[pd.DataFrame] = []
    registro: list[dict] = []

    for i, espectro in enumerate(ESPECTRA_LIST, start=1):
        print(f"\n[{i:02d}/{len(ESPECTRA_LIST)}] {espectro}")
        params = PARAMETROS_LEVELS_BASE.copy()
        params["spectrum"] = espectro

        try:
            response = _http_get(
                URL_LEVELS, params, LEVELS_TIMEOUT_S, f"niveles {espectro}"
            )
        except RuntimeError as exc:
            print(f"  FALLO: {exc}")
            registro.append({"espectro": espectro, "estado": "ERROR", "filas": 0})
            continue

        nombre_archivo = DIR_NIVELES / f"nist_levels_{espectro.replace(' ', '_')}_original.csv"
        nombre_archivo.write_text(response.text, encoding="utf-8")

        df = parsear_respuesta_nist(response.text, espectro)
        if df is not None and len(df) > 0:
            lista_dfs.append(df)
            print(f"  OK — {len(df):,} niveles → {nombre_archivo.name}")
            registro.append({"espectro": espectro, "estado": "OK", "filas": len(df)})
        else:
            print("  VACIO — sin filas parseables")
            registro.append({"espectro": espectro, "estado": "VACIO", "filas": 0})

        if i < len(ESPECTRA_LIST):
            time.sleep(LEVEL_PAUSE_S)

    df_registro = pd.DataFrame(registro)
    print("\nResumen niveles:")
    print(df_registro.to_string(index=False))

    ok_count = int((df_registro["estado"] == "OK").sum())
    if ok_count != len(ESPECTRA_LIST) or not lista_dfs:
        raise RuntimeError(
            f"Solo {ok_count}/{len(ESPECTRA_LIST)} espectros OK. Abortando consolidado."
        )

    df_levels = pd.concat(lista_dfs, ignore_index=True)
    # Sanity: el consolidado histórico del proyecto tiene ~5.7k niveles y >2 columnas.
    if len(df_levels) < 1000 or df_levels.shape[1] < 5:
        raise RuntimeError(
            f"Consolidado sospechoso ({len(df_levels)} filas, "
            f"{df_levels.shape[1]} columnas). Revisar params NIST."
        )

    out_path = DIR_ORIGINALES / "nist_levels_todos_original.csv"
    df_levels.to_csv(out_path, index=False, encoding="utf-8")

    print(f"\nConsolidado: {out_path}")
    print(f"Filas: {len(df_levels):,} | Columnas: {df_levels.shape[1]}")
    print(f"Tamano: {out_path.stat().st_size:,} bytes")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return out_path


def main() -> int:
    print("NIST ASD — descarga automatizada (Fase 2)")
    print(f"ROOT={ROOT}")
    asegurar_carpetas()

    try:
        path_lines = descargar_lineas()
        path_levels = descargar_niveles()
    except Exception as exc:  # noqa: BLE001
        print(f"\nERROR FATAL: {exc}", file=sys.stderr)
        return 1

    print("\n" + "=" * 60)
    print("DESCARGA COMPLETADA")
    print("=" * 60)
    print(f"  {path_lines}")
    print(f"  {path_levels}")
    print(f"  {DIR_NIVELES}/nist_levels_*_original.csv ({len(ESPECTRA_LIST)} archivos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

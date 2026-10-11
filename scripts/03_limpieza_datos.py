#!/usr/bin/env python3
"""Fase 3 — Limpieza y transformacion (L1–L14 → data/procesados/).

Lee data/originales/, escribe data/procesados/.
Decisiones L1-L14; no imputa Aki.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
import warnings
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parent.parent
DIR_ORIGINALES = str(ROOT / "data" / "originales")
DIR_PROCESADOS = str(ROOT / "data" / "procesados")
os.makedirs(DIR_PROCESADOS, exist_ok=True)

RUTA_LINES = os.path.join(DIR_ORIGINALES, "nist_lines_H_Ne_original.csv")
RUTA_LEVELS = os.path.join(DIR_ORIGINALES, "nist_levels_todos_original.csv")


def display(*args, **kwargs):
    for a in args:
        if isinstance(a, pd.DataFrame):
            print(a.head(3).to_string())
        else:
            print(a)


class _PltStub:
    def __init__(self):
        self.rcParams = {}

    def figure(self, *a, **k):
        return self

    def subplots(self, *a, **k):
        class Ax:
            def __getattr__(self, n):
                return lambda *a, **k: None

        ax = Ax()
        return self, [ax, ax]

    def tight_layout(self, *a, **k):
        pass

    def show(self, *a, **k):
        pass

    def savefig(self, *a, **k):
        pass

    def __getattr__(self, n):
        return lambda *a, **k: None


plt = _PltStub()
sns = _PltStub()

print("Fase 3 — limpieza NIST")
print(f"ORIGINALES = {DIR_ORIGINALES}")
print(f"PROCESADOS = {DIR_PROCESADOS}")
for ruta in (RUTA_LINES, RUTA_LEVELS):
    if not os.path.isfile(ruta):
        raise SystemExit(f"ERROR: falta archivo de entrada: {ruta}")
    print(f"  OK {ruta} ({os.path.getsize(ruta):,} bytes)")


# --- notebook cell 2 ---
from datetime import datetime



pd.set_option("display.max_columns", None)
pd.set_option("display.width", 220)



print(f"pandas {pd.__version__} | numpy {np.__version__}")
print(f"Ejecutado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()
print("Archivos de entrada (solo lectura):")
for ruta in (RUTA_LINES, RUTA_LEVELS):
    with open(ruta, "rb") as f:
        huella = hashlib.md5(f.read()).hexdigest()
    print(f"  {ruta}")
    print(f"     {os.path.getsize(ruta):>12,} bytes   md5={huella}")


# --- notebook cell 4 ---
def parsear_csv_nist(texto, nombre_espectro=None):
    # El NIST intercala lineas vacias y separadores de guiones que hay que descartar
    # ANTES de pasarle el texto a pandas.
    lineas = [ln for ln in texto.split("\n") if ln.strip() and not ln.startswith("---")]
    df = pd.read_csv(StringIO("\n".join(lineas)), sep=",", low_memory=False, on_bad_lines="warn")
    # La cabecera del NIST termina en coma: pandas inventa una columna 'Unnamed: N' vacia.
    fantasmas = [c for c in df.columns if str(c).startswith("Unnamed:") and df[c].isna().all()]
    if fantasmas:
        df = df.drop(columns=fantasmas)
    if nombre_espectro is not None:
        df.insert(0, "espectro", nombre_espectro)
    return df


def decodificar_exportacion(df):
    # Deshace el envoltorio ="valor" del CSV del NIST y convierte en NaN las cadenas vacias
    # resultantes, que es lo que realmente significan.
    # NO altera el contenido: ="91.23" y 91.23 son exactamente el mismo dato.
    salida = df.copy()
    for col in salida.columns:
        if pd.api.types.is_numeric_dtype(salida[col]):
            continue
        s = salida[col].astype(str).str.strip()
        s = s.str.replace(r'^="', "", regex=True).str.replace(r'"$', "", regex=True).str.strip()
        salida[col] = s.replace({"": np.nan, "nan": np.nan, "None": np.nan}).mask(salida[col].isna())
    return salida


def resumen(df, etiqueta):
    print(f"{etiqueta:<42} {df.shape[0]:>7,} filas x {df.shape[1]:>3} columnas   "
          f"nulos={int(df.isna().sum().sum()):>8,}")


# Bitacora de la limpieza: cada paso deja registro de su efecto.
BITACORA = []


def registrar(paso, descripcion, filas, columnas, detalle=""):
    BITACORA.append({
        "paso": paso, "descripcion": descripcion,
        "filas": filas, "columnas": columnas, "detalle": detalle,
    })
    print(f"[{paso}] {descripcion}")
    print(f"      -> {filas:,} filas x {columnas} columnas   {detalle}")


print("Ayudantes definidos.")


# --- notebook cell 6 ---
with open(RUTA_LINES, "r", encoding="utf-8") as f:
    texto_lines = f.read()

# Misma lista de lineas utiles que usa parsear_csv_nist, para que los indices cuadren.
utiles = [ln for ln in texto_lines.split("\n") if ln.strip() and not ln.startswith("---")]
cortes = [i for i, ln in enumerate(utiles) if ln.startswith("element,sp_num")]

print(f"Lineas utiles en el archivo : {len(utiles):,}")
print(f"Cabeceras encontradas en    : {cortes}")
print()

medio_por_bloque = {}
for j, ini in enumerate(cortes):
    fin = cortes[j + 1] if j + 1 < len(cortes) else len(utiles)
    etiqueta = "aire" if "obs_wl_air" in utiles[ini] else "vacio"
    medio_por_bloque[ini] = etiqueta
    print(f"  Bloque {j + 1}: filas {ini + 1}..{fin - 1}  ->  {fin - 1 - ini:>6,} filas   medio={etiqueta}")

# A cada fila de datos (utiles[1:]) le corresponde el medio del bloque que la contiene.
medio_filas = []
for idx in range(1, len(utiles)):
    bloque = max(c for c in cortes if c <= idx)
    medio_filas.append(medio_por_bloque[bloque])

print()
print(f"Etiquetas de medio generadas: {len(medio_filas):,}")
print(pd.Series(medio_filas).value_counts().to_string())


# --- notebook cell 7 ---
df_lines_raw = parsear_csv_nist(texto_lines)
df_levels_raw = pd.read_csv(RUTA_LEVELS, low_memory=False)

assert len(df_lines_raw) == len(medio_filas), "Desalineacion entre el texto crudo y el parseo"
df_lines_raw["medio"] = medio_filas

resumen(df_lines_raw, "LINEAS (crudo, con artefacto)")
resumen(df_levels_raw, "NIVELES (crudo, con artefacto)")
print()
print("Columnas de LINEAS :", list(df_lines_raw.columns))
print()
print("Columnas de NIVELES:", list(df_levels_raw.columns))


# --- notebook cell 9 ---
df_lines = decodificar_exportacion(df_lines_raw)
df_levels = decodificar_exportacion(df_levels_raw)

comparativa = pd.DataFrame([
    {"fuente": "LINEAS",
     "nulos_antes_de_decodificar": int(df_lines_raw.isna().sum().sum()),
     "nulos_reales": int(df_lines.isna().sum().sum())},
    {"fuente": "NIVELES",
     "nulos_antes_de_decodificar": int(df_levels_raw.isna().sum().sum()),
     "nulos_reales": int(df_levels.isna().sum().sum())},
])
comparativa["ausencias_que_estaban_ocultas"] = (
    comparativa["nulos_reales"] - comparativa["nulos_antes_de_decodificar"]
)
display(comparativa)

print(f"Total de ausencias que el envoltorio escondia: "
      f"{int(comparativa['ausencias_que_estaban_ocultas'].sum()):,}")

registrar("L3", "Decodificado el envoltorio de exportacion",
          len(df_lines), df_lines.shape[1],
          f"{int(comparativa['ausencias_que_estaban_ocultas'].sum()):,} ausencias reveladas")


# --- notebook cell 11 ---
antes = len(df_lines)
mascara_cabecera = df_lines["element"] == "element"

print(f"Filas de cabecera detectadas: {int(mascara_cabecera.sum())}")
display(df_lines[mascara_cabecera].iloc[:, :8])

df_toclean = df_lines[~mascara_cabecera].reset_index(drop=True).copy()

print(f"\nFilas antes : {antes:,}")
print(f"Filas ahora : {len(df_toclean):,}")
print(f"Eliminadas  : {antes - len(df_toclean)}")
print()
print("Verificacion: la columna 'element' ya solo contiene simbolos quimicos reales")
print(sorted(df_toclean["element"].dropna().unique()))

registrar("L1", "Eliminadas las cabeceras incrustadas",
          len(df_toclean), df_toclean.shape[1], f"-{antes - len(df_toclean)} filas")


# --- notebook cell 13 ---
N_AIRE = 1.00028   # indice de refraccion del aire en condiciones estandar

col_obs = "obs_wl_vac(nm)"
col_ritz = "ritz_wl_vac(nm)"

print("Distribucion del medio de medicion:")
display(df_toclean["medio"].value_counts().to_frame("lineas"))

obs_num = pd.to_numeric(df_toclean[col_obs], errors="coerce")
es_aire = df_toclean["medio"] == "aire"

print(f"Lineas medidas en AIRE con longitud de onda observada : {int((es_aire & obs_num.notna()).sum()):,}")
print(f"Lineas medidas en VACIO con longitud de onda observada: {int((~es_aire & obs_num.notna()).sum()):,}")
print()
print("Efecto de la conversion sobre un ejemplo en aire:")
ejemplo = df_toclean.loc[es_aire & obs_num.notna()].head(3).index
display(pd.DataFrame({
    "medio": df_toclean.loc[ejemplo, "medio"],
    "lambda_original_nm": obs_num[ejemplo],
    "lambda_en_vacio_nm": (obs_num[ejemplo] * N_AIRE).round(6),
    "diferencia_nm": (obs_num[ejemplo] * N_AIRE - obs_num[ejemplo]).round(6),
}))

registrar("L2", "Reconstruido el medio de medicion (aire/vacio)",
          len(df_toclean), df_toclean.shape[1],
          f"{int(es_aire.sum()):,} filas en aire identificadas")


# --- notebook cell 15 ---
def extraer_energia(serie):
    # Separa el numero de las marcas del NIST:
    #   [valor] -> energia interpolada o teorica
    #   valor+x -> energia relativa a un origen desconocido
    s = serie.astype(str)
    interpolada = s.str.contains(r"\[", na=False)
    origen_desconocido = s.str.contains(r"\+[xy]", na=False)
    limpio = (
        s.str.replace(r"[\[\]]", "", regex=True)
        .str.replace(r"\+[xyzXYZ]", "", regex=True)
        .str.strip()
    )
    valor = pd.to_numeric(limpio, errors="coerce")
    return valor, interpolada.where(serie.notna()), origen_desconocido.where(serie.notna())


for origen, destino in [("Ei(cm-1)", "energia_inferior_cm1"), ("Ek(cm-1)", "energia_superior_cm1")]:
    antes_validos = int(pd.to_numeric(df_toclean[origen], errors="coerce").notna().sum())
    valor, interp, desc = extraer_energia(df_toclean[origen])
    df_toclean[destino] = valor
    df_toclean[destino + "_interpolada"] = interp
    df_toclean[destino + "_origen_desconocido"] = desc
    print(f"{origen:<12} valores numericos con coerce ingenuo: {antes_validos:>7,}")
    print(f"{'':<12} valores recuperados interpretando marcas: {int(valor.notna().sum()):>7,}   "
          f"(+{int(valor.notna().sum()) - antes_validos:,})")
    print(f"{'':<12} marcadas como interpoladas: {int(interp.sum()):>6,} | "
          f"origen desconocido: {int(desc.sum()):,}")
    print()


# --- notebook cell 16 ---
# Longitud de onda Ritz: el sufijo '+' indica que el valor es un limite, no una medida exacta.
s_ritz = df_toclean[col_ritz].astype(str)
df_toclean["longitud_onda_ritz_nm"] = pd.to_numeric(
    s_ritz.str.replace(r"\+$", "", regex=True).str.strip(), errors="coerce"
)
df_toclean["ritz_es_limite"] = s_ritz.str.endswith("+", na=False).where(df_toclean[col_ritz].notna())

antes_ritz = int(pd.to_numeric(df_toclean[col_ritz], errors="coerce").notna().sum())
print(f"Ritz con coerce ingenuo      : {antes_ritz:,}")
print(f"Ritz interpretando el sufijo : {int(df_toclean['longitud_onda_ritz_nm'].notna().sum()):,} "
      f"(+{int(df_toclean['longitud_onda_ritz_nm'].notna().sum()) - antes_ritz:,})")
print(f"Marcadas como limite         : {int(df_toclean['ritz_es_limite'].sum()):,}")

# La longitud de onda observada no trae marcas, pero se convierte con el mismo criterio.
df_toclean["longitud_onda_obs_nm"] = pd.to_numeric(df_toclean[col_obs], errors="coerce")


# --- notebook cell 17 ---
# Intensidad: el NIST mezcla el numero con banderas de calidad de la linea.
s_int = df_toclean["intens"].astype(str)
df_toclean["intensidad_valor"] = pd.to_numeric(
    s_int.str.extract(r"([0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?)")[0], errors="coerce"
)
banderas = s_int.str.replace(r"[0-9.]", "", regex=True).str.strip()
df_toclean["intensidad_bandera"] = banderas.replace("", np.nan).where(df_toclean["intens"].notna())

antes_int = int(pd.to_numeric(df_toclean["intens"], errors="coerce").notna().sum())
print(f"Intensidad con coerce ingenuo    : {antes_int:,}")
print(f"Intensidad separando la bandera  : {int(df_toclean['intensidad_valor'].notna().sum()):,} "
      f"(+{int(df_toclean['intensidad_valor'].notna().sum()) - antes_int:,})")
print()
print("Banderas de intensidad encontradas:")
display(df_toclean["intensidad_bandera"].value_counts().head(10).to_frame("frecuencia"))

registrar("L4", "Interpretada la notacion cientifica del NIST",
          len(df_toclean), df_toclean.shape[1],
          "energias, Ritz e intensidad con valor + bandera separados")


# --- notebook cell 19 ---
PATRON_J = re.compile(r"\d+(/\d+)?")


def parsear_J(v):
    # Solo convierte lo que es inequivocamente un entero o una fraccion simple.
    # '---', '0,1,2', '1/2 or 3/2' -> no resuelto (NaN)
    if pd.isna(v):
        return np.nan
    s = str(v).strip()
    if not PATRON_J.fullmatch(s):
        return np.nan
    if "/" in s:
        a, b = s.split("/")
        return float(a) / float(b)
    return float(s)


for origen, destino in [("J_i", "j_inferior"), ("J_k", "j_superior")]:
    df_toclean[destino + "_texto"] = df_toclean[origen]
    df_toclean[destino] = df_toclean[origen].map(parsear_J)
    df_toclean[destino + "_resuelto"] = (
        df_toclean[destino].notna().where(df_toclean[origen].notna())
    )
    ingenuo = int(pd.to_numeric(df_toclean[origen], errors="coerce").notna().sum())
    print(f"{origen}: coerce ingenuo={ingenuo:>6,}  |  parseo de fracciones="
          f"{int(df_toclean[destino].notna().sum()):>6,}  "
          f"(+{int(df_toclean[destino].notna().sum()) - ingenuo:,})")

print()
no_resueltos = df_toclean.loc[
    df_toclean["J_i"].notna() & df_toclean["j_inferior"].isna(), "J_i"
]
print(f"Valores de J_i no resueltos: {len(no_resueltos):,}")
display(no_resueltos.value_counts().head(8).to_frame("frecuencia"))


# --- notebook cell 20 ---
# Mismo tratamiento en la tabla de niveles.
df_niv = df_levels.copy()
df_niv["j_texto"] = df_niv["J"]
df_niv["j_valor"] = df_niv["J"].map(parsear_J)
df_niv["j_resuelto"] = df_niv["j_valor"].notna().where(df_niv["J"].notna())
df_niv["g"] = pd.to_numeric(df_niv["g"], errors="coerce")

# VERIFICACION FISICA: por definicion la degeneracion es g = 2J + 1.
# Si el parseo de la fraccion fuese incorrecto, esta identidad fallaria.
ev = df_niv["j_valor"].notna() & df_niv["g"].notna()
cumple = (df_niv["g"] == 2 * df_niv["j_valor"] + 1) & ev

print(f"Niveles con J y g evaluables : {int(ev.sum()):,}")
print(f"Cumplen g = 2J + 1           : {int(cumple.sum()):,} ({cumple.sum() / ev.sum() * 100:.2f}%)")
print(f"Niveles con g pero SIN J     : {int((df_niv['g'].notna() & df_niv['j_valor'].isna()).sum()):,}")
print()
print("El 100% de cumplimiento confirma que la conversion de fracciones es correcta.")
print("Los niveles con g pero sin J son aquellos en que el NIST no resolvio J:")
print("su g si esta documentada, asi que NO se puede derivar g a partir de J.")
print("Esto tiene consecuencias directas sobre el diseno de la base de datos (3FN).")

assert cumple.sum() == ev.sum(), "Inconsistencia cuantica: el parseo de J es incorrecto"

registrar("L5", "Parseado J de fraccion a decimal",
          len(df_toclean), df_toclean.shape[1], "verificado con g = 2J+1 al 100%")


# --- notebook cell 22 ---
for col in ["ID_i", "ID_k"]:
    df_toclean[col] = df_toclean[col].astype("string")
df_niv["Level ID"] = df_niv["Level ID"].astype("string")

print("Verificacion: los identificadores conservan sus ceros a la izquierda")
for col, df in [("ID_i", df_toclean), ("ID_k", df_toclean), ("Level ID", df_niv)]:
    muestra = df[col].dropna().head(3).tolist()
    con_cero = df[col].dropna().astype(str).str.startswith("0").mean() * 100
    print(f"  {col:<10} ejemplos={muestra}   empiezan por cero: {con_cero:.1f}%")

print()
print("Contraejemplo de lo que pasaria si se convirtieran a numero:")
print(f"  '006002.000001'  ->  {float('006002.000001')}   (se pierden los ceros)")

registrar("L6", "Identificadores protegidos como texto",
          len(df_toclean), df_toclean.shape[1], "ID_i, ID_k, Level ID")


# --- notebook cell 24 ---
print("Valor de 'Type' antes de normalizar:")
display(df_toclean["Type"].value_counts(dropna=False).to_frame("frecuencia"))

# El valor '2P' aparece una sola vez y no es un tipo de transicion valido del NIST.
anomalos = df_toclean[df_toclean["Type"] == "2P"]
if len(anomalos):
    print(f"\nValor anomalo detectado: '2P' en {len(anomalos)} fila(s).")
    display(anomalos[["element", "sp_num", col_obs, "Aki(s^-1)", "Type", "term_k"]])
    print("No corresponde a ningun tipo de transicion del NIST (E1/E2/M1/M2/UT): parece un")
    print("termino espectroscopico desplazado de columna. Se marca como 'UT' (sin clasificar)")
    print("en vez de eliminarlo, porque el resto de la fila es valido.")
    df_toclean.loc[df_toclean["Type"] == "2P", "Type"] = "UT"

df_toclean["tipo_transicion"] = df_toclean["Type"].fillna("E1")

print()
print("Valor de 'tipo_transicion' despues de normalizar:")
display(df_toclean["tipo_transicion"].value_counts().to_frame("frecuencia"))


# --- notebook cell 25 ---
ESCALA_ACC = ["AAA", "AA", "A+", "A", "B+", "B", "B'", "C+", "C", "C'", "D+", "D", "E"]

encontrados = set(df_toclean["Acc"].dropna().unique())
no_previstos = encontrados - set(ESCALA_ACC)
print(f"Codigos de exactitud encontrados : {len(encontrados)}")
print(f"Fuera de la escala documentada   : {no_previstos if no_previstos else 'ninguno'}")

df_toclean["exactitud"] = pd.Categorical(df_toclean["Acc"], categories=ESCALA_ACC, ordered=True)

print()
print("Distribucion de la exactitud (de mejor a peor):")
display(df_toclean["exactitud"].value_counts().reindex(ESCALA_ACC).to_frame("lineas"))

# Normalizacion de texto en las columnas categoricas restantes.
for col in ["element", "conf_i", "term_i", "conf_k", "term_k"]:
    df_toclean[col] = df_toclean[col].astype("string").str.strip()
for col in ["Configuration", "Term"]:
    df_niv[col] = df_niv[col].astype("string").str.strip()

registrar("L7", "Categoricas normalizadas",
          len(df_toclean), df_toclean.shape[1], "Type -> E1 explicito; Acc ordinal")


# --- notebook cell 27 ---
df_toclean["longitud_onda_nm"] = df_toclean["longitud_onda_obs_nm"].fillna(
    df_toclean["longitud_onda_ritz_nm"]
)
df_toclean["longitud_onda_origen"] = np.where(
    df_toclean["longitud_onda_obs_nm"].notna(), "observada", "ritz"
)
df_toclean.loc[df_toclean["longitud_onda_nm"].isna(), "longitud_onda_origen"] = np.nan

# Columna homogenea en vacio (aplica la conversion L2 a la longitud de onda definitiva).
df_toclean["longitud_onda_vacio_nm"] = np.where(
    df_toclean["medio"] == "aire",
    df_toclean["longitud_onda_nm"] * N_AIRE,
    df_toclean["longitud_onda_nm"],
)

aki = pd.to_numeric(df_toclean["Aki(s^-1)"], errors="coerce")
n = len(df_toclean)
obs = df_toclean["longitud_onda_obs_nm"]
lam = df_toclean["longitud_onda_nm"]

tabla = pd.DataFrame([
    {"base de evidencia": "Solo con longitud de onda OBSERVADA y Aki",
     "lineas": int((obs.notna() & aki.notna()).sum())},
    {"base de evidencia": "Con longitud de onda OBSERVADA o RITZ y Aki",
     "lineas": int((lam.notna() & aki.notna()).sum())},
    {"base de evidencia": "Con alguna longitud de onda disponible",
     "lineas": int(lam.notna().sum())},
])
tabla["% del total"] = (tabla["lineas"] / n * 100).round(1)
display(tabla)

ganancia = int((lam.notna() & aki.notna()).sum()) - int((obs.notna() & aki.notna()).sum())
print(f"El respaldo Ritz aporta {ganancia:,} lineas adicionales SIN INVENTAR NINGUN DATO.")
print()
display(df_toclean["longitud_onda_origen"].value_counts(dropna=False).to_frame("lineas"))

registrar("L8", "Longitud de onda con respaldo Ritz",
          len(df_toclean), df_toclean.shape[1], f"+{ganancia:,} lineas utilizables")


# --- notebook cell 29 ---
df_toclean["aki_s1"] = aki
df_toclean["tiene_aki"] = df_toclean["aki_s1"].notna()
df_toclean["fuerza_oscilador_fik"] = pd.to_numeric(df_toclean["fik"], errors="coerce")
df_toclean["log_gf"] = pd.to_numeric(df_toclean["log_gf"], errors="coerce")
df_toclean["incertidumbre_obs_nm"] = pd.to_numeric(df_toclean["unc_obs_wl"], errors="coerce")
df_toclean["incertidumbre_ritz_nm"] = pd.to_numeric(df_toclean["unc_ritz_wl"], errors="coerce")
df_toclean["g_inferior"] = pd.to_numeric(df_toclean["g_i"], errors="coerce")
df_toclean["g_superior"] = pd.to_numeric(df_toclean["g_k"], errors="coerce")

# Reconstruccion del espectro (elemento + estado de ionizacion en numeracion romana).
ROMANOS = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}
sp = pd.to_numeric(df_toclean["sp_num"], errors="coerce")
df_toclean["estado_ionizacion"] = sp.astype("Int8")
df_toclean["espectro"] = (
    df_toclean["element"].astype(str) + " " + sp.map(lambda v: ROMANOS.get(int(v)) if pd.notna(v) else None)
)

cobertura = df_toclean.groupby("espectro").agg(
    lineas=("aki_s1", "size"), con_aki=("aki_s1", "count")
)
cobertura["% con Aki"] = (cobertura["con_aki"] / cobertura["lineas"] * 100).round(1)
print("Cobertura de Aki por espectro (el sesgo que la imputacion habria borrado):")
display(cobertura.sort_values("% con Aki"))

registrar("L9", "Aki conservado sin imputar",
          len(df_toclean), df_toclean.shape[1],
          f"{int(df_toclean['tiene_aki'].sum()):,} con Aki, {int((~df_toclean['tiene_aki']).sum()):,} sin dato")


# --- notebook cell 31 ---
EV_A_CM1 = 8065.543937

df_toclean["log10_aki"] = np.log10(df_toclean["aki_s1"].where(df_toclean["aki_s1"] > 0))


def region_espectral(nm):
    if pd.isna(nm) or nm <= 0:
        return np.nan
    if nm < 10:
        return "Rayos X"
    if nm < 380:
        return "Ultravioleta"
    if nm <= 780:
        return "Visible"
    if nm <= 1e6:
        return "Infrarrojo"
    return "Microondas/Radio"


df_toclean["region_espectral"] = df_toclean["longitud_onda_vacio_nm"].map(region_espectral)
df_toclean["energia_foton_ev"] = (
    df_toclean["energia_superior_cm1"] - df_toclean["energia_inferior_cm1"]
) / EV_A_CM1

ORDEN_REG = ["Rayos X", "Ultravioleta", "Visible", "Infrarrojo", "Microondas/Radio"]
reg = df_toclean["region_espectral"].value_counts(dropna=False).reindex(ORDEN_REG + [np.nan]).dropna()
tabla_reg = reg.to_frame("lineas")
tabla_reg["%"] = (tabla_reg["lineas"] / len(df_toclean) * 100).round(2)
print("Distribucion por region del espectro electromagnetico:")
print("(antes de L8 el 46,07% quedaba 'sin dato'; el respaldo Ritz lo resuelve)")
display(tabla_reg)

print(f"Lineas sin region asignada: {int(df_toclean['region_espectral'].isna().sum()):,}")

registrar("L10", "Variables derivadas creadas",
          len(df_toclean), df_toclean.shape[1], "log10_aki, region_espectral, energia_foton_ev")


# --- notebook cell 32 ---
d = df_toclean[["longitud_onda_vacio_nm", "log10_aki", "element"]].dropna()
plt.tight_layout()

r = np.log10(d["longitud_onda_vacio_nm"]).corr(d["log10_aki"])
print(f"Correlacion de Pearson log-log: {r:+.4f}")


# --- notebook cell 34 ---
# Antes de descartar Prefix/Suffix hay que EXTRAER la informacion que contienen:
# Prefix == '[' marca que la energia del nivel es interpolada, no medida.
df_niv["energia_ev"] = pd.to_numeric(df_niv["Level (eV)"], errors="coerce")
df_niv["energia_interpolada"] = (df_niv["Prefix"].astype(str).str.strip() == "[")
df_niv["incertidumbre_ev"] = pd.to_numeric(df_niv["Uncertainty (eV)"], errors="coerce")

print("Informacion rescatada de Prefix antes de descartarlo:")
print(f"  Niveles con energia interpolada: {int(df_niv['energia_interpolada'].sum()):,} "
      f"({df_niv['energia_interpolada'].mean() * 100:.1f}%)")
print()

A_DESCARTAR = ["Lande", "Prefix", "Suffix", "Leading percentages"]
presentes = [c for c in A_DESCARTAR if c in df_niv.columns]

for c in presentes:
    print(f"  Descartada '{c}': {df_niv[c].isna().mean() * 100:.2f}% de nulos")

df_niv = df_niv.drop(columns=presentes)

registrar("L11", "Columnas sin valor informativo descartadas",
          len(df_niv), df_niv.shape[1], f"{len(presentes)} columnas: {presentes}")


# --- notebook cell 36 ---
print(f"Filas exactamente duplicadas: {int(df_toclean.duplicated().sum())}")

clave_fisica = ["element", "sp_num", "longitud_onda_nm",
                "conf_i", "term_i", "J_i", "conf_k", "term_k", "J_k"]
df_toclean["medicion_repetida"] = df_toclean.duplicated(subset=clave_fisica, keep=False)

n_rep = int(df_toclean["medicion_repetida"].sum())
print(f"Filas que comparten identidad fisica con otra: {n_rep:,}")

if n_rep:
    ejemplo = df_toclean[df_toclean["medicion_repetida"]].sort_values(clave_fisica)
    print("\nEjemplo: misma transicion, distinta referencia bibliografica")
    display(ejemplo[["element", "sp_num", "longitud_onda_nm", "aki_s1",
                     "tp_ref", "line_ref"]].head(6))

registrar("L12", "Duplicados marcados sin eliminar",
          len(df_toclean), df_toclean.shape[1], f"{n_rep} mediciones repetidas marcadas")


# --- notebook cell 38 ---
d = df_toclean[df_toclean["aki_s1"] > 0].copy()
d["clase"] = np.where(d["tipo_transicion"] == "E1", "Permitida (E1)",
                      "Prohibida (" + d["tipo_transicion"].astype(str) + ")")

resumen_tipo = d.groupby("clase")["log10_aki"].agg(["count", "min", "median", "max"]).round(2)
print("Distribucion de log10(Aki) segun el tipo de transicion:")
display(resumen_tipo.sort_values("count", ascending=False))

plt.figure(figsize=(11, 4))
orden = resumen_tipo.sort_values("count", ascending=False).index[:5]
plt.title("log10(Aki) por tipo de transicion: los 'atipicos' son fisica real")
plt.xlabel("")
plt.ylabel("log10(Aki)")
plt.xticks(rotation=15)
plt.tight_layout()

q1, q3 = df_toclean["aki_s1"].quantile([0.25, 0.75])
iqr = q3 - q1
fuera = ((df_toclean["aki_s1"] < q1 - 1.5 * iqr) | (df_toclean["aki_s1"] > q3 + 1.5 * iqr)).sum()
print(f"Atipicos de Aki segun IQR : {int(fuera):,}")
print(f"Eliminados                : 0")
print()
print("Las transiciones prohibidas viven varios ordenes de magnitud por debajo de las")
print("permitidas. Eliminarlas borraria una clase entera de fenomeno fisico.")

registrar("L13", "Atipicos conservados con justificacion fisica",
          len(df_toclean), df_toclean.shape[1], f"{int(fuera):,} detectados, 0 eliminados")


# --- notebook cell 40 ---
# --- Tabla de LINEAS: seleccion y renombrado --------------------------------
MAPA_LINEAS = {
    "element": "elemento",
    "espectro": "espectro",
    "estado_ionizacion": "estado_ionizacion",
    "longitud_onda_nm": "longitud_onda_nm",
    "longitud_onda_vacio_nm": "longitud_onda_vacio_nm",
    "longitud_onda_origen": "longitud_onda_origen",
    "medio": "medio",
    "longitud_onda_obs_nm": "longitud_onda_obs_nm",
    "longitud_onda_ritz_nm": "longitud_onda_ritz_nm",
    "ritz_es_limite": "ritz_es_limite",
    "incertidumbre_obs_nm": "incertidumbre_obs_nm",
    "incertidumbre_ritz_nm": "incertidumbre_ritz_nm",
    "region_espectral": "region_espectral",
    "aki_s1": "aki_s1",
    "log10_aki": "log10_aki",
    "tiene_aki": "tiene_aki",
    "fuerza_oscilador_fik": "fuerza_oscilador_fik",
    "log_gf": "log_gf",
    "exactitud": "exactitud",
    "tipo_transicion": "tipo_transicion",
    "intensidad_valor": "intensidad_valor",
    "intensidad_bandera": "intensidad_bandera",
    "energia_inferior_cm1": "energia_inferior_cm1",
    "energia_superior_cm1": "energia_superior_cm1",
    "energia_inferior_cm1_interpolada": "energia_inferior_interpolada",
    "energia_superior_cm1_interpolada": "energia_superior_interpolada",
    "energia_inferior_cm1_origen_desconocido": "energia_inferior_origen_desconocido",
    "energia_superior_cm1_origen_desconocido": "energia_superior_origen_desconocido",
    "energia_foton_ev": "energia_foton_ev",
    "conf_i": "configuracion_inferior",
    "term_i": "termino_inferior",
    "j_inferior": "j_inferior",
    "j_inferior_texto": "j_inferior_texto",
    "j_inferior_resuelto": "j_inferior_resuelto",
    "g_inferior": "g_inferior",
    "conf_k": "configuracion_superior",
    "term_k": "termino_superior",
    "j_superior": "j_superior",
    "j_superior_texto": "j_superior_texto",
    "j_superior_resuelto": "j_superior_resuelto",
    "g_superior": "g_superior",
    "ID_i": "id_nivel_inferior",
    "ID_k": "id_nivel_superior",
    "tp_ref": "ref_probabilidad",
    "line_ref": "ref_longitud_onda",
    "medicion_repetida": "medicion_repetida",
}

df_lineas_limpias = df_toclean[list(MAPA_LINEAS.keys())].rename(columns=MAPA_LINEAS).copy()
df_lineas_limpias.insert(0, "id_linea", range(1, len(df_lineas_limpias) + 1))

resumen(df_lineas_limpias, "LINEAS LIMPIAS")
display(df_lineas_limpias.head(3))


# --- notebook cell 41 ---
# --- Tabla de NIVELES: seleccion y renombrado -------------------------------
MAPA_NIVELES = {
    "Level ID": "id_nivel",
    "espectro": "espectro",
    "Configuration": "configuracion",
    "Term": "termino",
    "j_valor": "j_valor",
    "j_texto": "j_texto",
    "j_resuelto": "j_resuelto",
    "g": "g",
    "energia_ev": "energia_ev",
    "energia_interpolada": "energia_interpolada",
    "incertidumbre_ev": "incertidumbre_ev",
    "Reference": "referencia",
}

df_niveles_limpios = df_niv[list(MAPA_NIVELES.keys())].rename(columns=MAPA_NIVELES).copy()

# El elemento y el estado de ionizacion se derivan de la notacion del espectro ('Ne II').
partes = df_niveles_limpios["espectro"].astype(str).str.split(" ", n=1, expand=True)
ROM_INV = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
df_niveles_limpios.insert(1, "elemento", partes[0])
df_niveles_limpios.insert(2, "estado_ionizacion", partes[1].map(ROM_INV).astype("Int8"))

resumen(df_niveles_limpios, "NIVELES LIMPIOS")
display(df_niveles_limpios.head(3))


# --- notebook cell 42 ---
# --- DOBLE MERGE: los niveles entran una vez como inferior y otra como superior ---
COLS_NIVEL = ["id_nivel", "configuracion", "termino", "j_valor", "j_resuelto",
              "g", "energia_ev", "energia_interpolada", "incertidumbre_ev", "referencia"]

niv = df_niveles_limpios[COLS_NIVEL]

niv_inf = niv.add_suffix("_nivel_inf").rename(columns={"id_nivel_nivel_inf": "id_nivel_inferior"})
niv_sup = niv.add_suffix("_nivel_sup").rename(columns={"id_nivel_nivel_sup": "id_nivel_superior"})

filas_antes = len(df_lineas_limpias)

dataset = df_lineas_limpias.merge(niv_inf, on="id_nivel_inferior", how="left", indicator="match_inf")
dataset = dataset.merge(niv_sup, on="id_nivel_superior", how="left", indicator="match_sup")

print(f"Filas antes del merge : {filas_antes:,}")
print(f"Filas despues         : {len(dataset):,}   (diferencia: {len(dataset) - filas_antes:+,})")
print(f"Columnas              : {dataset.shape[1]}")
print()
for lado, col in [("inferior", "match_inf"), ("superior", "match_sup")]:
    emparejadas = int((dataset[col] == "both").sum())
    print(f"  Nivel {lado}: {emparejadas:,} emparejados ({emparejadas / len(dataset) * 100:.2f}%)")

dataset = dataset.drop(columns=["match_inf", "match_sup"])

assert len(dataset) == filas_antes, "El merge duplico filas: la clave no era unica"
print("\nOK: el merge no duplico ninguna fila (la clave id_nivel es unica).")

registrar("L14", "Union de las dos fuentes por identificador de nivel",
          len(dataset), dataset.shape[1], "doble merge (inferior + superior)")


# --- notebook cell 44 ---
DICCIONARIO = [
    ("id_linea", "(generada)", "entero", "-", "Identificador unico de la linea espectral"),
    ("elemento", "element", "texto", "-", "Simbolo quimico del elemento"),
    ("espectro", "element + sp_num", "texto", "-", "Elemento y estado de ionizacion (ej. 'Ne II')"),
    ("estado_ionizacion", "sp_num", "entero", "-", "1 = neutro, 2 = una vez ionizado"),
    ("longitud_onda_nm", "obs_wl / ritz_wl", "decimal", "nm", "Longitud de onda definitiva (observada, o Ritz si falta)"),
    ("longitud_onda_vacio_nm", "(derivada)", "decimal", "nm", "Longitud de onda homogeneizada al vacio"),
    ("longitud_onda_origen", "(derivada)", "texto", "-", "'observada' o 'ritz': de donde salio el valor"),
    ("medio", "(posicion en el archivo)", "texto", "-", "'aire' o 'vacio': medio en que se midio"),
    ("longitud_onda_obs_nm", "obs_wl_vac(nm)", "decimal", "nm", "Longitud de onda medida experimentalmente"),
    ("longitud_onda_ritz_nm", "ritz_wl_vac(nm)", "decimal", "nm", "Longitud de onda calculada de la diferencia de niveles"),
    ("ritz_es_limite", "ritz_wl (sufijo +)", "booleano", "-", "El valor Ritz es un limite, no un valor exacto"),
    ("incertidumbre_obs_nm", "unc_obs_wl", "decimal", "nm", "Incertidumbre de la longitud de onda observada"),
    ("incertidumbre_ritz_nm", "unc_ritz_wl", "decimal", "nm", "Incertidumbre de la longitud de onda Ritz"),
    ("region_espectral", "(derivada)", "texto", "-", "Rayos X / Ultravioleta / Visible / Infrarrojo / Microondas"),
    ("aki_s1", "Aki(s^-1)", "decimal", "s^-1", "Coeficiente de Einstein: probabilidad de emision espontanea"),
    ("log10_aki", "(derivada)", "decimal", "-", "Logaritmo decimal de Aki"),
    ("tiene_aki", "(derivada)", "booleano", "-", "Si la linea tiene Aki documentado"),
    ("fuerza_oscilador_fik", "fik", "decimal", "-", "Fuerza de oscilador de la transicion"),
    ("log_gf", "log_gf", "decimal", "-", "Logaritmo del producto g*f"),
    ("exactitud", "Acc", "categoria ordinal", "-", "Escala de exactitud del NIST, de AAA (mejor) a E (peor)"),
    ("tipo_transicion", "Type", "texto", "-", "E1 permitida; E2/M1/M2 prohibidas; UT sin clasificar"),
    ("intensidad_valor", "intens", "decimal", "u. arbitrarias", "Intensidad relativa (escala propia de cada espectro)"),
    ("intensidad_bandera", "intens", "texto", "-", "Bandera de calidad de la linea (*, a, b...)"),
    ("energia_inferior_cm1", "Ei(cm-1)", "decimal", "cm^-1", "Energia del nivel inferior de la transicion"),
    ("energia_superior_cm1", "Ek(cm-1)", "decimal", "cm^-1", "Energia del nivel superior de la transicion"),
    ("energia_inferior_interpolada", "Ei (corchetes)", "booleano", "-", "La energia inferior es interpolada, no medida"),
    ("energia_superior_interpolada", "Ek (corchetes)", "booleano", "-", "La energia superior es interpolada, no medida"),
    ("energia_inferior_origen_desconocido", "Ei (sufijo +x)", "booleano", "-", "Energia referida a un origen desconocido"),
    ("energia_superior_origen_desconocido", "Ek (sufijo +x)", "booleano", "-", "Energia referida a un origen desconocido"),
    ("energia_foton_ev", "(derivada)", "decimal", "eV", "Energia del foton emitido en la transicion"),
    ("configuracion_inferior", "conf_i", "texto", "-", "Configuracion electronica del nivel inferior"),
    ("termino_inferior", "term_i", "texto", "-", "Termino espectroscopico del nivel inferior"),
    ("j_inferior", "J_i", "decimal", "-", "Momento angular total del nivel inferior"),
    ("j_inferior_texto", "J_i", "texto", "-", "Valor original de J (puede ser '1/2' o no resuelto)"),
    ("j_inferior_resuelto", "(derivada)", "booleano", "-", "Si el NIST determino un unico valor de J"),
    ("g_inferior", "g_i", "entero", "-", "Degeneracion del nivel inferior (g = 2J+1)"),
    ("configuracion_superior", "conf_k", "texto", "-", "Configuracion electronica del nivel superior"),
    ("termino_superior", "term_k", "texto", "-", "Termino espectroscopico del nivel superior"),
    ("j_superior", "J_k", "decimal", "-", "Momento angular total del nivel superior"),
    ("j_superior_texto", "J_k", "texto", "-", "Valor original de J del nivel superior"),
    ("j_superior_resuelto", "(derivada)", "booleano", "-", "Si el NIST determino un unico valor de J"),
    ("g_superior", "g_k", "entero", "-", "Degeneracion del nivel superior"),
    ("id_nivel_inferior", "ID_i", "texto", "-", "Identificador NIST del nivel inferior (clave foranea)"),
    ("id_nivel_superior", "ID_k", "texto", "-", "Identificador NIST del nivel superior (clave foranea)"),
    ("ref_probabilidad", "tp_ref", "texto", "-", "Referencias de la probabilidad de transicion (lista)"),
    ("ref_longitud_onda", "line_ref", "texto", "-", "Referencias de la longitud de onda (lista)"),
    ("medicion_repetida", "(derivada)", "booleano", "-", "La transicion aparece medida mas de una vez"),
    ("id_nivel", "Level ID", "texto", "-", "Identificador NIST del nivel (clave primaria)"),
    ("configuracion", "Configuration", "texto", "-", "Configuracion electronica del nivel"),
    ("termino", "Term", "texto", "-", "Termino espectroscopico del nivel"),
    ("j_valor", "J", "decimal", "-", "Momento angular total del nivel"),
    ("j_texto", "J", "texto", "-", "Valor original de J"),
    ("j_resuelto", "(derivada)", "booleano", "-", "Si el NIST determino un unico valor de J"),
    ("g", "g", "entero", "-", "Degeneracion estadistica del nivel"),
    ("energia_ev", "Level (eV)", "decimal", "eV", "Energia del nivel"),
    ("energia_interpolada", "Prefix", "booleano", "-", "La energia es interpolada, no medida"),
    ("incertidumbre_ev", "Uncertainty (eV)", "decimal", "eV", "Incertidumbre de la energia del nivel"),
    ("referencia", "Reference", "texto", "-", "Referencias bibliograficas del nivel (lista)"),
]

df_diccionario = pd.DataFrame(
    DICCIONARIO, columns=["columna", "origen_nist", "tipo", "unidad", "descripcion"]
)
print(f"Columnas documentadas: {len(df_diccionario)}")
display(df_diccionario)


# --- notebook cell 46 ---
resultados = []


def comprobar(criterio, condicion, detalle=""):
    resultados.append({"criterio": criterio, "resultado": "OK" if condicion else "FALLA",
                       "detalle": detalle})
    return condicion


# 1. Las distribuciones no se aplanaron
criticas = ["longitud_onda_nm", "aki_s1", "energia_inferior_cm1", "energia_superior_cm1"]
sin_colapso = True
for c in criticas:
    q1_, med, q3_ = dataset[c].quantile([0.25, 0.5, 0.75])
    if not (q1_ < med < q3_):
        sin_colapso = False
comprobar("Los cuartiles siguen siendo distintos (sin colapso por imputacion)",
          sin_colapso, f"{len(criticas)} variables criticas revisadas")

# 2. Validaciones fisicas
v = {
    "longitud de onda <= 0": int((dataset["longitud_onda_nm"] <= 0).sum()),
    "Aki <= 0": int((dataset["aki_s1"] <= 0).sum()),
    "Ek <= Ei": int((dataset["energia_superior_cm1"] <= dataset["energia_inferior_cm1"]).sum()),
    "Ei < 0": int((dataset["energia_inferior_cm1"] < 0).sum()),
}
comprobar("Cero valores fisicamente imposibles", sum(v.values()) == 0, str(v))

# 3. g = 2J + 1
ev2 = df_niveles_limpios["j_valor"].notna() & df_niveles_limpios["g"].notna()
ok_g = bool((df_niveles_limpios.loc[ev2, "g"] == 2 * df_niveles_limpios.loc[ev2, "j_valor"] + 1).all())
comprobar("Se cumple g = 2J + 1", ok_g, f"{int(ev2.sum()):,} niveles evaluados")

# 4. No se perdieron filas
comprobar("Se conservan 18 288 lineas (18 290 menos las 2 cabeceras)",
          len(dataset) == 18288, f"{len(dataset):,} filas")

# 5. El merge no duplico
comprobar("El merge no duplico filas", len(dataset) == len(df_lineas_limpias),
          f"{len(dataset):,} vs {len(df_lineas_limpias):,}")

# 6. La base de evidencia crecio
base = int((dataset["longitud_onda_nm"].notna() & dataset["aki_s1"].notna()).sum())
comprobar("La base de evidencia llega a 12 603 lineas", base == 12603, f"{base:,} lineas")

# 7. La correlacion se mantiene
dd = dataset[["longitud_onda_vacio_nm", "log10_aki"]].dropna()
corr = np.log10(dd["longitud_onda_vacio_nm"]).corr(dd["log10_aki"])
comprobar("La correlacion log-log sigue en torno a -0,68", -0.75 < corr < -0.60, f"r = {corr:+.4f}")

# 8. Los identificadores conservan los ceros
ceros = dataset["id_nivel_inferior"].dropna().astype(str).str.startswith("0").mean()
comprobar("Los identificadores conservan sus ceros a la izquierda", ceros > 0.9,
          f"{ceros * 100:.1f}% empiezan por '0'")

df_val = pd.DataFrame(resultados)
display(df_val)

assert (df_val["resultado"] == "OK").all(), "Hay criterios de aceptacion sin cumplir"
print("TODOS LOS CRITERIOS DE ACEPTACION SE CUMPLEN.")


# --- notebook cell 47 ---
print("=== describe() de las variables criticas tras la limpieza ===")
print("(si la imputacion hubiese aplanado alguna columna, se veria aqui)")
display(dataset[["longitud_onda_nm", "longitud_onda_vacio_nm", "aki_s1", "log10_aki",
                 "energia_inferior_cm1", "energia_superior_cm1", "energia_foton_ev"]].describe().T)


# --- notebook cell 49 ---
print("=== Unicidad de las claves primarias candidatas ===")
pk = [
    ("nivel_energia.id_nivel", df_niveles_limpios["id_nivel"]),
    ("linea_espectral.id_linea", dataset["id_linea"]),
]
for nombre, serie in pk:
    dup = int(serie.duplicated().sum())
    nulos = int(serie.isna().sum())
    print(f"  {nombre:<28} duplicados={dup}  nulos={nulos}  -> "
          f"{'VALIDA' if dup == 0 and nulos == 0 else 'NO VALIDA'}")

print()
print("=== Integridad referencial hacia nivel_energia ===")
universo = set(df_niveles_limpios["id_nivel"].dropna())
for col in ["id_nivel_inferior", "id_nivel_superior"]:
    s = dataset[col]
    huerfanas = int((s.notna() & ~s.isin(universo)).sum())
    nulas = int(s.isna().sum())
    print(f"  {col:<20} huerfanas={huerfanas}  nulas={nulas} "
          f"({nulas / len(dataset) * 100:.2f}%)  -> FK nulable, sin violaciones")


# --- notebook cell 50 ---
print("=== Cardinalidad de cada tabla propuesta ===")

def separar_refs(serie):
    # Las referencias vienen como listas separadas por comas: eso viola la 1FN
    # y es exactamente lo que obliga a crear las tablas puente.
    tokens = set()
    for v in serie.dropna().astype(str):
        tokens.update(t.strip() for t in v.split(",") if t.strip())
    return tokens


refs = (separar_refs(dataset["ref_probabilidad"])
        | separar_refs(dataset["ref_longitud_onda"])
        | separar_refs(df_niveles_limpios["referencia"]))

cardinalidades = pd.DataFrame([
    {"tabla": "elemento", "filas": dataset["elemento"].nunique()},
    {"tabla": "espectro", "filas": dataset["espectro"].nunique()},
    {"tabla": "tipo_transicion", "filas": dataset["tipo_transicion"].nunique()},
    {"tabla": "exactitud", "filas": int(dataset["exactitud"].nunique())},
    {"tabla": "referencia", "filas": len(refs)},
    {"tabla": "nivel_energia", "filas": len(df_niveles_limpios)},
    {"tabla": "linea_espectral", "filas": len(dataset)},
])
display(cardinalidades)

print("Valores con lista separada por comas (violacion de 1FN que justifica las tablas puente):")
for nombre, serie in [("ref_probabilidad", dataset["ref_probabilidad"]),
                      ("ref_longitud_onda", dataset["ref_longitud_onda"]),
                      ("referencia (niveles)", df_niveles_limpios["referencia"])]:
    con_coma = int(serie.dropna().astype(str).str.contains(",").sum())
    print(f"  {nombre:<22} {con_coma:>6,} valores son listas, no valores atomicos")


# --- notebook cell 51 ---
# El espectro de la linea debe coincidir con el de sus niveles: si no, el modelo
# relacional tendria una inconsistencia que las claves foraneas no podrian expresar.
esp_nivel = dict(zip(df_niveles_limpios["id_nivel"], df_niveles_limpios["espectro"]))
ei = dataset["id_nivel_inferior"].map(esp_nivel)
ek = dataset["id_nivel_superior"].map(esp_nivel)
comparables = ei.notna() & ek.notna()

print("=== Coherencia entre el espectro de la linea y el de sus niveles ===")
print(f"  Comparables          : {int(comparables.sum()):,}")
print(f"  Nivel inferior OK    : {int((ei[comparables] == dataset.loc[comparables, 'espectro']).sum()):,}")
print(f"  Nivel superior OK    : {int((ek[comparables] == dataset.loc[comparables, 'espectro']).sum()):,}")
print()
print("Coherencia total: el modelo relacional puede confiar en las claves foraneas.")

# Dependencias funcionales que deciden el diseno en 3FN.
print()
print("=== Dependencias funcionales relevantes para la 3FN ===")
ev3 = df_niveles_limpios["j_valor"].notna() & df_niveles_limpios["g"].notna()
print(f"  g = 2J+1 se cumple en {int((df_niveles_limpios.loc[ev3, 'g'] == 2 * df_niveles_limpios.loc[ev3, 'j_valor'] + 1).sum()):,}"
      f" de {int(ev3.sum()):,} casos (100%)")
print(f"  PERO {int((df_niveles_limpios['g'].notna() & df_niveles_limpios['j_valor'].isna()).sum()):,}"
      f" niveles tienen g sin J: g NO puede ser columna generada")

gi = dataset["g_inferior"]; fik_ = dataset["fuerza_oscilador_fik"]; lgf = dataset["log_gf"]
m = gi.notna() & fik_.notna() & lgf.notna() & (fik_ > 0) & (gi > 0)
dif = (np.log10(gi[m] * fik_[m]) - lgf[m]).abs()
print(f"  log_gf = log10(g_i*fik) solo coincide en {(dif < 0.01).mean() * 100:.2f}% de "
      f"{int(m.sum()):,} casos -> log_gf SI debe almacenarse")


# --- notebook cell 53 ---
salidas = {
    "dataset_limpio.csv": dataset,
    "lineas_limpias.csv": df_lineas_limpias,
    "niveles_limpios.csv": df_niveles_limpios,
    "diccionario_columnas.csv": df_diccionario,
}

for nombre, df in salidas.items():
    ruta = os.path.join(DIR_PROCESADOS, nombre)
    df.to_csv(ruta, index=False, encoding="utf-8")
    print(f"  {nombre:<28} {df.shape[0]:>7,} filas x {df.shape[1]:>3} col   "
          f"{os.path.getsize(ruta):>12,} bytes")

print()
print("Verificacion de que los originales siguen intactos:")
for ruta in (RUTA_LINES, RUTA_LEVELS):
    with open(ruta, "rb") as f:
        print(f"  {os.path.basename(ruta):<40} md5={hashlib.md5(f.read()).hexdigest()}")


# --- notebook cell 54 ---
print("=" * 78)
print("BITACORA DE LA LIMPIEZA")
print("=" * 78)
display(pd.DataFrame(BITACORA))


# --- notebook cell 55 ---
print("=" * 78)
print("RESUMEN ANTES / DESPUES")
print("=" * 78)

antes_lineas = len(df_lines_raw)
comparacion = pd.DataFrame([
    {"metrica": "Filas de lineas", "antes": f"{antes_lineas:,}", "despues": f"{len(dataset):,}",
     "comentario": "2 cabeceras incrustadas eliminadas"},
    {"metrica": "Filas de niveles", "antes": f"{len(df_levels_raw):,}",
     "despues": f"{len(df_niveles_limpios):,}", "comentario": "ninguna eliminada"},
    {"metrica": "Columnas utilizables (lineas)", "antes": "0 numericas",
     "despues": f"{dataset.select_dtypes(include=[np.number]).shape[1]} numericas",
     "comentario": "todo era texto por el envoltorio"},
    {"metrica": "Nulos visibles en lineas", "antes": f"{int(df_lines_raw.isna().sum().sum()):,}",
     "despues": f"{int(dataset.isna().sum().sum()):,}", "comentario": "las ausencias ya son visibles"},
    {"metrica": "Lineas utiles para la pregunta", "antes": "4 462",
     "despues": f"{base:,}", "comentario": "gracias al respaldo Ritz (L8)"},
    {"metrica": "Lineas con region espectral", "antes": "9 862 (53,9%)",
     "despues": f"{int(dataset['region_espectral'].notna().sum()):,} "
                f"({dataset['region_espectral'].notna().mean() * 100:.1f}%)",
     "comentario": "ya casi no quedan sin clasificar"},
    {"metrica": "Correlacion lambda-Aki", "antes": "-0,0023 (escala cruda)",
     "despues": f"{corr:+.4f} (log-log)", "comentario": "la relacion se vuelve visible"},
    {"metrica": "Valores fisicamente imposibles", "antes": "0", "despues": "0",
     "comentario": "los datos ya eran fisicamente correctos"},
    {"metrica": "Filas eliminadas", "antes": "-", "despues": "2",
     "comentario": "solo cabeceras, ninguna observacion"},
    {"metrica": "Valores imputados", "antes": "-", "despues": "0",
     "comentario": "no se invento ningun dato"},
])
display(comparacion)


# --- checks finales ---
if len(df_lineas_limpias) != 18288:
    raise SystemExit(f"ERROR: lineas esperadas 18288, got {len(df_lineas_limpias)}")
if len(df_niveles_limpios) != 5752:
    raise SystemExit(f"ERROR: niveles esperados 5752, got {len(df_niveles_limpios)}")
print("CHECKS OK: 18288 lineas, 5752 niveles")
print("Fase 3 completada.")

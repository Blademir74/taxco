import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

BASE_PATH = Path(r"C:\Users\campe\Desktop\taxco")
SECCION_MIN = 2134
SECCION_MAX = 2222
ID_MUNICIPIO_TAXCO = 56

def to_int(series):
    s = series.astype(str).str.extract(r"(^\d+)", expand=False)
    return pd.to_numeric(s, errors="coerce").astype("Int64")

def to_num(series):
    return pd.to_numeric(series, errors="coerce")

# Cargar 2018
df2018 = pd.read_csv(BASE_PATH / "2018.csv", encoding="latin1")
df2018["SECCION_INT"] = to_int(df2018["SECCION"])
df2018_taxco = df2018[
    (df2018["ID_MUNICIPIO"] == ID_MUNICIPIO_TAXCO) &
    (df2018["SECCION_INT"].between(SECCION_MIN, SECCION_MAX))
].copy()

print("="*80)
print("DIAGNÓSTICO DETALLADO 2018 - INCONSISTENCIAS")
print("="*80)

# 1. DUPLICADOS
print("\n[1/3] CASILLAS DUPLICADAS (9 registros)")
print("-"*80)
dups = df2018_taxco[df2018_taxco.duplicated(subset=["SECCION_INT", "CASILLA"], keep=False)]
dups_display = dups[["SECCION", "CASILLA", "TOTAL_VOTOS", "LISTA_NOMINAL"]].sort_values(["SECCION", "CASILLA"])
print(dups_display.to_string(index=False))

# 2. TOTAL INCORRECTO (total ≠ suma de componentes)
print("\n\n[2/3] ACTAS CON TOTAL_VOTOS INCORRECTO (67 registros)")
print("-"*80)

for col in ["NUM_VOTOS_VALIDOS", "NUM_VOTOS_CAN_NREG", "NUM_VOTOS_NULOS", "TOTAL_VOTOS", "LISTA_NOMINAL"]:
    df2018_taxco[col] = to_num(df2018_taxco[col])

df2018_taxco["TOTAL_CALC"] = (
    df2018_taxco["NUM_VOTOS_VALIDOS"].fillna(0) +
    df2018_taxco["NUM_VOTOS_CAN_NREG"].fillna(0) +
    df2018_taxco["NUM_VOTOS_NULOS"].fillna(0)
)

inc_total = df2018_taxco[df2018_taxco["TOTAL_VOTOS"] != df2018_taxco["TOTAL_CALC"]].copy()
inc_total["DIFERENCIA"] = inc_total["TOTAL_VOTOS"] - inc_total["TOTAL_CALC"]

inc_display = inc_total[[
    "SECCION", "CASILLA", "NUM_VOTOS_VALIDOS", "NUM_VOTOS_NULOS", 
    "TOTAL_VOTOS", "TOTAL_CALC", "DIFERENCIA", "LISTA_NOMINAL"
]].head(15)

print("Primeras 15 actas con error:")
print(inc_display.to_string(index=False))
print(f"\n... y {len(inc_total)-15} actas más con el mismo problema")

# 3. TOTAL > LISTA NOMINAL (imposible físicamente)
print("\n\n[3/3] ACTAS CON TOTAL_VOTOS > LISTA_NOMINAL (68 registros)")
print("-"*80)

inc_mayor = df2018_taxco[df2018_taxco["TOTAL_VOTOS"] > df2018_taxco["LISTA_NOMINAL"]].copy()
inc_mayor["EXCESO"] = inc_mayor["TOTAL_VOTOS"] - inc_mayor["LISTA_NOMINAL"]

inc_mayor_display = inc_mayor[[
    "SECCION", "CASILLA", "TOTAL_VOTOS", "LISTA_NOMINAL", "EXCESO"
]].sort_values("EXCESO", ascending=False).head(15)

print("Top 15 actas con mayor exceso:")
print(inc_mayor_display.to_string(index=False))

# ESTADÍSTICAS
print("\n" + "="*80)
print("ESTADÍSTICAS DE CALIDAD 2018")
print("="*80)
print(f"Total de casillas analizadas: {len(df2018_taxco)}")
print(f"Casillas con datos correctos: {len(df2018_taxco) - len(inc_total) - len(inc_mayor) + len(inc_total[inc_total['TOTAL_VOTOS'] > inc_total['LISTA_NOMINAL']])}")
print(f"Casillas con problemas: {len(inc_total.merge(inc_mayor, on=['SECCION', 'CASILLA'], how='outer'))}")
print(f"\nPorcentaje de datos limpios: {(1 - len(inc_total.merge(inc_mayor, on=['SECCION', 'CASILLA'], how='outer'))/len(df2018_taxco))*100:.1f}%")

# EXPORTAR PARA REVISIÓN
OUT_DIR = BASE_PATH / "diagnostico_2018"
OUT_DIR.mkdir(exist_ok=True)

dups.to_csv(OUT_DIR / "2018_duplicados.csv", index=False)
inc_total.to_csv(OUT_DIR / "2018_total_incorrecto.csv", index=False)
inc_mayor.to_csv(OUT_DIR / "2018_total_mayor_lista.csv", index=False)

print(f"\n✓ Archivos de diagnóstico exportados a: {OUT_DIR}")
print("  - 2018_duplicados.csv")
print("  - 2018_total_incorrecto.csv")
print("  - 2018_total_mayor_lista.csv")

import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configuración
BASE_PATH = Path(r"C:\Users\campe\Desktop\taxco")
SECCION_MIN = 2134
SECCION_MAX = 2222
ID_MUNICIPIO_TAXCO = 56

print("="*60)
print("AUDITORÍA DE DATOS ELECTORALES - TAXCO DE ALARCÓN")
print("="*60)

# Funciones auxiliares
def to_int(series):
    """Convierte sección a entero manejando anexas (2177B -> 2177)"""
    s = series.astype(str).str.extract(r"(^\d+)", expand=False)
    return pd.to_numeric(s, errors="coerce").astype("Int64")

def to_num(series):
    """Convierte a numérico"""
    return pd.to_numeric(series, errors="coerce")

# 1. CARGA DE ARCHIVOS
print("\n[1/5] Cargando archivos...")
try:
    df2018 = pd.read_csv(BASE_PATH / "2018.csv", encoding="latin1")
    print(f"  ✓ 2018.csv: {len(df2018)} registros")
except Exception as e:
    print(f"  ✗ Error en 2018.csv: {e}")
    exit()

try:
    df2021 = pd.read_csv(BASE_PATH / "2021.csv", encoding="latin1")
    print(f"  ✓ 2021.csv: {len(df2021)} registros")
except Exception as e:
    print(f"  ✗ Error en 2021.csv: {e}")
    exit()

try:
    df2024 = pd.read_csv(BASE_PATH / "2024.csv", encoding="latin1")
    print(f"  ✓ 2024.csv: {len(df2024)} registros")
except Exception as e:
    print(f"  ✗ Error en 2024.csv: {e}")
    exit()

try:
    df_ine = pd.read_csv(BASE_PATH / "ine.csv", encoding="latin1")
    print(f"  ✓ ine.csv: {len(df_ine)} registros")
except Exception as e:
    print(f"  ✗ Error en ine.csv: {e}")
    exit()

try:
    df_inegi = pd.read_csv(BASE_PATH / "INEGI_limpio.csv", encoding="latin1")
    print(f"  ✓ INEGI_limpio.csv: {len(df_inegi)} registros")
except Exception as e:
    print(f"  ✗ Error en INEGI_limpio.csv: {e}")
    exit()

# 2. FILTRADO GEOGRÁFICO
print("\n[2/5] Filtrando municipio 56 (Taxco) y secciones 2134-2222...")

for df in [df2018, df2021, df2024]:
    df["SECCION_INT"] = to_int(df["SECCION"])

df2018_taxco = df2018[
    (df2018["ID_MUNICIPIO"] == ID_MUNICIPIO_TAXCO) &
    (df2018["SECCION_INT"].between(SECCION_MIN, SECCION_MAX))
].copy()

df2021_taxco = df2021[
    (df2021["ID_MUNICIPIO"] == float(ID_MUNICIPIO_TAXCO)) &
    (df2021["SECCION_INT"].between(SECCION_MIN, SECCION_MAX))
].copy()

df2024_taxco = df2024[
    (df2024["ID_MUNICIPIO"] == ID_MUNICIPIO_TAXCO) &
    (df2024["SECCION_INT"].between(SECCION_MIN, SECCION_MAX))
].copy()

df_ine["SECCION_INT"] = to_int(df_ine["SECCION"])
df_ine_taxco = df_ine[
    df_ine["SECCION_INT"].between(SECCION_MIN, SECCION_MAX)
].copy()

df_inegi_taxco = df_inegi[
    (df_inegi["CLAVE MUNICIPIO"] == ID_MUNICIPIO_TAXCO) &
    (df_inegi["SECCION"].between(SECCION_MIN, SECCION_MAX))
].copy()

print(f"  ✓ 2018 Taxco: {len(df2018_taxco)} casillas")
print(f"  ✓ 2021 Taxco: {len(df2021_taxco)} casillas")
print(f"  ✓ 2024 Taxco: {len(df2024_taxco)} casillas")
print(f"  ✓ INE Taxco: {len(df_ine_taxco)} secciones")
print(f"  ✓ INEGI Taxco: {len(df_inegi_taxco)} secciones")

# 3. DETECCIÓN DE DUPLICADOS
print("\n[3/5] Detectando duplicados...")

dup_2018 = df2018_taxco.duplicated(subset=["SECCION_INT", "CASILLA"], keep=False).sum()
dup_2021 = df2021_taxco.duplicated(subset=["SECCION_INT", "CASILLAS"], keep=False).sum()
dup_2024 = df2024_taxco.duplicated(subset=["SECCION_INT", "CASILLAS"], keep=False).sum()
dup_ine = df_ine_taxco.duplicated(subset=["SECCION_INT"], keep=False).sum()

print(f"  • 2018: {dup_2018} casillas duplicadas")
print(f"  • 2021: {dup_2021} casillas duplicadas")
print(f"  • 2024: {dup_2024} casillas duplicadas")
print(f"  • INE: {dup_ine} secciones duplicadas")

# 4. VALORES NULOS EN CAMPOS CRÍTICOS
print("\n[4/5] Detectando valores nulos...")

nulos_2018 = {
    "SECCION": df2018_taxco["SECCION"].isna().sum(),
    "TOTAL_VOTOS": df2018_taxco["TOTAL_VOTOS"].isna().sum(),
    "LISTA_NOMINAL": df2018_taxco["LISTA_NOMINAL"].isna().sum()
}

nulos_2021 = {
    "SECCION": df2021_taxco["SECCION"].isna().sum(),
    "TOTAL_VOTOS": df2021_taxco["TOTAL_VOTOS"].isna().sum(),
    "LISTA_NOMINAL": df2021_taxco["LISTA_NOMINAL"].isna().sum()
}

nulos_2024 = {
    "SECCION": df2024_taxco["SECCION"].isna().sum(),
    "TOTAL_VOTOS": df2024_taxco["TOTAL_VOTOS"].isna().sum(),
    "LISTA_NOMINAL": df2024_taxco["LISTA_NOMINAL"].isna().sum()
}

print(f"  • 2018: {sum(nulos_2018.values())} nulos totales")
print(f"  • 2021: {sum(nulos_2021.values())} nulos totales")
print(f"  • 2024: {sum(nulos_2024.values())} nulos totales")

# 5. INTEGRIDAD NUMÉRICA
print("\n[5/5] Validando integridad numérica...")

# Preparar columnas
for df in [df2018_taxco, df2021_taxco, df2024_taxco]:
    for col in ["NUM_VOTOS_VALIDOS", "NUM_VOTOS_CAN_NREG", "NUM_VOTOS_NULOS", "TOTAL_VOTOS", "LISTA_NOMINAL"]:
        if col in df.columns:
            df[col] = to_num(df[col])

# 2018
df2018_taxco["TOTAL_CALC"] = (
    df2018_taxco["NUM_VOTOS_VALIDOS"].fillna(0) +
    df2018_taxco["NUM_VOTOS_CAN_NREG"].fillna(0) +
    df2018_taxco["NUM_VOTOS_NULOS"].fillna(0)
)
inc_total_2018 = (df2018_taxco["TOTAL_VOTOS"] != df2018_taxco["TOTAL_CALC"]).sum()
inc_mayor_2018 = (df2018_taxco["TOTAL_VOTOS"] > df2018_taxco["LISTA_NOMINAL"]).sum()

# 2021
df2021_taxco["TOTAL_CALC"] = (
    df2021_taxco["NUM_VOTOS_VALIDOS"].fillna(0) +
    df2021_taxco["NUM_VOTOS_CAN_NREG"].fillna(0) +
    df2021_taxco["NUM_VOTOS_NULOS"].fillna(0)
)
inc_total_2021 = (df2021_taxco["TOTAL_VOTOS"] != df2021_taxco["TOTAL_CALC"]).sum()
inc_mayor_2021 = (df2021_taxco["TOTAL_VOTOS"] > df2021_taxco["LISTA_NOMINAL"]).sum()

# 2024
df2024_taxco["TOTAL_CALC"] = (
    df2024_taxco["NUM_VOTOS_VALIDOS"].fillna(0) +
    df2024_taxco["NUM_VOTOS_CAN_NREG"].fillna(0) +
    df2024_taxco["NUM_VOTOS_NULOS"].fillna(0)
)
inc_total_2024 = (df2024_taxco["TOTAL_VOTOS"] != df2024_taxco["TOTAL_CALC"]).sum()
inc_mayor_2024 = (df2024_taxco["TOTAL_VOTOS"] > df2024_taxco["LISTA_NOMINAL"]).sum()

print(f"  • 2018: {inc_total_2018} actas con total incorrecto, {inc_mayor_2018} con total > lista nominal")
print(f"  • 2021: {inc_total_2021} actas con total incorrecto, {inc_mayor_2021} con total > lista nominal")
print(f"  • 2024: {inc_total_2024} actas con total incorrecto, {inc_mayor_2024} con total > lista nominal")

# RESUMEN FINAL
print("\n" + "="*60)
print("RESUMEN DE AUDITORÍA")
print("="*60)
print(f"Total de secciones en Taxco (rango 2134-2222): {df_ine_taxco['SECCION_INT'].nunique()}")
print(f"Total de casillas 2018: {len(df2018_taxco)}")
print(f"Total de casillas 2021: {len(df2021_taxco)}")
print(f"Total de casillas 2024: {len(df2024_taxco)}")
print(f"\n⚠️  INCONSISTENCIAS CRÍTICAS:")
print(f"  • Duplicados totales: {dup_2018 + dup_2021 + dup_2024}")
print(f"  • Actas con total > lista nominal: {inc_mayor_2018 + inc_mayor_2021 + inc_mayor_2024}")
print("\n✓ Auditoría completada. Archivos listos para ETL.")

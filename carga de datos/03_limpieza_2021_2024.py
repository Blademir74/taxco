import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

BASE_PATH = Path(r"C:\Users\campe\Desktop\taxco")
OUT_DIR = BASE_PATH / "datos_limpios"
OUT_DIR.mkdir(exist_ok=True)

SECCION_MIN = 2134
SECCION_MAX = 2222
ID_MUNICIPIO_TAXCO = 56

def to_int(series):
    s = series.astype(str).str.extract(r"(^\d+)", expand=False)
    return pd.to_numeric(s, errors="coerce").astype("Int64")

def to_num(series):
    return pd.to_numeric(series, errors="coerce")

print("="*80)
print("LIMPIEZA Y VALIDACIÓN - 2021 Y 2024")
print("="*80)

# =============================================
# 2021
# =============================================
print("\n[1/2] PROCESANDO 2021...")

df2021 = pd.read_csv(BASE_PATH / "2021.csv", encoding="latin1")
df2021["SECCION_INT"] = to_int(df2021["SECCION"])

df2021_taxco = df2021[
    (df2021["ID_MUNICIPIO"] == float(ID_MUNICIPIO_TAXCO)) &
    (df2021["SECCION_INT"].between(SECCION_MIN, SECCION_MAX))
].copy()

print(f"  • Registros originales: {len(df2021_taxco)}")

# Normalizar columnas numéricas
for col in ["NUM_VOTOS_VALIDOS", "NUM_VOTOS_CAN_NREG", "NUM_VOTOS_NULOS", "TOTAL_VOTOS", "LISTA_NOMINAL"]:
    if col in df2021_taxco.columns:
        df2021_taxco[col] = to_num(df2021_taxco[col])

# Validar integridad
df2021_taxco['TOTAL_CALCULADO'] = (
    df2021_taxco['NUM_VOTOS_VALIDOS'].fillna(0) +
    df2021_taxco['NUM_VOTOS_CAN_NREG'].fillna(0) +
    df2021_taxco['NUM_VOTOS_NULOS'].fillna(0)
)

df2021_taxco['FLAG_CALIDAD'] = 'VALIDO'
df2021_taxco['OBSERVACIONES'] = ''

# Marcar inconsistencias
mask_total_inc = df2021_taxco['TOTAL_VOTOS'] != df2021_taxco['TOTAL_CALCULADO']
df2021_taxco.loc[mask_total_inc, 'FLAG_CALIDAD'] = 'TOTAL_INCORRECTO'
df2021_taxco.loc[mask_total_inc, 'OBSERVACIONES'] = 'Total difiere de suma de componentes'

mask_excede = df2021_taxco['TOTAL_VOTOS'] > df2021_taxco['LISTA_NOMINAL']
df2021_taxco.loc[mask_excede, 'FLAG_CALIDAD'] = 'EXCEDE_LISTA'
df2021_taxco.loc[mask_excede, 'OBSERVACIONES'] = 'Total votos mayor a lista nominal'

# Verificar duplicados
duplicados_2021 = df2021_taxco.duplicated(subset=['SECCION_INT', 'CASILLAS'], keep=False).sum()

print(f"  ✓ Casillas válidas: {(df2021_taxco['FLAG_CALIDAD'] == 'VALIDO').sum()}")
print(f"  ⚠ Con problemas: {(df2021_taxco['FLAG_CALIDAD'] != 'VALIDO').sum()}")
print(f"  • Duplicados: {duplicados_2021}")
print(f"  • Total casillas: {len(df2021_taxco)}")

# Exportar
archivo_2021 = OUT_DIR / "2021_limpio.csv"
df2021_taxco.to_csv(archivo_2021, index=False, encoding='utf-8-sig')
print(f"  ✓ Guardado en: {archivo_2021.name}")

# =============================================
# 2024
# =============================================
print("\n[2/2] PROCESANDO 2024...")

df2024 = pd.read_csv(BASE_PATH / "2024.csv", encoding="latin1")
df2024["SECCION_INT"] = to_int(df2024["SECCION"])

df2024_taxco = df2024[
    (df2024["ID_MUNICIPIO"] == ID_MUNICIPIO_TAXCO) &
    (df2024["SECCION_INT"].between(SECCION_MIN, SECCION_MAX))
].copy()

print(f"  • Registros originales: {len(df2024_taxco)}")

# Normalizar columnas numéricas
for col in ["NUM_VOTOS_VALIDOS", "NUM_VOTOS_CAN_NREG", "NUM_VOTOS_NULOS", "TOTAL_VOTOS", "LISTA_NOMINAL"]:
    if col in df2024_taxco.columns:
        df2024_taxco[col] = to_num(df2024_taxco[col])

# Validar integridad
df2024_taxco['TOTAL_CALCULADO'] = (
    df2024_taxco['NUM_VOTOS_VALIDOS'].fillna(0) +
    df2024_taxco['NUM_VOTOS_CAN_NREG'].fillna(0) +
    df2024_taxco['NUM_VOTOS_NULOS'].fillna(0)
)

df2024_taxco['FLAG_CALIDAD'] = 'VALIDO'
df2024_taxco['OBSERVACIONES'] = ''

# Marcar inconsistencias
mask_total_inc = df2024_taxco['TOTAL_VOTOS'] != df2024_taxco['TOTAL_CALCULADO']
df2024_taxco.loc[mask_total_inc, 'FLAG_CALIDAD'] = 'TOTAL_INCORRECTO'
df2024_taxco.loc[mask_total_inc, 'OBSERVACIONES'] = 'Total difiere de suma de componentes'

mask_excede = df2024_taxco['TOTAL_VOTOS'] > df2024_taxco['LISTA_NOMINAL']
df2024_taxco.loc[mask_excede, 'FLAG_CALIDAD'] = 'EXCEDE_LISTA'
df2024_taxco.loc[mask_excede, 'OBSERVACIONES'] = 'Total votos mayor a lista nominal'

# Verificar duplicados
duplicados_2024 = df2024_taxco.duplicated(subset=['SECCION_INT', 'CASILLAS'], keep=False).sum()

print(f"  ✓ Casillas válidas: {(df2024_taxco['FLAG_CALIDAD'] == 'VALIDO').sum()}")
print(f"  ⚠ Con problemas: {(df2024_taxco['FLAG_CALIDAD'] != 'VALIDO').sum()}")
print(f"  • Duplicados: {duplicados_2024}")
print(f"  • Total casillas: {len(df2024_taxco)}")

# Exportar
archivo_2024 = OUT_DIR / "2024_limpio.csv"
df2024_taxco.to_csv(archivo_2024, index=False, encoding='utf-8-sig')
print(f"  ✓ Guardado en: {archivo_2024.name}")

print("\n" + "="*80)
print("✓ LIMPIEZA DE 2021 Y 2024 COMPLETADA")
print("="*80)

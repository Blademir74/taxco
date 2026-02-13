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

print("="*80)
print("LIMPIEZA Y FILTRADO - INE E INEGI")
print("="*80)

# =============================================
# PADRÓN INE
# =============================================
print("\n[1/2] PROCESANDO PADRÓN INE...")

ine = pd.read_csv(BASE_PATH / "ine.csv", encoding="latin1")

# Normalizar nombres de columnas (tienen \n)
ine.columns = ine.columns.str.replace('\n', '_').str.upper()

print(f"  • Columnas detectadas: {list(ine.columns)}")

# Identificar columnas correctas
col_municipio = [c for c in ine.columns if 'MUNICIPIO' in c and 'CLAVE' in c][0]
col_seccion = 'SECCION'
col_hombres = [c for c in ine.columns if 'HOMBRES' in c][0]
col_mujeres = [c for c in ine.columns if 'MUJERES' in c][0]
col_nominal = [c for c in ine.columns if 'NOMINAL' in c and 'LISTA' in c][0]

ine['SECCION_INT'] = to_int(ine[col_seccion])

ine_taxco = ine[
    (ine[col_municipio] == ID_MUNICIPIO_TAXCO) &
    (ine['SECCION_INT'].between(SECCION_MIN, SECCION_MAX))
].copy()

print(f"  • Registros originales INE: {len(ine)}")
print(f"  • Registros Taxco: {len(ine_taxco)}")

# Verificar duplicados
duplicados_ine = ine_taxco.duplicated(subset=['SECCION_INT'], keep=False).sum()
print(f"  • Duplicados: {duplicados_ine}")

# Estandarizar nombres
ine_limpio = pd.DataFrame({
    'SECCION': ine_taxco['SECCION_INT'],
    'LISTA_HOMBRES': ine_taxco[col_hombres],
    'LISTA_MUJERES': ine_taxco[col_mujeres],
    'LISTA_NOMINAL_OFICIAL': ine_taxco[col_nominal],
    'ANIO_PADRON': 2024,  # Asumiendo corte 2024, ajusta si es necesario
    'FUENTE': 'ine.csv'
})

# Validación
print(f"  ✓ Secciones únicas: {ine_limpio['SECCION'].nunique()}")
print(f"  ✓ Rango de lista nominal: {ine_limpio['LISTA_NOMINAL_OFICIAL'].min()} - {ine_limpio['LISTA_NOMINAL_OFICIAL'].max()}")

archivo_ine = OUT_DIR / "ine_limpio.csv"
ine_limpio.to_csv(archivo_ine, index=False, encoding='utf-8-sig')
print(f"  ✓ Guardado en: {archivo_ine.name}")

# =============================================
# INDICADORES INEGI
# =============================================
print("\n[2/2] PROCESANDO INDICADORES INEGI...")

inegi = pd.read_csv(BASE_PATH / "INEGI_limpio.csv", encoding="latin1")

print(f"  • Registros originales: {len(inegi)}")
print(f"  • Columnas: {list(inegi.columns)}")

inegi_taxco = inegi[
    (inegi["CLAVE MUNICIPIO"] == ID_MUNICIPIO_TAXCO) &
    (inegi["SECCION"].between(SECCION_MIN, SECCION_MAX))
].copy()

print(f"  • Registros Taxco: {len(inegi_taxco)}")

# Verificar duplicados
duplicados_inegi = inegi_taxco.duplicated(subset=['SECCION'], keep=False).sum()
print(f"  • Duplicados: {duplicados_inegi}")

# Estandarizar
inegi_limpio = pd.DataFrame({
    'SECCION': inegi_taxco['SECCION'],
    'DISTRITO_FEDERAL': inegi_taxco['DISTRITO FEDERAL'],
    'CLAVE_MUNICIPIO': inegi_taxco['CLAVE MUNICIPIO'],
    'POBTOT': inegi_taxco['POBTOT'],
    'GRADO_PROM_ESCOLAR': inegi_taxco['GRAPROES'],
    
    # Salud
    'POB_SIN_DERECHOHAB': inegi_taxco['PSINDER'],
    'POB_CON_DERECHOHAB': inegi_taxco['PDER_SS'],
    'PCT_SIN_DERECHOHAB': (inegi_taxco['PSINDER'] / inegi_taxco['POBTOT'] * 100).round(2),
    
    # Mercado laboral
    'PEA': inegi_taxco['PEA'],
    'PE_INACTIVA': inegi_taxco['PE_INAC'],
    'POB_OCUPADA': inegi_taxco['POCUPADA'],
    'POB_DESOCUPADA': inegi_taxco['PDESOCUP'],
    
    # Vivienda
    'NUM_VIVIENDAS_PARTICULARES': inegi_taxco['OCUPVIVPAR'],
    'PROMEDIO_OCUPANTES': inegi_taxco['PROM_OCUP'],
    
    # Servicios TIC
    'VPH_AUTOM': inegi_taxco['VPH_AUTOM'],
    'VPH_PC': inegi_taxco['VPH_PC'],
    'VPH_CEL': inegi_taxco['VPH_CEL'],
    'VPH_INTERNET': inegi_taxco['VPH_INTER'],
    
    'ANIO_INEGI': 2020,  # Censo 2020
    'FUENTE': 'INEGI_limpio.csv'
})

print(f"  ✓ Secciones únicas: {inegi_limpio['SECCION'].nunique()}")
print(f"  ✓ Población total: {inegi_limpio['POBTOT'].sum():,}")
print(f"  ✓ Promedio grado escolar: {inegi_limpio['GRADO_PROM_ESCOLAR'].mean():.2f}")

archivo_inegi = OUT_DIR / "inegi_limpio.csv"
inegi_limpio.to_csv(archivo_inegi, index=False, encoding='utf-8-sig')
print(f"  ✓ Guardado en: {archivo_inegi.name}")

print("\n" + "="*80)
print("✓ LIMPIEZA DE INE E INEGI COMPLETADA")
print("="*80)
print(f"\nArchivos generados en: {OUT_DIR}")
print("  - 2018_limpio.csv")
print("  - 2021_limpio.csv")
print("  - 2024_limpio.csv")
print("  - ine_limpio.csv")
print("  - inegi_limpio.csv")

import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

BASE_PATH = Path(r"C:\Users\campe\Desktop\taxco")
OUT_DIR = BASE_PATH / "datos_limpios"
OUT_DIR.mkdir(exist_ok=True)

print("="*80)
print("LIMPIEZA DE DATOS 2018 - UNIFICACIÓN DE SISTEMAS DE CONTEO")
print("="*80)

# Cargar archivo original
df = pd.read_csv(BASE_PATH / "2018.csv", encoding="latin1")

print(f"\n[1/6] Datos originales: {len(df)} registros")

# Separar en dos bloques
df['BLOQUE'] = df['LISTA_NOMINAL'].apply(lambda x: 'BASICAS' if x > 0 else 'ESPECIALES')

basicas = df[df['BLOQUE'] == 'BASICAS'].copy()
especiales = df[df['BLOQUE'] == 'ESPECIALES'].copy()

print(f"  • Casillas básicas (1,2,3,4,6): {len(basicas)}")
print(f"  • Casillas especiales (B,C,E): {len(especiales)}")

# BLOQUE 1: CASILLAS BÁSICAS - Ya están correctas
print(f"\n[2/6] Procesando casillas básicas...")

basicas_clean = basicas[[
    'ID_ESTADO', 'NOMBRE_ESTADO', 'ID_DISTRITO_LOCAL', 
    'CABECERA_DISTRITAL_LOCAL', 'ID_MUNICIPIO', 'MUNICIPIO',
    'SECCION', 'CASILLA',
    'PAN', 'PRI', 'PRD', 'PVEM', 'PT', 'MC', 'NA', 'MORENA', 'ES',
    'PPG', 'IH', 'CG', 'PSM', 'PSG',
    'CAND_IND1', 'CAND_IND2', 'CAND_IND4', 'CAND_IND5', 
    'CAND_IND7', 'CAND_IND8', 'CAND_IND9',
    'PAN_PRD_MC', 'PAN_PRD', 'PAN_MC', 'PRD_MC', 'PRI_PVEM', 'MORENA_ES',
    'NUM_VOTOS_VALIDOS', 'NUM_VOTOS_CAN_NREG', 'NUM_VOTOS_NULOS',
    'TOTAL_VOTOS', 'LISTA_NOMINAL'
]].copy()

# Validar integridad
basicas_clean['TOTAL_CALCULADO'] = (
    basicas_clean['NUM_VOTOS_VALIDOS'].fillna(0) +
    basicas_clean['NUM_VOTOS_CAN_NREG'].fillna(0) +
    basicas_clean['NUM_VOTOS_NULOS'].fillna(0)
)

basicas_clean['FLAG_CALIDAD'] = 'VALIDO'
basicas_clean['OBSERVACIONES'] = ''

# Marcar inconsistencias
mask_total_inc = basicas_clean['TOTAL_VOTOS'] != basicas_clean['TOTAL_CALCULADO']
basicas_clean.loc[mask_total_inc, 'FLAG_CALIDAD'] = 'TOTAL_INCORRECTO'
basicas_clean.loc[mask_total_inc, 'OBSERVACIONES'] = 'Total difiere de suma de componentes'

mask_excede = basicas_clean['TOTAL_VOTOS'] > basicas_clean['LISTA_NOMINAL']
basicas_clean.loc[mask_excede, 'FLAG_CALIDAD'] = 'EXCEDE_LISTA'
basicas_clean.loc[mask_excede, 'OBSERVACIONES'] = 'Total votos mayor a lista nominal'

print(f"  ✓ Casillas válidas: {(basicas_clean['FLAG_CALIDAD'] == 'VALIDO').sum()}")
print(f"  ⚠ Con problemas: {(basicas_clean['FLAG_CALIDAD'] != 'VALIDO').sum()}")

# BLOQUE 2: CASILLAS ESPECIALES - Usar columnas .1
print(f"\n[3/6] Procesando casillas especiales (B, C, E)...")

# Verificar si las columnas .1 tienen datos válidos
print(f"  • LISTA_NOMINAL (original): {especiales['LISTA_NOMINAL'].sum()}")
print(f"  • LISTA_NOMINAL.1 (alt): {especiales['LISTA_NOMINAL.1'].sum()}")
print(f"  • TOTAL_VOTOS (original): {especiales['TOTAL_VOTOS'].sum()}")
print(f"  • TOTAL_VOTOS.1 (alt): {especiales['TOTAL_VOTOS.1'].sum()}")

# Usar columnas .1 para casillas especiales
especiales_clean = especiales.copy()

# Reemplazar con valores de columnas .1 si son mayores
especiales_clean['LISTA_NOMINAL_CORREGIDA'] = especiales_clean[['LISTA_NOMINAL', 'LISTA_NOMINAL.1']].max(axis=1)
especiales_clean['TOTAL_VOTOS_CORREGIDO'] = especiales_clean[['TOTAL_VOTOS', 'TOTAL_VOTOS.1']].max(axis=1)
especiales_clean['NUM_VOTOS_NULOS_CORREGIDO'] = especiales_clean['NUM_VOTOS_NULOS.1'].fillna(
    especiales_clean['NUM_VOTOS_NULOS']
)

especiales_clean['FLAG_CALIDAD'] = 'CASILLA_ESPECIAL_CORREGIDA'
especiales_clean['OBSERVACIONES'] = 'Datos tomados de columnas alternas (.1)'

# Unificar estructura
especiales_clean = especiales_clean[[
    'ID_ESTADO', 'NOMBRE_ESTADO', 'ID_DISTRITO_LOCAL',
    'CABECERA_DISTRITAL_LOCAL', 'ID_MUNICIPIO', 'MUNICIPIO',
    'SECCION', 'CASILLA',
    'PAN', 'PRI', 'PRD', 'PVEM', 'PT', 'MC', 'NA', 'MORENA', 'ES',
    'PPG', 'IH', 'CG', 'PSM', 'PSG',
    'CAND_IND1', 'CAND_IND2', 'CAND_IND4', 'CAND_IND5',
    'CAND_IND7', 'CAND_IND8', 'CAND_IND9',
    'PAN_PRD_MC', 'PAN_PRD', 'PAN_MC', 'PRD_MC', 'PRI_PVEM', 'MORENA_ES',
    'NUM_VOTOS_VALIDOS', 'NUM_VOTOS_CAN_NREG'
]].copy()

especiales_clean['NUM_VOTOS_NULOS'] = especiales['NUM_VOTOS_NULOS.1']
especiales_clean['TOTAL_VOTOS'] = especiales['TOTAL_VOTOS.1']
especiales_clean['LISTA_NOMINAL'] = especiales['LISTA_NOMINAL.1']
especiales_clean['FLAG_CALIDAD'] = 'CASILLA_ESPECIAL'
especiales_clean['OBSERVACIONES'] = 'Casilla especial (B/C/E) corregida'
especiales_clean['TOTAL_CALCULADO'] = (
    especiales_clean['NUM_VOTOS_VALIDOS'].fillna(0) +
    especiales_clean['NUM_VOTOS_CAN_NREG'].fillna(0) +
    especiales_clean['NUM_VOTOS_NULOS'].fillna(0)
)

print(f"  ✓ Casillas especiales procesadas: {len(especiales_clean)}")

# UNIFICAR AMBOS BLOQUES
print(f"\n[4/6] Unificando datos...")

df_limpio = pd.concat([basicas_clean, especiales_clean], ignore_index=True)

# Eliminar duplicados (casillas C repetidas)
print(f"\n[5/6] Eliminando duplicados reales...")
print(f"  • Registros antes: {len(df_limpio)}")

# Identificar duplicados por SECCION + CASILLA
df_limpio['ES_DUPLICADO'] = df_limpio.duplicated(subset=['SECCION', 'CASILLA'], keep='first')
duplicados = df_limpio[df_limpio['ES_DUPLICADO']].copy()

print(f"  • Duplicados encontrados: {len(duplicados)}")
print("\nCasillas duplicadas a eliminar:")
print(duplicados[['SECCION', 'CASILLA', 'TOTAL_VOTOS', 'LISTA_NOMINAL']])

# Eliminar duplicados manteniendo el primero
df_limpio = df_limpio[~df_limpio['ES_DUPLICADO']].drop(columns=['ES_DUPLICADO'])

print(f"  • Registros después: {len(df_limpio)}")

# VALIDACIÓN FINAL
print(f"\n[6/6] Validación final...")

total_validos = (df_limpio['FLAG_CALIDAD'] == 'VALIDO').sum()
total_especiales = (df_limpio['FLAG_CALIDAD'] == 'CASILLA_ESPECIAL').sum()
total_problemas = (df_limpio['FLAG_CALIDAD'].isin(['TOTAL_INCORRECTO', 'EXCEDE_LISTA'])).sum()

print(f"  ✓ Casillas válidas: {total_validos}")
print(f"  ✓ Casillas especiales corregidas: {total_especiales}")
print(f"  ⚠ Casillas con flags de calidad: {total_problemas}")
print(f"  TOTAL: {len(df_limpio)} casillas")

# Verificar totales vs lista nominal
excesos = (df_limpio['TOTAL_VOTOS'] > df_limpio['LISTA_NOMINAL']).sum()
print(f"\n  Casillas con TOTAL > LISTA después de limpieza: {excesos}")

# EXPORTAR
archivo_salida = OUT_DIR / "2018_limpio.csv"
df_limpio.to_csv(archivo_salida, index=False, encoding='utf-8-sig')

print(f"\n{'='*80}")
print(f"✓ LIMPIEZA COMPLETADA")
print(f"{'='*80}")
print(f"Archivo generado: {archivo_salida}")

# Estadísticas finales
print(f"\nESTADÍSTICAS DE CALIDAD:")
print(df_limpio['FLAG_CALIDAD'].value_counts())

print(f"\nCASILLAS POR TIPO:")
print(df_limpio['CASILLA'].value_counts().sort_index())

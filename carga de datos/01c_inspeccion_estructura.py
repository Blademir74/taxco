import pandas as pd
from pathlib import Path

BASE_PATH = Path(r"C:\Users\campe\Desktop\taxco")

print("="*80)
print("INSPECCIÓN DE ESTRUCTURA - 2018.csv")
print("="*80)

# Cargar sin procesar
df = pd.read_csv(BASE_PATH / "2018.csv", encoding="latin1")

print(f"\n[1] DIMENSIONES DEL ARCHIVO")
print(f"Filas totales: {len(df)}")
print(f"Columnas totales: {len(df.columns)}")

print(f"\n[2] NOMBRES DE COLUMNAS (todas)")
for i, col in enumerate(df.columns, 1):
    print(f"  {i:2}. {col}")

print(f"\n[3] COLUMNAS DUPLICADAS O SOSPECHOSAS")
cols_counter = {}
for col in df.columns:
    cols_counter[col] = cols_counter.get(col, 0) + 1

for col, count in cols_counter.items():
    if count > 1 or '.1' in col:
        print(f"  ⚠️  {col} (aparece {count} veces)")

print(f"\n[4] VALORES ÚNICOS EN COLUMNAS CLAVE")
print(f"SECCION valores únicos: {df['SECCION'].nunique()}")
print(f"CASILLA valores únicos: {df['CASILLA'].nunique()}")
print(f"Casillas únicas por tipo:")
print(df['CASILLA'].value_counts().head(20))

print(f"\n[5] ESTADÍSTICAS DE LISTA_NOMINAL")
print(f"Valores cero: {(df['LISTA_NOMINAL'] == 0).sum()}")
print(f"Valores nulos: {df['LISTA_NOMINAL'].isna().sum()}")
print(f"Distribución:")
print(df['LISTA_NOMINAL'].describe())

print(f"\n[6] ANÁLISIS DE NUM_VOTOS_NULOS")
if 'NUM_VOTOS_NULOS' in df.columns:
    print(f"Valores nulos en NUM_VOTOS_NULOS: {df['NUM_VOTOS_NULOS'].isna().sum()}")
    print(f"Valores distintos de cero: {(df['NUM_VOTOS_NULOS'] > 0).sum()}")
else:
    print("⚠️  Columna NUM_VOTOS_NULOS NO ENCONTRADA")

print(f"\n[7] MUESTRA DE REGISTROS CON LISTA_NOMINAL = 0")
zeros = df[df['LISTA_NOMINAL'] == 0][['SECCION', 'CASILLA', 'TOTAL_VOTOS', 'LISTA_NOMINAL', 'NUM_VOTOS_VALIDOS']].head(10)
print(zeros.to_string(index=False))

print(f"\n[8] MUESTRA DE REGISTROS CON LISTA_NOMINAL > 0")
validos = df[df['LISTA_NOMINAL'] > 0][['SECCION', 'CASILLA', 'TOTAL_VOTOS', 'LISTA_NOMINAL', 'NUM_VOTOS_VALIDOS']].head(10)
print(validos.to_string(index=False))

# Verificar si hay dos bloques de datos
print(f"\n[9] DETECCIÓN DE BLOQUES DE DATOS")
df['tiene_ln'] = df['LISTA_NOMINAL'] > 0
print(f"Registros con LISTA_NOMINAL > 0: {df['tiene_ln'].sum()}")
print(f"Registros con LISTA_NOMINAL = 0: {(~df['tiene_ln']).sum()}")

# Ver si hay patrón por tipo de casilla
print(f"\n[10] LISTA_NOMINAL POR TIPO DE CASILLA")
casilla_ln = df.groupby('CASILLA')['LISTA_NOMINAL'].agg(['count', 'sum', 'mean'])
print(casilla_ln.head(20))

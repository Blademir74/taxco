import pandas as pd
from pathlib import Path

BASE_PATH = Path(r"C:\Users\campe\Desktop\taxco\datos_limpios")

print("="*80)
print("VALIDACIÓN CRUZADA DE ARCHIVOS LIMPIOS")
print("="*80)

# Cargar archivos limpios
e2018 = pd.read_csv(BASE_PATH / "2018_limpio.csv")
e2021 = pd.read_csv(BASE_PATH / "2021_limpio.csv")
e2024 = pd.read_csv(BASE_PATH / "2024_limpio.csv")
ine = pd.read_csv(BASE_PATH / "ine_limpio.csv")
inegi = pd.read_csv(BASE_PATH / "inegi_limpio.csv")

print("\n[1/3] CONTEO DE SECCIONES POR FUENTE")
print("-"*80)
print(f"  • 2018: {e2018['SECCION'].nunique()} secciones únicas")
print(f"  • 2021: {e2021['SECCION_INT'].nunique()} secciones únicas")
print(f"  • 2024: {e2024['SECCION_INT'].nunique()} secciones únicas")
print(f"  • INE: {ine['SECCION'].nunique()} secciones")
print(f"  • INEGI: {inegi['SECCION'].nunique()} secciones")

print("\n[2/3] COBERTURA DE SECCIONES")
print("-"*80)
secciones_ine = set(ine['SECCION'].unique())
secciones_2018 = set(e2018['SECCION'].unique())
secciones_2021 = set(e2021['SECCION_INT'].dropna().unique())
secciones_2024 = set(e2024['SECCION_INT'].dropna().unique())
secciones_inegi = set(inegi['SECCION'].unique())

print(f"  • Secciones en INE pero no en 2018: {secciones_ine - secciones_2018}")
print(f"  • Secciones en INE pero no en 2021: {secciones_ine - secciones_2021}")
print(f"  • Secciones en INE pero no en 2024: {secciones_ine - secciones_2024}")
print(f"  • Secciones en INEGI pero no en INE: {secciones_inegi - secciones_ine}")

print("\n[3/3] ESTADÍSTICAS DE CALIDAD")
print("-"*80)
print("2018:")
print(e2018['FLAG_CALIDAD'].value_counts())
print("\n2021:")
print(e2021['FLAG_CALIDAD'].value_counts())
print("\n2024:")
print(e2024['FLAG_CALIDAD'].value_counts())

print("\n" + "="*80)
print("✓ VALIDACIÓN COMPLETADA")
print("="*80)
print("\nARCHIVOS LISTOS PARA CARGA A SQL")

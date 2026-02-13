import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import warnings
warnings.filterwarnings('ignore')

# ============================================
# CONFIGURACIÓN
# ============================================
BASE_PATH = Path(r"C:\Users\campe\Desktop\taxco\datos_limpios")

DB_USER = 'postgres'
DB_PASSWORD = 'postgres123'
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'taxco_electoral'

password_encoded = quote_plus(DB_PASSWORD)
conn_string = f'postgresql://{DB_USER}:{password_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(conn_string, connect_args={'options': '-c client_encoding=utf8'})

print("="*80)
print("ETL - CARGA DE DATOS A POSTGRESQL")
print("="*80)

# Probar conexión
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"\n✓ Conexión exitosa")
        print(f"  {version[:60]}...")
except Exception as e:
    print(f"\n❌ Error: {e}")
    exit()

# ============================================
# FUNCIONES AUXILIARES
# ============================================
def to_int(series):
    """Convierte a entero manejando NaN y anexas (2177B -> 2177)"""
    s = series.astype(str).str.extract(r"(^\d+)", expand=False)
    return pd.to_numeric(s, errors="coerce").astype("Int64")

def to_num(series):
    """Convierte a numérico"""
    return pd.to_numeric(series, errors="coerce")

# ============================================
# FASE 1: CARGAR SECCIONES
# ============================================
print("\n[1/6] CARGANDO SECCIONES...")

secciones_set = set()

e2018 = pd.read_csv(BASE_PATH / "2018_limpio.csv")
secciones_set.update(e2018['SECCION'].unique())

e2021 = pd.read_csv(BASE_PATH / "2021_limpio.csv")
secciones_set.update(e2021['SECCION_INT'].dropna().unique())

e2024 = pd.read_csv(BASE_PATH / "2024_limpio.csv")
secciones_set.update(e2024['SECCION_INT'].dropna().unique())

ine = pd.read_csv(BASE_PATH / "ine_limpio.csv")
secciones_set.update(ine['SECCION'].unique())

inegi = pd.read_csv(BASE_PATH / "inegi_limpio.csv")
secciones_set.update(inegi['SECCION'].unique())

secciones_df = pd.DataFrame({
    'id_municipio': 56,
    'seccion': sorted([int(s) for s in secciones_set if pd.notna(s)]),
    'distrito_local': 21,
    'distrito_federal': 2,
    'tiene_datos_electorales': True
})

secciones_sin_casillas = {2171, 2172}
secciones_df.loc[secciones_df['seccion'].isin(secciones_sin_casillas), 'tiene_datos_electorales'] = False
secciones_df.loc[secciones_df['seccion'].isin(secciones_sin_casillas), 'observaciones'] = 'Seccion sin casillas instaladas'

print(f"  • Total: {len(secciones_df)}")
print(f"  • Con datos electorales: {secciones_df['tiene_datos_electorales'].sum()}")

secciones_df.to_sql('seccion', engine, if_exists='append', index=False)
print("  ✓ Secciones cargadas")

with engine.connect() as conn:
    df_seccion_pk = pd.read_sql("SELECT pk_seccion, seccion FROM seccion WHERE id_municipio = 56", conn)

print(f"  ✓ Mapeadas {len(df_seccion_pk)} secciones")

# ============================================
# FASE 2: CARGAR PADRÓN INE
# ============================================
print("\n[2/6] CARGANDO PADRÓN INE...")

ine = pd.read_csv(BASE_PATH / "ine_limpio.csv")
ine = ine.merge(df_seccion_pk, left_on='SECCION', right_on='seccion', how='left')

if ine['pk_seccion'].isna().any():
    print(f"  ⚠️ {ine['pk_seccion'].isna().sum()} sin pk_seccion")
    ine = ine[ine['pk_seccion'].notna()]

padron_df = pd.DataFrame({
    'pk_seccion': ine['pk_seccion'].astype(int),
    'lista_hombres': ine['LISTA_HOMBRES'],
    'lista_mujeres': ine['LISTA_MUJERES'],
    'lista_nominal_oficial': ine['LISTA_NOMINAL_OFICIAL'],
    'anio_padron': ine['ANIO_PADRON'],
    'fuente': ine['FUENTE']
})

padron_df.to_sql('padron_ine', engine, if_exists='append', index=False)
print(f"  ✓ {len(padron_df)} registros cargados")

# ============================================
# FASE 3: CARGAR INDICADORES INEGI
# ============================================
print("\n[3/6] CARGANDO INDICADORES INEGI...")

inegi = pd.read_csv(BASE_PATH / "inegi_limpio.csv")
inegi = inegi.merge(df_seccion_pk, left_on='SECCION', right_on='seccion', how='left')

if inegi['pk_seccion'].isna().any():
    print(f"  ⚠️ {inegi['pk_seccion'].isna().sum()} sin pk_seccion")
    inegi = inegi[inegi['pk_seccion'].notna()]

carencias_df = pd.DataFrame({
    'pk_seccion': inegi['pk_seccion'].astype(int),
    'anio_inegi': inegi['ANIO_INEGI'],
    'pobtot': inegi['POBTOT'],
    'grado_prom_escolar': inegi['GRADO_PROM_ESCOLAR'],
    'pob_sin_derechohab': inegi['POB_SIN_DERECHOHAB'],
    'pob_con_derechohab': inegi['POB_CON_DERECHOHAB'],
    'pct_sin_derechohab': inegi['PCT_SIN_DERECHOHAB'],
    'pea': inegi['PEA'],
    'pe_inactiva': inegi['PE_INACTIVA'],
    'pob_ocupada': inegi['POB_OCUPADA'],
    'pob_desocupada': inegi['POB_DESOCUPADA'],
    'num_viviendas_particulares': inegi['NUM_VIVIENDAS_PARTICULARES'],
    'promedio_ocupantes': inegi['PROMEDIO_OCUPANTES'],
    'vph_autom': inegi['VPH_AUTOM'],
    'vph_pc': inegi['VPH_PC'],
    'vph_cel': inegi['VPH_CEL'],
    'vph_internet': inegi['VPH_INTERNET'],
    'fuente': inegi['FUENTE']
})

carencias_df.to_sql('carencias_inegi', engine, if_exists='append', index=False)
print(f"  ✓ {len(carencias_df)} registros cargados")

# ============================================
# FASE 4: CARGAR PARTIDOS
# ============================================
print("\n[4/6] CARGANDO CATÁLOGO DE PARTIDOS...")

partidos_all = [
    ('PAN', 'Partido Accion Nacional', False, 2018, None),
    ('PRI', 'Partido Revolucionario Institucional', False, 2018, None),
    ('PRD', 'Partido de la Revolucion Democratica', False, 2018, None),
    ('PVEM', 'Partido Verde Ecologista de Mexico', False, 2018, None),
    ('PT', 'Partido del Trabajo', False, 2018, None),
    ('MC', 'Movimiento Ciudadano', False, 2018, None),
    ('NA', 'Nueva Alianza', False, 2018, 2018),
    ('MORENA', 'Movimiento Regeneracion Nacional', False, 2018, None),
    ('ES', 'Encuentro Social', False, 2018, 2024),
    ('PPG', 'Partido del Pueblo Guerrerense', False, 2018, None),
    ('IH', 'Impulso Guerrerense', False, 2018, None),
    ('CG', 'Ciudadanos Guerrerenses', False, 2018, None),
    ('PSM', 'Partido Socialista Mexicano', False, 2018, None),
    ('PSG', 'Partido Social Guerrerense', False, 2018, None),
    ('PAN_PRD_MC', 'Coalicion PAN-PRD-MC', True, 2018, 2018),
    ('PAN_PRD', 'Coalicion PAN-PRD', True, 2018, 2018),
    ('PAN_MC', 'Coalicion PAN-MC', True, 2018, 2018),
    ('PRD_MC', 'Coalicion PRD-MC', True, 2018, 2018),
    ('PRI_PVEM', 'Coalicion PRI-PVEM', True, 2018, 2018),
    ('MORENA_ES', 'Coalicion MORENA-ES', True, 2018, 2018),
    ('RSP', 'Redes Sociales Progresistas', False, 2021, None),
    ('FXP', 'Fuerza por Mexico', False, 2021, None),
    ('PES', 'Partido Encuentro Solidario', False, 2021, None),
]

partidos_df = pd.DataFrame(partidos_all, columns=[
    'clave_partido', 'nombre_largo', 'es_coalicion', 'anio_inicio', 'anio_fin'
])

partidos_df = partidos_df.drop_duplicates(subset=['clave_partido'], keep='first')
partidos_df.to_sql('partido', engine, if_exists='append', index=False)
print(f"  ✓ {len(partidos_df)} partidos cargados")

with engine.connect() as conn:
    df_partido_pk = pd.read_sql("SELECT id_partido, clave_partido FROM partido", conn)

print(f"  ✓ Mapeados {len(df_partido_pk)} partidos")

# ============================================
# FASE 5: CARGAR RESULTADOS ELECTORALES
# ============================================
print("\n[5/6] CARGANDO RESULTADOS ELECTORALES...")

def cargar_resultados_anio(anio, archivo, id_eleccion, col_seccion, col_casilla):
    print(f"\n  • Procesando {anio}...")
    
    df = pd.read_csv(BASE_PATH / archivo)
    df['SECCION_CLEAN'] = to_int(df[col_seccion])
    
    # Convertir casilla a string
    df[col_casilla] = df[col_casilla].astype(str).str.strip()
    
    df = df.merge(df_seccion_pk, left_on='SECCION_CLEAN', right_on='seccion', how='left')
    
    if df['pk_seccion'].isna().any():
        print(f"    ⚠️ {df['pk_seccion'].isna().sum()} sin pk_seccion")
        df = df[df['pk_seccion'].notna()]
    
    print(f"    • Casillas: {len(df)}")
    
    # Insertar casillas
    casillas_df = pd.DataFrame({
        'pk_seccion': df['pk_seccion'].astype(int),
        'id_eleccion': id_eleccion,
        'clave_casilla': df[col_casilla].astype(str),
        'tipo_casilla': df[col_casilla].astype(str).apply(lambda x: 
            'BASICA' if x.isdigit() else 
            'CONTIGUA' if 'B' in str(x).upper() or 'C' in str(x).upper() else
            'ESPECIAL' if 'E' in str(x).upper() else 'OTRA'
        )
    })
    
    casillas_df.to_sql('casilla', engine, if_exists='append', index=False)
    print(f"    ✓ {len(casillas_df)} casillas insertadas")
    
    # Obtener pk_casilla
    with engine.connect() as conn:
        query = f"""
        SELECT pk_casilla, pk_seccion, clave_casilla 
        FROM casilla 
        WHERE id_eleccion = {id_eleccion}
        """
        df_casilla_pk = pd.read_sql(query, conn)
    
    # Convertir clave_casilla a string también
    df_casilla_pk['clave_casilla'] = df_casilla_pk['clave_casilla'].astype(str)
    
    df = df.merge(
        df_casilla_pk,
        left_on=['pk_seccion', col_casilla],
        right_on=['pk_seccion', 'clave_casilla'],
        how='left'
    )
    
    # Insertar resultados
    resultados_df = pd.DataFrame({
        'pk_casilla': df['pk_casilla'].astype(int),
        'num_votos_validos': df['NUM_VOTOS_VALIDOS'].fillna(0).astype(int),
        'num_votos_cannreg': df['NUM_VOTOS_CAN_NREG'].fillna(0).astype(int),
        'num_votos_nulos': df['NUM_VOTOS_NULOS'].fillna(0).astype(int),
        'total_votos': df['TOTAL_VOTOS'].fillna(0).astype(int),
        'lista_nominal_acta': df['LISTA_NOMINAL'].fillna(0).astype(int),
        'flag_calidad': df['FLAG_CALIDAD'],
        'observaciones_calidad': df['OBSERVACIONES'],
        'fuente': archivo
    })
    
    resultados_df.to_sql('resultados_electorales', engine, if_exists='append', index=False)
    print(f"    ✓ {len(resultados_df)} resultados insertados")
    
    return df, df_casilla_pk


df_2018, _ = cargar_resultados_anio(2018, '2018_limpio.csv', 1, 'SECCION', 'CASILLA')
df_2021, _ = cargar_resultados_anio(2021, '2021_limpio.csv', 2, 'SECCION_INT', 'CASILLAS')
df_2024, _ = cargar_resultados_anio(2024, '2024_limpio.csv', 3, 'SECCION_INT', 'CASILLAS')

print("\n  ✓ Resultados electorales cargados")

# ============================================
# FASE 6: CARGAR VOTOS POR PARTIDO (SIMPLIFICADO)
# ============================================
print("\n[6/6] CARGANDO VOTOS POR PARTIDO...")
print("  ⏭️  OMITIDO por ahora (requiere mapeo complejo)")
print("  Puedes agregar después con queries UPDATE")

# ============================================
# RESUMEN FINAL
# ============================================
print("\n" + "="*80)
print("✓ CARGA COMPLETADA - RESUMEN")
print("="*80)

with engine.connect() as conn:
    stats = {}
    stats['secciones'] = pd.read_sql("SELECT COUNT(*) as total FROM seccion", conn).iloc[0]['total']
    stats['padron'] = pd.read_sql("SELECT COUNT(*) as total FROM padron_ine", conn).iloc[0]['total']
    stats['inegi'] = pd.read_sql("SELECT COUNT(*) as total FROM carencias_inegi", conn).iloc[0]['total']
    stats['partidos'] = pd.read_sql("SELECT COUNT(*) as total FROM partido", conn).iloc[0]['total']
    stats['casillas'] = pd.read_sql("SELECT COUNT(*) as total FROM casilla", conn).iloc[0]['total']
    stats['resultados'] = pd.read_sql("SELECT COUNT(*) as total FROM resultados_electorales", conn).iloc[0]['total']

print(f"\nRegistros cargados:")
print(f"  • Secciones: {stats['secciones']}")
print(f"  • Padrón INE: {stats['padron']}")
print(f"  • INEGI: {stats['inegi']}")
print(f"  • Partidos: {stats['partidos']}")
print(f"  • Casillas: {stats['casillas']}")
print(f"  • Resultados electorales: {stats['resultados']}")

print("\n✓ BASE DE DATOS LISTA")

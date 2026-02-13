import pandas as pd
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
print("ETL - CARGA DE VOTOS POR PARTIDO")
print("="*80)

# ============================================
# OBTENER MAPEOS
# ============================================
print("\n[0] Obteniendo mapeos de BD...")

with engine.connect() as conn:
    df_seccion_pk = pd.read_sql(
        "SELECT pk_seccion, seccion FROM seccion WHERE id_municipio = 56", 
        conn
    )
    print(f"  • Secciones: {len(df_seccion_pk)}")

with engine.connect() as conn:
    df_partido_pk = pd.read_sql(
        "SELECT id_partido, clave_partido FROM partido", 
        conn
    )
    print(f"  • Partidos: {len(df_partido_pk)}")

# ============================================
# FUNCIÓN PARA CARGAR VOTOS POR AÑO
# ============================================
def cargar_votos_partido_anio(anio, archivo, id_eleccion, col_seccion, col_casilla, columnas_partidos):
    """Carga votos por partido para un año específico"""
    print(f"\n[{anio}] Procesando votos por partido...")
    
    # Leer archivo limpio
    df = pd.read_csv(BASE_PATH / archivo)
    print(f"  • Casillas en archivo: {len(df)}")
    
    # Limpiar sección
    df['SECCION_CLEAN'] = df[col_seccion].astype(str).str.extract(r'(\d+)')[0].astype(float)
    df[col_casilla] = df[col_casilla].astype(str)
    
    # Join con pk_seccion
    df = df.merge(df_seccion_pk, left_on='SECCION_CLEAN', right_on='seccion', how='left')
    
    if df['pk_seccion'].isna().any():
        print(f"  ⚠️ {df['pk_seccion'].isna().sum()} casillas sin pk_seccion, omitiendo...")
        df = df[df['pk_seccion'].notna()]
    
    # Obtener pk_resultado para estas casillas
    with engine.connect() as conn:
        query = f"""
        SELECT re.pk_resultado, re.pk_casilla, c.pk_seccion, c.clave_casilla
        FROM resultados_electorales re
        JOIN casilla c ON c.pk_casilla = re.pk_casilla
        WHERE c.id_eleccion = {id_eleccion}
        """
        df_resultado_pk = pd.read_sql(query, conn)
    
    print(f"  • Resultados en BD: {len(df_resultado_pk)}")
    
    # Join para obtener pk_resultado
    df_resultado_pk['clave_casilla'] = df_resultado_pk['clave_casilla'].astype(str)
    
    df = df.merge(
        df_resultado_pk,
        left_on=['pk_seccion', col_casilla],
        right_on=['pk_seccion', 'clave_casilla'],
        how='inner'
    )
    
    print(f"  • Casillas con match: {len(df)}")
    
    if len(df) == 0:
        print(f"  ⚠️ No se encontraron matches")
        return
    
    # Preparar lista de votos por partido
    votos_partido_list = []
    partidos_encontrados = set()
    partidos_no_encontrados = set()
    
    for idx, row in df.iterrows():
        pk_resultado = row['pk_resultado']
        
        for col_partido in columnas_partidos:
            # Verificar que la columna existe
            if col_partido not in df.columns:
                continue
            
            votos_raw = row.get(col_partido, 0)
            
            # Convertir a numérico de forma segura
            try:
                votos = pd.to_numeric(votos_raw, errors='coerce')
                if pd.isna(votos):
                    votos = 0
                else:
                    votos = int(votos)
            except:
                votos = 0
            
            # Saltar si es 0 o negativo
            if votos <= 0:
                continue
            
            # Buscar id_partido
            partido_match = df_partido_pk[df_partido_pk['clave_partido'] == col_partido]
            
            if len(partido_match) == 0:
                partidos_no_encontrados.add(col_partido)
                continue
            
            id_partido = partido_match.iloc[0]['id_partido']
            partidos_encontrados.add(col_partido)
            
            votos_partido_list.append({
                'pk_resultado': int(pk_resultado),
                'id_partido': int(id_partido),
                'votos': votos
            })
    
    print(f"  • Partidos encontrados: {len(partidos_encontrados)}")
    if partidos_no_encontrados:
        print(f"  ⚠️ Partidos NO en BD: {sorted(partidos_no_encontrados)}")
    
    # Insertar en BD
    if len(votos_partido_list) > 0:
        votos_partido_df = pd.DataFrame(votos_partido_list)
        
        # Eliminar duplicados
        votos_partido_df = votos_partido_df.drop_duplicates(
            subset=['pk_resultado', 'id_partido'], 
            keep='first'
        )
        
        print(f"  • Registros a insertar: {len(votos_partido_df)}")
        
        votos_partido_df.to_sql(
            'resultados_partido', 
            engine, 
            if_exists='append', 
            index=False
        )
        
        print(f"  ✓ Insertados: {len(votos_partido_df)}")
        print(f"  • Total votos: {votos_partido_df['votos'].sum():,}")
        
    else:
        print(f"  ⚠️ No se generaron registros")

# ============================================
# CARGAR CADA AÑO
# ============================================

columnas_2018 = [
    'PAN', 'PRI', 'PRD', 'PVEM', 'PT', 'MC', 'NA', 'MORENA', 'ES',
    'PPG', 'IH', 'CG', 'PSM', 'PSG',
    'PAN_PRD_MC', 'PAN_PRD', 'PAN_MC', 'PRD_MC', 'PRI_PVEM', 'MORENA_ES'
]

columnas_2021 = [
    'PAN', 'PRI', 'PRD', 'PT', 'PVEM', 'MC', 'MORENA', 'PES', 'RSP', 'FXP',
    'PRI_PRD', 'PT_PVEM'
]

columnas_2024 = [
    'PAN', 'PRI', 'PRD', 'PVEM', 'PT', 'MC', 'MORENA'
]

cargar_votos_partido_anio(2018, '2018_limpio.csv', 1, 'SECCION', 'CASILLA', columnas_2018)
cargar_votos_partido_anio(2021, '2021_limpio.csv', 2, 'SECCION_INT', 'CASILLAS', columnas_2021)
cargar_votos_partido_anio(2024, '2024_limpio.csv', 3, 'SECCION_INT', 'CASILLAS', columnas_2024)

# ============================================
# VALIDACIÓN FINAL
# ============================================
print("\n" + "="*80)
print("VALIDACIÓN")
print("="*80)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT COUNT(*) as total_registros, SUM(votos) as total_votos
        FROM resultados_partido
    """))
    stats = result.fetchone()
    
    print(f"\nResultados partido:")
    print(f"  • Registros: {stats[0]:,}")
    print(f"  • Total votos: {stats[1]:,}")
    
    result = conn.execute(text("""
        SELECT e.anio, COUNT(*) as registros, SUM(rp.votos) as votos
        FROM resultados_partido rp
        JOIN resultados_electorales re ON re.pk_resultado = rp.pk_resultado
        JOIN casilla c ON c.pk_casilla = re.pk_casilla
        JOIN eleccion e ON e.id_eleccion = c.id_eleccion
        GROUP BY e.anio
        ORDER BY e.anio
    """))
    
    print(f"\nPor año:")
    for row in result:
        print(f"  • {row[0]}: {row[1]:,} registros, {row[2]:,} votos")
    
    result = conn.execute(text("""
        SELECT p.clave_partido, SUM(rp.votos) as votos
        FROM resultados_partido rp
        JOIN partido p ON p.id_partido = rp.id_partido
        JOIN resultados_electorales re ON re.pk_resultado = rp.pk_resultado
        JOIN casilla c ON c.pk_casilla = re.pk_casilla
        WHERE c.id_eleccion = 3
        GROUP BY p.clave_partido
        ORDER BY votos DESC
        LIMIT 5
    """))
    
    print(f"\nTop 5 partidos 2024:")
    for row in result:
        print(f"  • {row[0]}: {row[1]:,} votos")

print("\n" + "="*80)
print("✓ CARGA DE VOTOS POR PARTIDO COMPLETADA")
print("="*80)

import geopandas as gpd
import pandas as pd
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import warnings
warnings.filterwarnings('ignore')

# ============================================
# CONFIGURACIÓN - CONEXIÓN DIRECTA
# ============================================
SHP_PATH = Path(r"C:\Users\campe\Desktop\taxco\shalphies")

# Configuración de PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'taxco_electoral',
    'user': 'postgres',
    'password': 'tu_password'  # ⚠️ CAMBIAR - escribir directamente sin caracteres raros
}

print("="*80)
print("CARGA DE GEOMETRÍAS A POSTGRESQL")
print("="*80)

# ============================================
# PROBAR CONEXIÓN
# ============================================
print("\n[TEST] Probando conexión...")

try:
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    print(f"✓ Conexión exitosa")
    print(f"  PostgreSQL: {version[:60]}...")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    print("\nAcciones:")
    print("  1. Verifica que PostgreSQL esté corriendo")
    print("  2. Confirma el password en pgAdmin")
    print("  3. Si el password tiene acentos, cámbialo temporalmente:")
    print("     ALTER USER postgres PASSWORD 'nueva_password_sin_acentos';")
    exit()

# ============================================
# PASO 1: CARGAR SECCIONES
# ============================================
print("\n[1/3] CARGANDO GEOMETRÍAS DE SECCIONES...")

# Leer shapefile completo
gdf_secciones = gpd.read_file(SHP_PATH / "SECCION_4326.shp")
print(f"  • Secciones totales en shapefile: {len(gdf_secciones)}")

# Filtrar Taxco (municipio 56)
gdf_taxco = gdf_secciones[gdf_secciones['MUNICIPIO'] == 56].copy()
print(f"  • Secciones de Taxco (municipio 56): {len(gdf_taxco)}")

# Filtrar rango 2134-2222
gdf_taxco = gdf_taxco[gdf_taxco['SECCION'].between(2134, 2222)].copy()
print(f"  • Secciones en rango 2134-2222: {len(gdf_taxco)}")

if len(gdf_taxco) == 0:
    print("  ⚠️ No se encontraron secciones de Taxco en el shapefile")
    exit()

print(f"\nSecciones encontradas: {sorted(gdf_taxco['SECCION'].unique())[:10]}...")

# Obtener pk_seccion de la BD usando psycopg2
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

cursor.execute("SELECT pk_seccion, seccion FROM seccion WHERE id_municipio = 56")
rows = cursor.fetchall()
df_seccion_bd = pd.DataFrame(rows, columns=['pk_seccion', 'seccion'])

print(f"  • Secciones en BD: {len(df_seccion_bd)}")

# Join para obtener pk_seccion
gdf_taxco = gdf_taxco.merge(
    df_seccion_bd,
    left_on='SECCION',
    right_on='seccion',
    how='inner'
)

print(f"  • Secciones con match BD-SHP: {len(gdf_taxco)}")

# Verificar CRS
print(f"  • CRS actual: {gdf_taxco.crs}")
if gdf_taxco.crs.to_epsg() != 4326:
    print("  • Reproyectando a EPSG:4326...")
    gdf_taxco = gdf_taxco.to_crs(epsg=4326)

# Convertir geometrías a MultiPolygon
from shapely.geometry import MultiPolygon

def ensure_multipolygon(geom):
    if geom.geom_type == 'MultiPolygon':
        return geom
    elif geom.geom_type == 'Polygon':
        return MultiPolygon([geom])
    else:
        return geom

gdf_taxco['geom_multi'] = gdf_taxco['geometry'].apply(ensure_multipolygon)

# ============================================
# PASO 2: ACTUALIZAR GEOMETRÍAS EN BD
# ============================================
print("\n[2/3] ACTUALIZANDO GEOMETRÍAS EN TABLA SECCION...")

actualizado = 0
errores = 0

for idx, row in gdf_taxco.iterrows():
    pk_seccion = int(row['pk_seccion'])
    wkt = row['geom_multi'].wkt
    
    try:
        cursor.execute("""
            UPDATE seccion 
            SET geom = ST_GeomFromText(%s, 4326),
                distrito_federal = %s,
                distrito_local = %s
            WHERE pk_seccion = %s
        """, (wkt, int(row['DISTRITO_F']), int(row['DISTRITO_L']), pk_seccion))
        
        actualizado += 1
        
        if actualizado % 10 == 0:
            print(f"  • Procesadas {actualizado} secciones...")
            
    except Exception as e:
        errores += 1
        print(f"  ⚠️ Error en sección {row['SECCION']}: {e}")

conn.commit()

print(f"\n  ✓ Geometrías actualizadas: {actualizado}")
if errores > 0:
    print(f"  ⚠️ Errores: {errores}")

# ============================================
# PASO 3: VALIDACIÓN
# ============================================
print("\n[3/3] VALIDANDO GEOMETRÍAS CARGADAS...")

cursor.execute("""
    SELECT 
        COUNT(*) as total_secciones,
        COUNT(geom) as con_geometria,
        COUNT(*) - COUNT(geom) as sin_geometria
    FROM seccion 
    WHERE id_municipio = 56
""")
stats = cursor.fetchone()

print(f"\n  • Total de secciones: {stats[0]}")
print(f"  • Con geometría: {stats[1]}")
print(f"  • Sin geometría: {stats[2]}")

# Calcular área total
cursor.execute("""
    SELECT 
        ROUND(SUM(ST_Area(geom::geography))/1000000, 2) as area_km2
    FROM seccion 
    WHERE id_municipio = 56 AND geom IS NOT NULL
""")
area = cursor.fetchone()[0]

print(f"  • Área total cubierta: {area} km²")

# Secciones sin geometría
cursor.execute("""
    SELECT seccion 
    FROM seccion 
    WHERE id_municipio = 56 AND geom IS NULL
    ORDER BY seccion
""")
sin_geom = [row[0] for row in cursor.fetchall()]

if sin_geom:
    print(f"\n  ⚠️ Secciones sin geometría: {sin_geom}")
else:
    print(f"\n  ✓ Todas las secciones tienen geometría")

# ============================================
# PASO 4: CARGAR MUNICIPIO (OPCIONAL)
# ============================================
print("\n[4/4] CARGANDO GEOMETRÍA DE MUNICIPIO...")

gdf_municipios = gpd.read_file(SHP_PATH / "MUNICIPIO_4326.shp")
gdf_taxco_muni = gdf_municipios[gdf_municipios['MUNICIPIO'] == 56].copy()

if len(gdf_taxco_muni) > 0:
    # Crear tabla si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS municipio_geometria (
            id_municipio SMALLINT PRIMARY KEY REFERENCES municipio(id_municipio),
            geom GEOMETRY(MULTIPOLYGON, 4326),
            area_km2 NUMERIC(10,2)
        )
    """)
    
    # Convertir a MultiPolygon
    geom_muni = gdf_taxco_muni.iloc[0]['geometry']
    geom_muni = ensure_multipolygon(geom_muni)
    wkt_muni = geom_muni.wkt
    
    # Insertar
    cursor.execute("""
        INSERT INTO municipio_geometria (id_municipio, geom, area_km2)
        VALUES (56, ST_GeomFromText(%s, 4326), 
                ROUND(ST_Area(ST_GeomFromText(%s, 4326)::geography)/1000000, 2))
        ON CONFLICT (id_municipio) DO UPDATE
        SET geom = EXCLUDED.geom, area_km2 = EXCLUDED.area_km2
    """, (wkt_muni, wkt_muni))
    
    conn.commit()
    print("  ✓ Geometría del municipio cargada")
else:
    print("  ⚠️ No se encontró el municipio 56 en shapefile")

# Cerrar conexión
cursor.close()
conn.close()

# ============================================
# RESUMEN FINAL
# ============================================
print("\n" + "="*80)
print("✓ CARGA DE GEOMETRÍAS COMPLETADA")
print("="*80)

print("\nPrueba en PostgreSQL:")
print("""
SELECT seccion, 
       ST_AsText(ST_Centroid(geom)) as centroide,
       ROUND(ST_Area(geom::geography)/1000000, 2) as area_km2
FROM seccion 
WHERE id_municipio = 56 AND geom IS NOT NULL
ORDER BY seccion
LIMIT 5;
""")

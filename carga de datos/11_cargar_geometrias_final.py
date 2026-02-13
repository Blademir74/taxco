import geopandas as gpd
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

print("="*80)
print("CARGA DE GEOMETRIAS A POSTGRESQL")
print("="*80)

# ============================================
# CONEXIÓN SIN ESPECIFICAR PARÁMETROS
# ============================================
print("\n[0] Conectando a PostgreSQL...")

try:
    # Conectar usando variables de entorno (sin especificar nada)
    conn = psycopg2.connect("")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    print("Conexion exitosa!")
    print(f"PostgreSQL: {version[:60]}...")
    
except Exception as e:
    print(f"Error: {e}")
    print("\nIntentando con parametros explicitos...")
    
    # Plan B: Especificar parámetros directamente
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='taxco_electoral',
            user='postgres',
            password='postgres123'  # CAMBIAR AQUI
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print("Conexion exitosa con Plan B!")
        
    except Exception as e2:
        print(f"Error Plan B: {e2}")
        print("\nSOLUCION: En pgAdmin ejecuta:")
        print("ALTER USER postgres PASSWORD 'postgres123';")
        print("\nLuego vuelve a ejecutar este script.")
        exit()

# ============================================
# CARGAR SHAPEFILES
# ============================================
print("\n[1/3] Cargando shapefiles...")

# Usar ruta absoluta simple
shp_secciones = r"C:\Users\campe\Desktop\taxco\shalphies\SECCION_4326.shp"
shp_municipios = r"C:\Users\campe\Desktop\taxco\shalphies\MUNICIPIO_4326.shp"

print(f"Leyendo: {shp_secciones}")
gdf_secciones = gpd.read_file(shp_secciones, encoding='utf-8')
print(f"Total secciones: {len(gdf_secciones)}")

# Filtrar Taxco
gdf_taxco = gdf_secciones[
    (gdf_secciones['MUNICIPIO'] == 56) &
    (gdf_secciones['SECCION'].between(2134, 2222))
].copy()

print(f"Secciones de Taxco (2134-2222): {len(gdf_taxco)}")

if len(gdf_taxco) == 0:
    print("No se encontraron secciones de Taxco")
    exit()

# ============================================
# OBTENER PK_SECCION DE LA BD
# ============================================
print("\n[2/3] Obteniendo pk_seccion de BD...")

cursor.execute("SELECT pk_seccion, seccion FROM seccion WHERE id_municipio = 56")
rows = cursor.fetchall()
df_seccion_bd = pd.DataFrame(rows, columns=['pk_seccion', 'seccion'])

print(f"Secciones en BD: {len(df_seccion_bd)}")

# Join
gdf_taxco = gdf_taxco.merge(
    df_seccion_bd,
    left_on='SECCION',
    right_on='seccion',
    how='inner'
)

print(f"Match BD-SHP: {len(gdf_taxco)}")

# Asegurar EPSG:4326
if gdf_taxco.crs.to_epsg() != 4326:
    gdf_taxco = gdf_taxco.to_crs(epsg=4326)

# Convertir a MultiPolygon
from shapely.geometry import MultiPolygon

def to_multipolygon(geom):
    if geom.geom_type == 'MultiPolygon':
        return geom
    return MultiPolygon([geom])

gdf_taxco['geom_wkt'] = gdf_taxco['geometry'].apply(
    lambda g: to_multipolygon(g).wkt
)

# ============================================
# ACTUALIZAR GEOMETRÍAS
# ============================================
print("\n[3/3] Actualizando geometrias en BD...")

actualizado = 0

for idx, row in gdf_taxco.iterrows():
    try:
        cursor.execute("""
            UPDATE seccion 
            SET geom = ST_GeomFromText(%s, 4326),
                distrito_federal = %s,
                distrito_local = %s
            WHERE pk_seccion = %s
        """, (
            row['geom_wkt'],
            int(row['DISTRITO_F']),
            int(row['DISTRITO_L']),
            int(row['pk_seccion'])
        ))
        
        actualizado += 1
        if actualizado % 10 == 0:
            print(f"  Procesadas: {actualizado}/{len(gdf_taxco)}")
            
    except Exception as e:
        print(f"  Error seccion {row['SECCION']}: {e}")

print(f"\nGeometrias actualizadas: {actualizado}")

# ============================================
# VALIDACIÓN
# ============================================
print("\n[VALIDACION]")

cursor.execute("""
    SELECT COUNT(*) as total, COUNT(geom) as con_geom
    FROM seccion WHERE id_municipio = 56
""")
total, con_geom = cursor.fetchone()

print(f"Secciones totales: {total}")
print(f"Con geometria: {con_geom}")
print(f"Sin geometria: {total - con_geom}")

# Área
cursor.execute("""
    SELECT ROUND(SUM(ST_Area(geom::geography))/1000000, 2)
    FROM seccion WHERE id_municipio = 56 AND geom IS NOT NULL
""")
area = cursor.fetchone()[0]
print(f"Area cubierta: {area} km2")

# Cerrar
cursor.close()
conn.close()

print("\n" + "="*80)
print("CARGA COMPLETADA")
print("="*80)

import geopandas as gpd
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

print("="*80)
print("CARGA DE GEOMETRIAS A POSTGRESQL")
print("="*80)

# ============================================
# CONEXIÓN CON ENCODING EXPLÍCITO
# ============================================
print("\n[0] Conectando a PostgreSQL...")

try:
    # Conexión especificando client_encoding
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='taxco_electoral',
        user='postgres',
        password='postgres123',
        options='-c client_encoding=UTF8'  # ← CLAVE: Forzar UTF-8
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    print("✓ Conexion exitosa!")
    print(f"  PostgreSQL: {version[:60]}...")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit()

# ============================================
# PASO 1: CARGAR SHAPEFILES
# ============================================
print("\n[1/4] Cargando shapefiles...")

shp_secciones = r"C:\Users\campe\Desktop\taxco\shalphies\SECCION_4326.shp"
shp_municipios = r"C:\Users\campe\Desktop\taxco\shalphies\MUNICIPIO_4326.shp"

print(f"  Leyendo: SECCION_4326.shp")
gdf_secciones = gpd.read_file(shp_secciones)
print(f"  • Total secciones: {len(gdf_secciones)}")

# Filtrar Taxco (municipio 56, rango 2134-2222)
gdf_taxco = gdf_secciones[
    (gdf_secciones['MUNICIPIO'] == 56) &
    (gdf_secciones['SECCION'].between(2134, 2222))
].copy()

print(f"  • Secciones de Taxco: {len(gdf_taxco)}")

if len(gdf_taxco) == 0:
    print("  ⚠️ No se encontraron secciones de Taxco")
    cursor.close()
    conn.close()
    exit()

# ============================================
# PASO 2: OBTENER PK_SECCION DE LA BD
# ============================================
print("\n[2/4] Mapeando con base de datos...")

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

print(f"  • Secciones con match: {len(gdf_taxco)}")

# Asegurar proyección correcta
if gdf_taxco.crs.to_epsg() != 4326:
    print("  • Reproyectando a EPSG:4326...")
    gdf_taxco = gdf_taxco.to_crs(epsg=4326)

# Convertir a MultiPolygon
from shapely.geometry import MultiPolygon

def to_multipolygon(geom):
    if geom.geom_type == 'MultiPolygon':
        return geom
    elif geom.geom_type == 'Polygon':
        return MultiPolygon([geom])
    else:
        return geom

gdf_taxco['geom_multi'] = gdf_taxco['geometry'].apply(to_multipolygon)

# ============================================
# PASO 3: ACTUALIZAR GEOMETRÍAS
# ============================================
print("\n[3/4] Actualizando geometrias en la base de datos...")

actualizado = 0
errores = 0

for idx, row in gdf_taxco.iterrows():
    pk_seccion = int(row['pk_seccion'])
    seccion_num = int(row['SECCION'])
    wkt = row['geom_multi'].wkt
    
    try:
        cursor.execute("""
            UPDATE seccion 
            SET geom = ST_GeomFromText(%s, 4326),
                distrito_federal = %s,
                distrito_local = %s
            WHERE pk_seccion = %s
        """, (
            wkt,
            int(row['DISTRITO_F']),
            int(row['DISTRITO_L']),
            pk_seccion
        ))
        
        actualizado += 1
        
        if actualizado % 10 == 0:
            print(f"  • Procesadas: {actualizado}/{len(gdf_taxco)}")
            
    except Exception as e:
        errores += 1
        print(f"  ⚠️ Error en sección {seccion_num}: {str(e)[:80]}")

print(f"\n  ✓ Geometrías actualizadas: {actualizado}")
if errores > 0:
    print(f"  ⚠️ Errores: {errores}")

# ============================================
# PASO 4: CARGAR MUNICIPIO
# ============================================
print("\n[4/4] Cargando geometria del municipio...")

# Crear tabla si no existe
cursor.execute("""
    CREATE TABLE IF NOT EXISTS municipio_geometria (
        id_municipio SMALLINT PRIMARY KEY REFERENCES municipio(id_municipio),
        geom GEOMETRY(MULTIPOLYGON, 4326),
        area_km2 NUMERIC(10,2)
    )
""")

# Leer shapefile de municipios
print(f"  Leyendo: MUNICIPIO_4326.shp")
gdf_municipios = gpd.read_file(shp_municipios)

# Filtrar Taxco
gdf_taxco_muni = gdf_municipios[gdf_municipios['MUNICIPIO'] == 56].copy()

if len(gdf_taxco_muni) > 0:
    geom_muni = to_multipolygon(gdf_taxco_muni.iloc[0]['geometry'])
    wkt_muni = geom_muni.wkt
    
    cursor.execute("""
        INSERT INTO municipio_geometria (id_municipio, geom, area_km2)
        VALUES (56, ST_GeomFromText(%s, 4326), 
                ROUND(CAST(ST_Area(ST_GeomFromText(%s, 4326)::geography)/1000000 AS numeric), 2)
        ON CONFLICT (id_municipio) DO UPDATE
        SET geom = EXCLUDED.geom, area_km2 = EXCLUDED.area_km2
    """, (wkt_muni, wkt_muni))
    
    print("  ✓ Geometria del municipio cargada")
else:
    print("  ⚠️ No se encontro municipio 56 en shapefile")

# ============================================
# VALIDACIÓN FINAL
# ============================================
print("\n" + "="*80)
print("VALIDACION")
print("="*80)

cursor.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(geom) as con_geom,
        COUNT(*) - COUNT(geom) as sin_geom
    FROM seccion 
    WHERE id_municipio = 56
""")
total, con_geom, sin_geom = cursor.fetchone()

print(f"\nSecciones:")
print(f"  • Total: {total}")
print(f"  • Con geometria: {con_geom}")
print(f"  • Sin geometria: {sin_geom}")

if sin_geom > 0:
    cursor.execute("""
        SELECT seccion 
        FROM seccion 
        WHERE id_municipio = 56 AND geom IS NULL
        ORDER BY seccion
    """)
    secciones_sin = [row[0] for row in cursor.fetchall()]
    print(f"\n  Secciones sin geometria: {secciones_sin}")

# Calcular área
cursor.execute("""
    SELECT ROUND(SUM(ST_Area(geom::geography))/1000000, 2)
    FROM seccion 
    WHERE id_municipio = 56 AND geom IS NOT NULL
""")
area = cursor.fetchone()[0]
print(f"\nArea cubierta: {area} km²")

# Cerrar conexión
cursor.close()
conn.close()

print("\n" + "="*80)
print("✓ CARGA DE GEOMETRIAS COMPLETADA")
print("="*80)

print("\nVerifica en PostgreSQL:")
print("""
SELECT seccion, 
       ST_AsText(ST_Centroid(geom)) as centroide,
       ROUND(ST_Area(geom::geography)/1000, 2) as area_m2
FROM seccion 
WHERE id_municipio = 56 AND geom IS NOT NULL
ORDER BY seccion
LIMIT 5;
""")

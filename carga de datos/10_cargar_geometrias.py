import geopandas as gpd
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import warnings
warnings.filterwarnings('ignore')

# ============================================
# CONFIGURACIÓN
# ============================================
SHP_PATH = Path(r"C:\Users\campe\Desktop\taxco\shalphies")

DB_USER = 'postgres'
DB_PASSWORD = 'tu_password'  # ⚠️ CAMBIAR - puede tener acentos
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'taxco_electoral'

# Codificar password para URL (maneja caracteres especiales)
password_encoded = quote_plus(DB_PASSWORD)

# Crear conexión
conn_string = f'postgresql://{DB_USER}:{password_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(conn_string, client_encoding='utf8')

print("="*80)
print("CARGA DE GEOMETRÍAS A POSTGRESQL")
print("="*80)
print(f"Conectando a: {DB_HOST}:{DB_PORT}/{DB_NAME}")

# Probar conexión
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✓ Conexión exitosa")
        print(f"  PostgreSQL: {version[:50]}...")
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    print("\nVerifica:")
    print("  1. PostgreSQL está corriendo")
    print("  2. El password es correcto")
    print("  3. La base de datos 'taxco_electoral' existe")
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

# Obtener pk_seccion de la BD
with engine.connect() as conn:
    df_seccion_bd = pd.read_sql(
        "SELECT pk_seccion, seccion FROM seccion WHERE id_municipio = 56",
        conn
    )

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

# Convertir geometrías a MultiPolygon (uniformizar)
gdf_taxco['geom_multi'] = gdf_taxco['geometry'].apply(
    lambda geom: geom if geom.geom_type == 'MultiPolygon' 
    else gpd.GeoSeries([geom]).unary_union
)

# ============================================
# PASO 2: ACTUALIZAR GEOMETRÍAS EN BD
# ============================================
print("\n[2/3] ACTUALIZANDO GEOMETRÍAS EN TABLA SECCION...")

actualizado = 0
errores = 0

with engine.connect() as conn:
    for idx, row in gdf_taxco.iterrows():
        pk_seccion = int(row['pk_seccion'])
        wkt = row['geom_multi'].wkt  # Well-Known Text
        
        try:
            # Actualizar geometría
            query = text("""
                UPDATE seccion 
                SET geom = ST_GeomFromText(:wkt, 4326),
                    distrito_federal = :distrito_f,
                    distrito_local = :distrito_l
                WHERE pk_seccion = :pk
            """)
            
            conn.execute(query, {
                'wkt': wkt,
                'distrito_f': int(row['DISTRITO_F']),
                'distrito_l': int(row['DISTRITO_L']),
                'pk': pk_seccion
            })
            conn.commit()
            actualizado += 1
            
            if actualizado % 10 == 0:
                print(f"  • Procesadas {actualizado} secciones...")
                
        except Exception as e:
            errores += 1
            print(f"  ⚠️ Error en sección {row['SECCION']}: {e}")

print(f"\n  ✓ Geometrías actualizadas: {actualizado}")
if errores > 0:
    print(f"  ⚠️ Errores: {errores}")

# ============================================
# PASO 3: VALIDACIÓN
# ============================================
print("\n[3/3] VALIDANDO GEOMETRÍAS CARGADAS...")

with engine.connect() as conn:
    # Contar geometrías no nulas
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total_secciones,
            COUNT(geom) as con_geometria,
            COUNT(*) - COUNT(geom) as sin_geometria
        FROM seccion 
        WHERE id_municipio = 56
    """))
    stats = result.fetchone()
    
    print(f"\n  • Total de secciones: {stats[0]}")
    print(f"  • Con geometría: {stats[1]}")
    print(f"  • Sin geometría: {stats[2]}")
    
    # Calcular área total
    result = conn.execute(text("""
        SELECT 
            ROUND(SUM(ST_Area(geom::geography))/1000000, 2) as area_km2
        FROM seccion 
        WHERE id_municipio = 56 AND geom IS NOT NULL
    """))
    area = result.fetchone()[0]
    
    print(f"  • Área total cubierta: {area} km²")
    
    # Secciones sin geometría
    result = conn.execute(text("""
        SELECT seccion 
        FROM seccion 
        WHERE id_municipio = 56 AND geom IS NULL
        ORDER BY seccion
    """))
    sin_geom = [row[0] for row in result]
    
    if sin_geom:
        print(f"\n  ⚠️ Secciones sin geometría: {sin_geom}")
    else:
        print(f"\n  ✓ Todas las secciones tienen geometría")

# ============================================
# PASO 4: CREAR TABLA AUXILIAR DE MUNICIPIO
# ============================================
print("\n[4/4] CARGANDO GEOMETRÍA DE MUNICIPIO (OPCIONAL)...")

# Leer shapefile de municipios
gdf_municipios = gpd.read_file(SHP_PATH / "MUNICIPIO_4326.shp")

# Filtrar Taxco (municipio 56)
gdf_taxco_muni = gdf_municipios[gdf_municipios['MUNICIPIO'] == 56].copy()

if len(gdf_taxco_muni) > 0:
    # Crear tabla municipio_geometria (si no existe)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS municipio_geometria (
                id_municipio SMALLINT PRIMARY KEY REFERENCES municipio(id_municipio),
                geom GEOMETRY(MULTIPOLYGON, 4326),
                area_km2 NUMERIC(10,2)
            )
        """))
        conn.commit()
    
    # Convertir a MultiPolygon
    geom_muni = gdf_taxco_muni.iloc[0]['geometry']
    if geom_muni.geom_type != 'MultiPolygon':
        from shapely.geometry import MultiPolygon
        geom_muni = MultiPolygon([geom_muni])
    
    wkt_muni = geom_muni.wkt
    
    # Insertar
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO municipio_geometria (id_municipio, geom, area_km2)
            VALUES (56, ST_GeomFromText(:wkt, 4326), 
                    ROUND(ST_Area(ST_GeomFromText(:wkt, 4326)::geography)/1000000, 2))
            ON CONFLICT (id_municipio) DO UPDATE
            SET geom = EXCLUDED.geom, area_km2 = EXCLUDED.area_km2
        """), {'wkt': wkt_muni})
        conn.commit()
    
    print("  ✓ Geometría del municipio cargada en tabla municipio_geometria")
else:
    print("  ⚠️ No se encontró el municipio 56 en MUNICIPIO_4326.shp")

# ============================================
# RESUMEN FINAL
# ============================================
print("\n" + "="*80)
print("✓ CARGA DE GEOMETRÍAS COMPLETADA")
print("="*80)

print("\nPrueba en PostgreSQL:")
print("""
-- Ver secciones con geometría
SELECT seccion, 
       ST_AsText(ST_Centroid(geom)) as centroide,
       ROUND(ST_Area(geom::geography)/1000000, 2) as area_km2
FROM seccion 
WHERE id_municipio = 56 AND geom IS NOT NULL
ORDER BY seccion
LIMIT 5;
""")

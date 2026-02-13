import geopandas as gpd
import psycopg2
from pathlib import Path
from shapely.geometry import MultiPolygon

SHP_PATH = Path(r"C:\Users\campe\Desktop\taxco\shalphies")

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'taxco_electoral',
    'user': 'postgres',
    'password': 'postgres123'
}

print("Cargando geometria del municipio...")

conn = psycopg2.connect(**DB_CONFIG, options='-c client_encoding=UTF8')
cursor = conn.cursor()

# Crear tabla si no existe
cursor.execute("""
    CREATE TABLE IF NOT EXISTS municipio_geometria (
        id_municipio SMALLINT PRIMARY KEY REFERENCES municipio(id_municipio),
        geom GEOMETRY(MULTIPOLYGON, 4326),
        area_km2 NUMERIC(10,2)
    )
""")

# Leer shapefile
gdf_municipios = gpd.read_file(SHP_PATH / "MUNICIPIO_4326.shp")
gdf_taxco_muni = gdf_municipios[gdf_municipios['MUNICIPIO'] == 56].copy()

if len(gdf_taxco_muni) > 0:
    geom_muni = gdf_taxco_muni.iloc[0]['geometry']
    
    # Convertir a MultiPolygon
    if geom_muni.geom_type != 'MultiPolygon':
        geom_muni = MultiPolygon([geom_muni])
    
    wkt_muni = geom_muni.wkt
    
    # Verificar si existe
    cursor.execute("SELECT COUNT(*) FROM municipio_geometria WHERE id_municipio = 56")
    existe = cursor.fetchone()[0]
    
    if existe > 0:
        print("  Actualizando geometria existente...")
        cursor.execute("""
            UPDATE municipio_geometria 
            SET geom = ST_GeomFromText(%s, 4326),
                area_km2 = ROUND(CAST(ST_Area(ST_GeomFromText(%s, 4326)::geography)/1000000 AS numeric), 2)
            WHERE id_municipio = 56
        """, (wkt_muni, wkt_muni))
    else:
        print("  Insertando geometria nueva...")
        cursor.execute("""
            INSERT INTO municipio_geometria (id_municipio, geom, area_km2)
            VALUES (56, ST_GeomFromText(%s, 4326), 
                    ROUND(CAST(ST_Area(ST_GeomFromText(%s, 4326)::geography)/1000000 AS numeric), 2))
        """, (wkt_muni, wkt_muni))
    
    conn.commit()
    print("  ✓ Geometria del municipio cargada")
    
    # Ver resultado
    cursor.execute("SELECT area_km2 FROM municipio_geometria WHERE id_municipio = 56")
    area = cursor.fetchone()[0]
    print(f"  Area: {area} km²")
    
else:
    print("  ⚠️ No se encontro municipio 56")

cursor.close()
conn.close()

print("\n✓ COMPLETADO")

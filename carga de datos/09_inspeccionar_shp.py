import geopandas as gpd
from pathlib import Path

SHP_PATH = Path(r"C:\Users\campe\Desktop\taxco\shalphies")

print("="*80)
print("INSPECCIÓN DE SHAPEFILES")
print("="*80)

# Listar archivos .shp
shp_files = list(SHP_PATH.glob("*.shp"))

print(f"\nArchivos .shp encontrados: {len(shp_files)}")
for f in shp_files:
    print(f"  • {f.name}")

if len(shp_files) == 0:
    print("\n⚠️  No se encontraron archivos .shp")
    print(f"Verifica la ruta: {SHP_PATH}")
    exit()

print("\n" + "="*80)

# Inspeccionar cada shapefile
for shp_file in shp_files:
    print(f"\n📁 ARCHIVO: {shp_file.name}")
    print("-"*80)
    
    try:
        gdf = gpd.read_file(shp_file)
        
        print(f"Registros: {len(gdf)}")
        print(f"CRS (sistema de coordenadas): {gdf.crs}")
        print(f"Tipo de geometría: {gdf.geometry.type.unique()}")
        
        print(f"\nColumnas ({len(gdf.columns)}):")
        for col in gdf.columns:
            print(f"  • {col}: {gdf[col].dtype}")
        
        print(f"\nPrimeras 3 filas (columnas principales):")
        cols_display = [c for c in gdf.columns if c != 'geometry'][:10]
        print(gdf[cols_display].head(3).to_string(index=False))
        
        # Si parece ser de secciones, buscar campo de sección
        posibles_campos_seccion = ['SECCION', 'seccion', 'ID_SECCION', 'CVE_SEC', 'SECC']
        campo_encontrado = [c for c in gdf.columns if any(p.lower() in c.lower() for p in posibles_campos_seccion)]
        
        if campo_encontrado:
            print(f"\n✓ Posible campo de sección: {campo_encontrado}")
            print(f"  Valores únicos: {gdf[campo_encontrado[0]].nunique()}")
            print(f"  Ejemplo de valores: {gdf[campo_encontrado[0]].head(5).tolist()}")
        
        # Si parece ser de municipio
        posibles_campos_muni = ['MUNICIPIO', 'NOM_MUN', 'CVE_MUN', 'ID_MUNICIPIO']
        campo_muni = [c for c in gdf.columns if any(p.lower() in c.lower() for p in posibles_campos_muni)]
        
        if campo_muni:
            print(f"\n✓ Posible campo de municipio: {campo_muni}")
            print(f"  Valores únicos: {gdf[campo_muni[0]].unique()[:5]}")
        
    except Exception as e:
        print(f"❌ Error al leer: {e}")

print("\n" + "="*80)
print("✓ INSPECCIÓN COMPLETADA")
print("="*80)

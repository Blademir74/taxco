import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse

# ===== CONFIGURACIÓN =====
# Base local (cambia la contraseña si es diferente)
LOCAL_DB = "postgresql://postgres:postgres123@localhost:5432/taxco_electoral"

# Neon (USAMOS LA QUE YA FUNCIONA)
NEON_DB = "postgresql://neondb_owner:npg_ZxOqBGdQ40hf@ep-dark-salad-aiwt2y0r-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"
# =========================

def migrar():
    print("Conectando a base local...")
    engine_local = create_engine(LOCAL_DB)
    
    print("Conectando a Neon...")
    engine_neon = create_engine(NEON_DB)
    
    # Lista de tablas a migrar (en orden para respetar claves foráneas)
    tablas = [
        'seccion',
        'partido',
        'eleccion',
        'categoria_servicio',
        'fuente_sentimiento',
        'padron_ine',
        'carencias_inegi',
        'casilla',
        'resultados_electorales',
        'resultados_partido',
        'sentimiento_social',
        'denuncias_ciudadanas',
        'invitaciones',
        'usuarios_tenant',
        'simpatizantes',
        'evidencias',
        'logs_gps'
    ]
    
    # Obtener solo las tablas que existen en local
    with engine_local.connect() as conn:
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        tablas_existentes = [row[0] for row in result]
    
    for tabla in tablas:
        if tabla not in tablas_existentes:
            print(f"⚠️ Tabla {tabla} no existe localmente, omitiendo...")
            continue
            
        print(f"📦 Migrando {tabla}...")
        try:
            # Leer de local
            df = pd.read_sql(f"SELECT * FROM {tabla}", engine_local)
            print(f"   → {len(df)} registros")
            
            if len(df) > 0:
                # Escribir en Neon (reemplaza si existe)
                df.to_sql(tabla, engine_neon, if_exists='replace', index=False)
                print(f"   ✅ {tabla} migrada correctamente")
            else:
                print(f"   ⏭️  {tabla} está vacía, creando estructura...")
                # Crear estructura vacía (solo la tabla sin datos)
                df.head(0).to_sql(tabla, engine_neon, if_exists='replace', index=False)
                
        except Exception as e:
            print(f"   ❌ Error en {tabla}: {e}")
            continue
    
    print("\n🎉 MIGRACIÓN COMPLETADA")

if __name__ == "__main__":
    migrar()
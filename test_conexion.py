from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

DB_USER = 'postgres'
DB_PASSWORD = 'tu_password'  # ⚠️ CAMBIAR
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'taxco_electoral'

print("Probando conexión a PostgreSQL...")
print(f"Usuario: {DB_USER}")
print(f"Host: {DB_HOST}:{DB_PORT}")
print(f"Base de datos: {DB_NAME}")
print(f"Password: {'*' * len(DB_PASSWORD)}")

# Codificar password
password_encoded = quote_plus(DB_PASSWORD)

# Intentar conectar
conn_string = f'postgresql://{DB_USER}:{password_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

try:
    engine = create_engine(conn_string, client_encoding='utf8')
    
    with engine.connect() as conn:
        # Probar query simple
        result = conn.execute(text("SELECT 1"))
        print("\n✓ Conexión exitosa")
        
        # Ver tablas
        result = conn.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """))
        tablas = [row[0] for row in result]
        print(f"\nTablas encontradas ({len(tablas)}):")
        for t in tablas:
            print(f"  • {t}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nPosibles causas:")
    print("  1. Password incorrecto")
    print("  2. PostgreSQL no está corriendo")
    print("  3. Base de datos no existe")
    print("  4. Problema de codificación en password")

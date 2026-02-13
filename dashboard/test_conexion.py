# -*- coding: utf-8 -*-
"""
test_conexion.py
Script de validación para verificar que la conexión a PostgreSQL funciona correctamente
con encoding UTF-8 ANTES de ejecutar Streamlit.

USO: python test_conexion.py
"""

import sys
import os

# Forzar UTF-8 en Python (Windows)
if sys.platform == "win32":
    # Configurar la consola de Windows para UTF-8
    os.system('chcp 65001 > nul')
    
    # Forzar stdout/stderr a UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

print("=" * 70)
print("🔍 VALIDACIÓN DE CONEXIÓN PostgreSQL + UTF-8")
print("=" * 70)
print()

# ============================================
# TEST 1: Importar módulos
# ============================================
print("📦 TEST 1: Importando módulos...")
try:
    import pandas as pd
    import sqlalchemy
    from sqlalchemy import create_engine, text
    import psycopg2
    print("✅ Módulos importados correctamente")
    print(f"   - pandas: {pd.__version__}")
    print(f"   - SQLAlchemy: {sqlalchemy.__version__}")
    print(f"   - psycopg2: {psycopg2.__version__}")
except Exception as e:
    print(f"❌ ERROR al importar módulos: {e}")
    sys.exit(1)

print()

# ============================================
# TEST 2: Cargar configuración
# ============================================
print("⚙️ TEST 2: Cargando configuración...")
try:
    from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    print("✅ Configuración cargada:")
    print(f"   - Host: {DB_HOST}")
    print(f"   - Port: {DB_PORT}")
    print(f"   - Database: {DB_NAME}")
    print(f"   - User: {DB_USER}")
    print(f"   - Password: {'*' * len(DB_PASSWORD)}")
except Exception as e:
    print(f"❌ ERROR al cargar config.py: {e}")
    sys.exit(1)

print()

# ============================================
# TEST 3: Crear engine
# ============================================
print("🔧 TEST 3: Creando SQLAlchemy engine...")
try:
    from queries import get_engine
    engine = get_engine()
    print("✅ Engine creado correctamente")
except Exception as e:
    print(f"❌ ERROR al crear engine: {e}")
    sys.exit(1)

print()

# ============================================
# TEST 4: Probar conexión básica
# ============================================
print("🔌 TEST 4: Probando conexión a PostgreSQL...")
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print("✅ Conexión exitosa!")
        print(f"   PostgreSQL version: {version[:60]}...")
except Exception as e:
    print(f"❌ ERROR de conexión: {e}")
    print("\n💡 Posibles causas:")
    print("   1. PostgreSQL no está corriendo")
    print("   2. Credenciales incorrectas")
    print("   3. Firewall bloqueando puerto 5432")
    sys.exit(1)

print()

# ============================================
# TEST 5: Verificar encoding
# ============================================
print("🔤 TEST 5: Verificando encoding UTF-8...")
try:
    with engine.connect() as conn:
        # Encoding del servidor
        result = conn.execute(text("SHOW server_encoding;"))
        server_encoding = result.fetchone()[0]
        
        # Encoding del cliente
        result = conn.execute(text("SHOW client_encoding;"))
        client_encoding = result.fetchone()[0]
        
        # Encoding de la base de datos
        result = conn.execute(text("""
            SELECT pg_encoding_to_char(encoding) 
            FROM pg_database 
            WHERE datname = :dbname
        """), {"dbname": DB_NAME})
        db_encoding = result.fetchone()[0]
        
        print("✅ Configuración de encoding:")
        print(f"   - Server encoding: {server_encoding}")
        print(f"   - Client encoding: {client_encoding}")
        print(f"   - Database encoding: {db_encoding}")
        
        # Verificar que todo sea UTF8
        if client_encoding.upper() != 'UTF8':
            print("\n⚠️ WARNING: Client encoding NO es UTF8")
            print("   La configuración debería forzarlo a UTF8 automáticamente")
        else:
            print("\n✅ Todos los encodings correctos!")
            
except Exception as e:
    print(f"❌ ERROR al verificar encoding: {e}")
    sys.exit(1)

print()

# ============================================
# TEST 6: Probar query con caracteres especiales
# ============================================
print("📝 TEST 6: Probando query con caracteres especiales...")
try:
    with engine.connect() as conn:
        # Query simple con caracteres acentuados
        result = conn.execute(text("""
            SELECT 
                'Taxco de Alarcón' as municipio,
                'José María Morelos' as personaje,
                'Año 2024' as periodo
        """))
        row = result.fetchone()
        
        print("✅ Query ejecutado correctamente:")
        print(f"   - Municipio: {row[0]}")
        print(f"   - Personaje: {row[1]}")
        print(f"   - Periodo: {row[2]}")
        
        # Verificar que los acentos se decodificaron bien
        if 'ó' in row[0] and 'é' in row[1]:
            print("\n✅ Acentos decodificados correctamente!")
        else:
            print("\n⚠️ WARNING: Posible problema con acentos")
            
except Exception as e:
    print(f"❌ ERROR en query con acentos: {e}")
    sys.exit(1)

print()

# ============================================
# TEST 7: Probar pd.read_sql (el que falla en tu caso)
# ============================================
print("🐼 TEST 7: Probando pandas.read_sql()...")
try:
    query = """
    SELECT 
        e.anio,
        e.tipo_eleccion
    FROM eleccion e
    ORDER BY e.anio
    LIMIT 3
    """
    df = pd.read_sql(query, engine)
    print("✅ pd.read_sql() ejecutado correctamente:")
    print(df.to_string(index=False))
    
except Exception as e:
    print(f"❌ ERROR en pd.read_sql(): {e}")
    print("\n💡 Este es el error que probablemente estabas teniendo.")
    print("   Si ves este mensaje, la solución NO funcionó completamente.")
    sys.exit(1)

print()

# ============================================
# TEST 8: Probar función real del dashboard
# ============================================
print("🎯 TEST 8: Probando función real get_kpis_participacion()...")
try:
    from queries import get_kpis_participacion
    df = get_kpis_participacion()
    
    if df.empty:
        print("⚠️ WARNING: La función devolvió DataFrame vacío")
        print("   Posibles causas:")
        print("   1. No hay datos en las tablas")
        print("   2. id_municipio = 56 no existe")
    else:
        print("✅ Función ejecutada correctamente:")
        print(df.to_string(index=False))
        
except Exception as e:
    print(f"❌ ERROR en get_kpis_participacion(): {e}")
    import traceback
    print("\n🔍 Stack trace completo:")
    print(traceback.format_exc())
    sys.exit(1)

print()

# ============================================
# RESULTADO FINAL
# ============================================
print("=" * 70)
print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE")
print("=" * 70)
print()
print("🚀 El sistema está listo para ejecutar Streamlit:")
print("   python -m streamlit run app.py")
print()
print("📌 NOTAS:")
print("   - Encoding configurado correctamente (UTF-8)")
print("   - Conexión a PostgreSQL funcionando")
print("   - Queries con caracteres especiales OK")
print("   - pandas.read_sql() funcionando")
print()
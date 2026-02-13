# test_connection.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from queries import get_engine
import pandas as pd

def test_connection():
    print("🔍 Probando conexión con creator (sin DSN)...")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            df = pd.read_sql("SELECT 'éxito' as prueba, 'óáñ' as acentos", engine)
            print("✅ CONEXIÓN EXITOSA")
            print("📋 Resultado:", df.iloc[0].to_dict())
        return True
    except Exception as e:
        print("❌ ERROR DE CONEXIÓN")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_connection()
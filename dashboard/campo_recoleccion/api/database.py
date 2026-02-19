
import os
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

load_dotenv()

<<<<<<< HEAD
# ============================================
# CONEXIÓN BASE DE DATOS (NEON + RENDER)
# ============================================
def get_db_url():
    """Construye la URL de conexión segura obligatoria para Neon"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        # Fallback a construcción manual (útil para local)
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DB_PORT = os.getenv("DB_PORT", "5432")
        DB_NAME = os.getenv("DB_NAME", "taxco_electoral")
        DB_USER = os.getenv("DB_USER", "postgres")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres123")
        database_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
=======
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no está configurada en las variables de entorno")
>>>>>>> c0e6b59f5a7880c257092a53aa7675117f052c2d

    # Corregir prefijo para SQLAlchemy (postgres -> postgresql)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # Forzar SSL mode para Neon (evita error de handshake)
    if "?sslmode=" not in database_url:
        if "?" in database_url:
            database_url += "&sslmode=require"
        else:
            database_url += "?sslmode=require"
            
    return database_url

DATABASE_URL = get_db_url()

# Crear engine con pool de conexiones optimizado para Render (tier gratuito/starter)
engine = create_engine(
    DATABASE_URL,
<<<<<<< HEAD
    poolclass=QueuePool,
    pool_size=5,                # Reducido para evitar error "too many clients" en Neon Free
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,          # Reciclar conexiones cada 30 min
    pool_pre_ping=True,         # Verifica conexión antes de usar (evita "server closed the connection unexpectedly")
    connect_args={'connect_timeout': 10}
=======
    connect_args={'client_encoding': 'utf8', 'sslmode': 'require'},
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
>>>>>>> c0e6b59f5a7880c257092a53aa7675117f052c2d
)

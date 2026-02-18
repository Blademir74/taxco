import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://...")
engine = create_engine(DATABASE_URL, connect_args={'client_encoding': 'utf8'})
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "taxco_electoral")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres123")

# Usamos un pool de conexiones para manejar múltiples brigadistas
url = URL.create(
    drivername="postgresql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)

engine = create_engine(
    url,
    connect_args={'client_encoding': 'utf8'},
    poolclass=QueuePool,
    pool_size=10,               # Número de conexiones simultáneas
    max_overflow=20,             # Conexiones extras bajo demanda
    pool_pre_ping=True           # Verifica la conexión antes de usarla
)
import os
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

load_dotenv()

def get_db_url():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DB_PORT = os.getenv("DB_PORT", "5432")
        DB_NAME = os.getenv("DB_NAME", "taxco_electoral")
        DB_USER = os.getenv("DB_USER", "postgres")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres123")
        database_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    if "?sslmode=" not in database_url:
        database_url += ("&sslmode=require" if "?" in database_url else "?sslmode=require")
    return database_url

DATABASE_URL = get_db_url()

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    connect_args={'connect_timeout': 10}
)
import os
import streamlit as st

# ============================================
# LEER SECRETS DE STREAMLIT O ENV
# ============================================
def get_secret(key, default=""):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

DATABASE_URL = get_secret("DATABASE_URL")
BACKEND_URL = get_secret("BACKEND_URL", "https://taxco-backend-api.onrender.com")

# Credenciales locales (fallback desarrollo)
DB_HOST = get_secret("DB_HOST", "ep-dark-salad-aiwt2y0r-pooler.c-4.us-east-1.aws.neon.tech")
DB_PORT = get_secret("DB_PORT", "5432")
DB_NAME = get_secret("DB_NAME", "neondb")
DB_USER = get_secret("DB_USER", "neondb_owner")
DB_PASSWORD = get_secret("DB_PASSWORD", "npg_ZxOqBGdQ40hf")

# ============================================
# CONFIGURACIÓN DEL MUNICIPIO
# ============================================
MUNICIPIO_ID = 56
MUNICIPIO_NOMBRE = "Taxco de Alarcón"
ANIOS_DISPONIBLES = [2018, 2021, 2024]
PRESUPUESTO_FAISMUN_2025 = 203_700_000

CENTRO_MAPA = {"lat": 18.5553, "lon": -99.6058}
ZOOM_INICIAL = 12

MAPEO_ELECCIONES = {
    2018: 1,
    2021: 2,
    2024: 3
}

COLORES_PARTIDOS = {
    "MORENA": "#8B0000",
    "PAN": "#0047AB",
    "PRI": "#006847",
    "PRD": "#FFCC00",
    "MC": "#FF6600",
    "PT": "#CC0000",
    "PVEM": "#00A550",
    "NA": "#003087",
    "SIN DATOS": "#888888"
}
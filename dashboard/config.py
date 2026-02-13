# -*- coding: utf-8 -*-

# Importar streamlit para acceder a secrets
try:
    import streamlit as st
    # Usar secrets de Streamlit Cloud si están disponibles
    DB_HOST = st.secrets.get("DB_HOST", "localhost")
    DB_PORT = st.secrets.get("DB_PORT", "5432")
    DB_NAME = st.secrets.get("DB_NAME", "taxco_electoral")
    DB_USER = st.secrets.get("DB_USER", "postgres")
    DB_PASSWORD = st.secrets.get("DB_PASSWORD", "postgres123")
except:
    # Valores por defecto para desarrollo local
    DB_HOST = "localhost"
    DB_PORT = "5432"
    DB_NAME = "taxco_electoral"
    DB_USER = "postgres"
    DB_PASSWORD = "postgres123"

MUNICIPIO_ID = 56
MUNICIPIO_NOMBRE = "Taxco de Alarcon"
ESTADO = "Guerrero"

ANIOS_DISPONIBLES = [2018, 2021, 2024]

MAPEO_ELECCIONES = {2018: 1, 2021: 2, 2024: 3}

PRESUPUESTO_FAISMUN_2025 = 203_700_000

COLORES_PARTIDOS = {
    'MORENA': '#8B242B',
    'PAN': '#0066CC',
    'PRI': '#E30613',
    'PRD': '#FFDD00',
    'PVEM': '#76B82A',
    'PT': '#DC143C',
    'MC': '#FF7F00',
    'NULO': '#CCCCCC',
    'NO_REGISTRADO': '#999999'
}

CONFIG_VISUALIZACION = {
    'mapa_centro': [18.5569, -99.6450],  # Coordenadas de Taxco
    'mapa_zoom': 12,
    'altura_grafica': 400,
    'ancho_grafica': 800
}

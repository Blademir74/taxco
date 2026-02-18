# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
try:
    import psycopg2
except ImportError:
    import psycopg as psycopg2
from config import *
import json
from shapely.geometry import shape

# ============================================
# CONEXIÓN SEGURA (sin DSN, UTF-8 forzado)
# ============================================
def get_connection():
    """Crea conexión directa con psycopg2, usando DATABASE_URL del entorno si está disponible."""
    import os
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Si hay variable de entorno, úsala directamente (espera que contenga todo: usuario, pass, host, puerto, db)
        return psycopg2.connect(database_url)
    else:
        # Fallback a parámetros locales (para desarrollo)
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            client_encoding='UTF8'
        )

def get_engine():
    """SQLAlchemy engine usando creator (evita DSN)."""
    return create_engine(
        'postgresql+psycopg2://',
        creator=get_connection
    )

# ============================================
# MAPEO ELECCIONES (desde config.py)
# ============================================
def get_id_eleccion(anio):
    return MAPEO_ELECCIONES.get(anio, 3)

# ============================================
# 1. KPIS DE PARTICIPACIÓN
# ============================================
def get_kpis_participacion():
    engine = get_engine()
    query = """
    SELECT 
        e.anio,
        COALESCE(SUM(rp.votos), 0) as total_votos,
        pi.lista_nominal_oficial as lista_nominal,
        ROUND(COALESCE(SUM(rp.votos)::numeric * 100.0 / NULLIF(pi.lista_nominal_oficial, 0), 0), 2) as participacion_pct
    FROM eleccion e
    LEFT JOIN casilla c ON c.id_eleccion = e.id_eleccion
    LEFT JOIN resultados_electorales re ON re.pk_casilla = c.pk_casilla
    LEFT JOIN resultados_partido rp ON rp.pk_resultado = re.pk_resultado
    LEFT JOIN seccion s ON s.pk_seccion = c.pk_seccion
    LEFT JOIN LATERAL (
        SELECT SUM(lista_nominal_oficial) as lista_nominal_oficial
        FROM padron_ine
        WHERE anio_padron = e.anio 
          AND pk_seccion IN (SELECT pk_seccion FROM seccion WHERE id_municipio = %s)
    ) pi ON true
    WHERE s.id_municipio = %s
    GROUP BY e.anio, pi.lista_nominal_oficial
    ORDER BY e.anio
    """
    return pd.read_sql(query, engine, params=(MUNICIPIO_ID, MUNICIPIO_ID))

# ============================================
# 2. FUERZA ELECTORAL
# ============================================
def get_fuerza_electoral(anio):
    engine = get_engine()
    id_eleccion = get_id_eleccion(anio)
    query = """
    SELECT p.clave_partido, SUM(rp.votos) as votos,
           ROUND(SUM(rp.votos)::numeric * 100.0 / NULLIF(SUM(SUM(rp.votos)) OVER (), 0), 2) as porcentaje
    FROM partido p
    JOIN resultados_partido rp ON rp.id_partido = p.id_partido
    JOIN resultados_electorales re ON re.pk_resultado = rp.pk_resultado
    JOIN casilla c ON c.pk_casilla = re.pk_casilla
    JOIN seccion s ON s.pk_seccion = c.pk_seccion
    WHERE s.id_municipio = %s AND c.id_eleccion = %s
    GROUP BY p.clave_partido
    ORDER BY votos DESC
    """
    return pd.read_sql(query, engine, params=(MUNICIPIO_ID, id_eleccion))

# ============================================
# 3. OUTLIERS DE INTEGRIDAD
# ============================================
def get_outliers_integridad():
    engine = get_engine()
    query = """
    SELECT 
        e.anio, 
        s.seccion, 
        c.clave_casilla as num_casilla,
        SUM(rp.votos) as votos_emitidos, 
        re.lista_nominal_acta as lista_nominal_casilla,
        ROUND(SUM(rp.votos)::numeric * 100.0 / NULLIF(re.lista_nominal_acta, 0), 2) as participacion_pct
    FROM casilla c
    JOIN seccion s ON s.pk_seccion = c.pk_seccion
    JOIN eleccion e ON e.id_eleccion = c.id_eleccion
    JOIN resultados_electorales re ON re.pk_casilla = c.pk_casilla
    JOIN resultados_partido rp ON rp.pk_resultado = re.pk_resultado
    WHERE s.id_municipio = %s AND re.lista_nominal_acta > 0
    GROUP BY e.anio, s.seccion, c.clave_casilla, re.lista_nominal_acta
    HAVING SUM(rp.votos) > re.lista_nominal_acta * 0.95
    ORDER BY participacion_pct DESC
    """
    return pd.read_sql(query, engine, params=(MUNICIPIO_ID,))

# ============================================
# 4. MAPA DE GANADORES
# ============================================
def get_mapa_ganadores(anio):
    engine = get_engine()
    id_eleccion = get_id_eleccion(anio)
    query = """
    WITH votos_por_seccion AS (
        SELECT 
            s.pk_seccion, 
            s.seccion, 
            p.clave_partido as partido, 
            SUM(rp.votos) as votos
        FROM seccion s
        LEFT JOIN casilla c ON c.pk_seccion = s.pk_seccion AND c.id_eleccion = %s
        LEFT JOIN resultados_electorales re ON re.pk_casilla = c.pk_casilla
        LEFT JOIN resultados_partido rp ON rp.pk_resultado = re.pk_resultado
        LEFT JOIN partido p ON p.id_partido = rp.id_partido
        WHERE s.id_municipio = %s
        GROUP BY s.pk_seccion, s.seccion, p.clave_partido
    ),
    ganador_por_seccion AS (
        SELECT DISTINCT ON (pk_seccion) 
            pk_seccion, 
            seccion, 
            partido as ganador, 
            votos as votos_ganador
        FROM votos_por_seccion
        WHERE partido IS NOT NULL
        ORDER BY pk_seccion, votos DESC
    )
    SELECT 
        s.seccion, 
        COALESCE(g.ganador, 'SIN DATOS') as ganador, 
        COALESCE(g.votos_ganador, 0) as votos_ganador,
        pi.lista_nominal_oficial,
        ROUND(COALESCE(g.votos_ganador, 0)::numeric * 100.0 / NULLIF(pi.lista_nominal_oficial, 0), 2) as participacion_pct,
        ST_AsGeoJSON(s.geom) as geometry
    FROM seccion s
    LEFT JOIN ganador_por_seccion g ON g.pk_seccion = s.pk_seccion
    LEFT JOIN padron_ine pi ON pi.pk_seccion = s.pk_seccion AND pi.anio_padron = %s
    WHERE s.id_municipio = %s AND s.geom IS NOT NULL
    """
    df = pd.read_sql(query, engine, params=(id_eleccion, MUNICIPIO_ID, anio, MUNICIPIO_ID))
    if not df.empty and 'geometry' in df.columns:
        df['geometry'] = df['geometry'].apply(lambda x: shape(json.loads(x)) if x else None)
        df = df.dropna(subset=['geometry'])
        return gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
    return gpd.GeoDataFrame()

# ============================================
# 5. MAPA DE REZAGO
# ============================================
def get_mapa_rezago():
    engine = get_engine()
    query = """
    SELECT 
        s.seccion, 
        ci.pobtot,
        ci.pct_sin_derechohab,
        ci.grado_prom_escolar,
        ci.num_viviendas_particulares,
        COALESCE(ci.vph_sin_agua, 0) as vph_sin_agua,
        COALESCE(ci.vph_sin_drenaje, 0) as vph_sin_drenaje,
        COALESCE(ci.vph_sin_electricidad, 0) as vph_sin_electricidad,
        ROUND(COALESCE(ci.vph_sin_agua::numeric, 0) * 100.0 / 
              NULLIF(ci.num_viviendas_particulares, 0), 2) as pct_sin_agua,
        ROUND(COALESCE(ci.vph_sin_drenaje::numeric, 0) * 100.0 / 
              NULLIF(ci.num_viviendas_particulares, 0), 2) as pct_sin_drenaje,
        ROUND(COALESCE(ci.vph_sin_electricidad::numeric, 0) * 100.0 / 
              NULLIF(ci.num_viviendas_particulares, 0), 2) as pct_sin_electricidad,
        ROUND(
            (COALESCE(ci.pct_sin_derechohab, 0) + 
             COALESCE(ci.vph_sin_agua::numeric * 100.0 / NULLIF(ci.num_viviendas_particulares, 0), 0) +
             COALESCE(ci.vph_sin_drenaje::numeric * 100.0 / NULLIF(ci.num_viviendas_particulares, 0), 0)
            ) / 3.0, 2) as pct_sin_servicios_basicos,
        ST_AsGeoJSON(s.geom) as geometry
    FROM seccion s
    JOIN carencias_inegi ci ON ci.pk_seccion = s.pk_seccion
    WHERE s.id_municipio = %(municipio_id)s
      AND s.geom IS NOT NULL
      AND ci.anio_inegi = (SELECT MAX(anio_inegi) FROM carencias_inegi)
      AND ci.num_viviendas_particulares > 0
    """
    params = {'municipio_id': MUNICIPIO_ID}
    try:
        df = pd.read_sql(query, engine, params=params)
    except Exception:
        return gpd.GeoDataFrame()
    if df.empty:
        return gpd.GeoDataFrame()
    df['geometry'] = df['geometry'].apply(lambda x: shape(json.loads(x)) if x else None)
    df = df.dropna(subset=['geometry'])
    if df.empty:
        return gpd.GeoDataFrame()
    return gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')

# ============================================
# 6. MAPA DE SENTIMIENTO (ISC)
# ============================================
def get_mapa_sentimiento():
    engine = get_engine()
    query = """
    SELECT 
        s.seccion,
        COALESCE(vss.indice_satisfaccion_ciudadana, 50) as indice_satisfaccion_ciudadana,
        COALESCE(vss.calificacion_promedio, 3) as calificacion_promedio,
        COALESCE(vss.sentimiento_promedio, 0) as sentimiento_promedio,
        COALESCE(vss.total_opiniones, 0) as total_opiniones,
        CASE 
            WHEN COALESCE(vss.indice_satisfaccion_ciudadana, 50) >= 75 THEN 'Excelente'
            WHEN COALESCE(vss.indice_satisfaccion_ciudadana, 50) >= 60 THEN 'Bueno'
            WHEN COALESCE(vss.indice_satisfaccion_ciudadana, 50) >= 40 THEN 'Regular'
            ELSE 'Deficiente' 
        END as nivel_satisfaccion,
        ST_AsGeoJSON(s.geom) as geometry
    FROM seccion s
    LEFT JOIN vw_indice_satisfaccion_seccion vss ON vss.pk_seccion = s.pk_seccion
    WHERE s.id_municipio = %s AND s.geom IS NOT NULL
    """
    df = pd.read_sql(query, engine, params=(MUNICIPIO_ID,))
    if not df.empty and 'geometry' in df.columns:
        df['geometry'] = df['geometry'].apply(lambda x: shape(json.loads(x)) if x else None)
        df = df.dropna(subset=['geometry'])
        return gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
    return gpd.GeoDataFrame()

# ============================================
# 7. PERFIL DE GÉNERO
# ============================================
def get_perfil_genero():
    engine = get_engine()
    query = """
    SELECT 
        s.seccion, 
        pi.lista_nominal_oficial, 
        pi.lista_mujeres, 
        pi.lista_hombres,
        ROUND(pi.lista_mujeres::numeric * 100.0 / NULLIF(pi.lista_nominal_oficial, 0), 1) as pct_mujeres,
        ROUND(pi.lista_hombres::numeric * 100.0 / NULLIF(pi.lista_nominal_oficial, 0), 1) as pct_hombres,
        CASE 
            WHEN pi.lista_mujeres > pi.lista_hombres THEN 'Femenino'
            WHEN pi.lista_hombres > pi.lista_mujeres THEN 'Masculino'
            ELSE 'Equilibrado' 
        END as predominancia_genero
    FROM seccion s
    JOIN padron_ine pi ON pi.pk_seccion = s.pk_seccion
    WHERE s.id_municipio = %s AND pi.anio_padron = 2024 AND pi.lista_nominal_oficial > 0
    ORDER BY s.seccion
    """
    return pd.read_sql(query, engine, params=(MUNICIPIO_ID,))

# ============================================
# 8. TOP 20 SECCIONES ESTRATÉGICAS
# ============================================
def get_secciones_estrategicas_20():
    engine = get_engine()
    query = """
    SELECT 
        s.seccion, 
        pi.lista_nominal_oficial,
        ROUND(pi.lista_nominal_oficial::numeric * 100.0 / 
              (SELECT SUM(lista_nominal_oficial) 
               FROM padron_ine 
               WHERE anio_padron = 2024 
                 AND pk_seccion IN (SELECT pk_seccion FROM seccion WHERE id_municipio = %s)), 2) as pct_peso_electoral
    FROM seccion s
    JOIN padron_ine pi ON pi.pk_seccion = s.pk_seccion
    WHERE s.id_municipio = %s AND pi.anio_padron = 2024
    ORDER BY pi.lista_nominal_oficial DESC
    LIMIT 20
    """
    return pd.read_sql(query, engine, params=(MUNICIPIO_ID, MUNICIPIO_ID))

# ============================================
# 9. CORRELACIÓN PARTICIPACIÓN VS CARENCIAS
# ============================================
def get_correlacion_participacion_carencias(anio):
    engine = get_engine()
    id_eleccion = get_id_eleccion(anio)
    query = """
    WITH participacion_seccion AS (
        SELECT 
            s.pk_seccion, 
            s.seccion, 
            COALESCE(SUM(rp.votos), 0) as votos_totales, 
            pi.lista_nominal_oficial,
            ROUND(COALESCE(SUM(rp.votos)::numeric, 0) * 100.0 / NULLIF(pi.lista_nominal_oficial, 0), 2) as participacion_pct
        FROM seccion s
        LEFT JOIN casilla c ON c.pk_seccion = s.pk_seccion AND c.id_eleccion = %s
        LEFT JOIN resultados_electorales re ON re.pk_casilla = c.pk_casilla
        LEFT JOIN resultados_partido rp ON rp.pk_resultado = re.pk_resultado
        LEFT JOIN padron_ine pi ON pi.pk_seccion = s.pk_seccion AND pi.anio_padron = %s
        WHERE s.id_municipio = %s
        GROUP BY s.pk_seccion, s.seccion, pi.lista_nominal_oficial
    )
    SELECT 
        ps.seccion, 
        COALESCE(ps.participacion_pct, 0) as participacion_pct,
        ci.pct_sin_derechohab,
        ci.grado_prom_escolar,
        ROUND(
            (COALESCE(ci.vph_sin_agua::numeric, 0) * 100.0 / NULLIF(ci.num_viviendas_particulares, 0) +
             COALESCE(ci.vph_sin_drenaje::numeric, 0) * 100.0 / NULLIF(ci.num_viviendas_particulares, 0)
            ) / 2.0, 2) as pct_sin_agua_drenaje,
        ci.pobtot
    FROM participacion_seccion ps
    JOIN carencias_inegi ci ON ci.pk_seccion = ps.pk_seccion
    WHERE ci.pobtot > 0
      AND ci.anio_inegi = (SELECT MAX(anio_inegi) FROM carencias_inegi)
    ORDER BY ps.seccion
    """
    return pd.read_sql(query, engine, params=(id_eleccion, anio, MUNICIPIO_ID))

# ============================================
# 10. TOP 10 SECCIONES CON MAYOR REZAGO
# ============================================
def get_seccion_rezago_top10():
    engine = get_engine()
    query = """
    SELECT 
        s.seccion, 
        ci.pobtot,
        ROUND(
            (COALESCE(ci.pct_sin_derechohab, 0) + 
             COALESCE(ci.vph_sin_agua::numeric * 100.0 / NULLIF(ci.num_viviendas_particulares, 0), 0) +
             COALESCE(ci.vph_sin_drenaje::numeric * 100.0 / NULLIF(ci.num_viviendas_particulares, 0), 0)
            ) / 3.0, 2) as pct_sin_servicios
    FROM seccion s
    JOIN carencias_inegi ci ON ci.pk_seccion = s.pk_seccion
    WHERE s.id_municipio = %s AND ci.pobtot > 0
      AND ci.anio_inegi = (SELECT MAX(anio_inegi) FROM carencias_inegi)
    ORDER BY pct_sin_servicios DESC, ci.pobtot DESC
    LIMIT 10
    """
    return pd.read_sql(query, engine, params=(MUNICIPIO_ID,))

# ============================================
# 11. RIESGO ELECTORAL
# ============================================
def get_riesgo_electoral():
    engine = get_engine()
    query = """
    SELECT 
        seccion, 
        ganador_2024, 
        votos_ganador, 
        lista_nominal_oficial, 
        pct_votos,
        indice_satisfaccion, 
        num_opiniones, 
        nivel_riesgo_electoral, 
        accion_recomendada
    FROM vw_riesgo_electoral
    ORDER BY indice_satisfaccion ASC
    """
    return pd.read_sql(query, engine)

# ============================================
# 12. SATISFACCIÓN POR SERVICIO
# ============================================
def get_satisfaccion_por_servicio_agregado():
    engine = get_engine()
    query = """
    SELECT 
        cs.nombre_categoria, 
        cs.pilar_gobierno, 
        ROUND(AVG(ss.calificacion), 2) as calificacion_promedio,
        COUNT(*) as total_opiniones,
        CASE 
            WHEN AVG(ss.calificacion) >= 4.0 THEN 'Excelente'
            WHEN AVG(ss.calificacion) >= 3.0 THEN 'Bueno'
            WHEN AVG(ss.calificacion) >= 2.0 THEN 'Regular'
            ELSE 'Deficiente' 
        END as nivel
    FROM sentimiento_social ss
    JOIN categoria_servicio cs ON cs.id_categoria = ss.id_categoria
    WHERE ss.calificacion IS NOT NULL
    GROUP BY cs.nombre_categoria, cs.pilar_gobierno
    ORDER BY calificacion_promedio DESC
    """
    return pd.read_sql(query, engine)

# ============================================
# NUEVAS FUNCIONES - FASE 2 (ALERTAS E INSIGHTS)
# ============================================

def get_alertas_conflicto(umbral_rezago=40, umbral_isc=40):
    """
    Retorna DataFrame con secciones que tienen:
    - Rezago social > umbral_rezago
    - ISC < umbral_isc
    """
    engine = get_engine()
    query = """
    SELECT 
        s.seccion,
        r.pct_sin_servicios_basicos as rezago,
        COALESCE(vss.indice_satisfaccion_ciudadana, 50) as isc,
        s.pk_seccion
    FROM seccion s
    LEFT JOIN vw_rezago_secciones r ON r.pk_seccion = s.pk_seccion
    LEFT JOIN vw_indice_satisfaccion_seccion vss ON vss.pk_seccion = s.pk_seccion
    WHERE s.id_municipio = %(municipio_id)s
      AND r.pct_sin_servicios_basicos > %(umbral_rezago)s
      AND COALESCE(vss.indice_satisfaccion_ciudadana, 50) < %(umbral_isc)s
    ORDER BY r.pct_sin_servicios_basicos DESC, vss.indice_satisfaccion_ciudadana ASC
    """
    params = {'municipio_id': MUNICIPIO_ID, 'umbral_rezago': umbral_rezago, 'umbral_isc': umbral_isc}
    return pd.read_sql(query, engine, params=params)

def get_acciones_prioritarias_24h(top_n=3):
    """
    Retorna las N secciones con mayor urgencia basada en:
    - Top 20 por peso electoral
    - Mayor rezago social
    - Menor ISC
    """
    engine = get_engine()
    query = """
    WITH top20 AS (
        SELECT 
            pi.pk_seccion,
            s.seccion,
            pi.lista_nominal_oficial,
            ROW_NUMBER() OVER (ORDER BY pi.lista_nominal_oficial DESC) as rank_peso
        FROM padron_ine pi
        JOIN seccion s ON s.pk_seccion = pi.pk_seccion
        WHERE pi.anio_padron = 2024 
          AND s.id_municipio = %(municipio_id)s
        ORDER BY pi.lista_nominal_oficial DESC
        LIMIT 20
    )
    SELECT 
        t.seccion,
        t.lista_nominal_oficial as peso_electoral,
        COALESCE(r.pct_sin_servicios_basicos, 0) as rezago,
        COALESCE(vss.indice_satisfaccion_ciudadana, 50) as isc,
        ROUND(
            (t.rank_peso * 0.3) + 
            (COALESCE(r.pct_sin_servicios_basicos, 0) * 0.5) + 
            ((100 - COALESCE(vss.indice_satisfaccion_ciudadana, 50)) * 0.2)
        , 0) as prioridad_score
    FROM top20 t
    LEFT JOIN vw_rezago_secciones r ON r.pk_seccion = t.pk_seccion
    LEFT JOIN vw_indice_satisfaccion_seccion vss ON vss.pk_seccion = t.pk_seccion
    ORDER BY prioridad_score DESC
    LIMIT %(top_n)s
    """
    params = {'municipio_id': MUNICIPIO_ID, 'top_n': top_n}
    return pd.read_sql(query, engine, params=params)

# ============================================
# 14. LISTA DE SECCIONES PARA SELECTOR
# ============================================
def get_lista_secciones():
    engine = get_engine()
    query = "SELECT seccion FROM seccion WHERE id_municipio = %s ORDER BY seccion"
    df = pd.read_sql(query, engine, params=(MUNICIPIO_ID,))
    return df['seccion'].tolist()

# ============================================
# 15. TOTAL DE SECCIONES
# ============================================
def get_total_secciones():
    engine = get_engine()
    query = "SELECT COUNT(*) FROM seccion WHERE id_municipio = %s"
    return pd.read_sql(query, engine, params=(MUNICIPIO_ID,)).iloc[0,0]

# ============================================
# 16. VERIFICAR SI UNA SECCIÓN ESTÁ EN TOP 20
# ============================================
def es_top20(seccion):
    """Devuelve True si la sección está en el top 20 por peso electoral."""
    top20 = get_secciones_estrategicas_20()
    return seccion in top20['seccion'].values

# ============================================
# 17. DATOS CONSOLIDADOS DE UNA SECCIÓN
# ============================================
def get_datos_seccion(seccion):
    """Obtiene datos consolidados de una sección."""
    engine = get_engine()
    query = """
    SELECT 
        s.seccion,
        pi.lista_nominal_oficial,
        pi.lista_mujeres,
        pi.lista_hombres,
        COALESCE(r.pct_sin_agua, 0) as pct_sin_agua,
        COALESCE(r.pct_sin_drenaje, 0) as pct_sin_drenaje,
        COALESCE(r.pct_sin_electricidad, 0) as pct_sin_electricidad,
        COALESCE(r.pct_sin_servicios_basicos, 0) as rezago,
        COALESCE(vss.indice_satisfaccion_ciudadana, 50) as isc,
        COALESCE(vss.total_opiniones, 0) as num_opiniones,
        (SELECT ganador_2024 FROM vw_riesgo_electoral WHERE seccion = s.seccion LIMIT 1) as ganador_2024,
        (SELECT pct_votos FROM vw_riesgo_electoral WHERE seccion = s.seccion LIMIT 1) as pct_votos
    FROM seccion s
    LEFT JOIN padron_ine pi ON pi.pk_seccion = s.pk_seccion AND pi.anio_padron = 2024
    LEFT JOIN vw_rezago_secciones r ON r.seccion = s.seccion
    LEFT JOIN vw_indice_satisfaccion_seccion vss ON vss.seccion = s.seccion
    WHERE s.seccion = %s AND s.id_municipio = %s
    """
    return pd.read_sql(query, engine, params=(seccion, MUNICIPIO_ID))

# ============================================
# 18. GENERADOR DE SCRIPT DE TERRITORIO
# ============================================
def generar_script_territorio(row):
    """Genera un mensaje estratégico basado en los datos de la sección."""
    mensaje = f"**Sección {row['seccion']}**\n\n"
    
    poblacion = row['lista_nominal_oficial']
    if poblacion and poblacion > 0:
        pct_mujeres = (row['lista_mujeres'] / poblacion * 100)
        pct_hombres = 100 - pct_mujeres
    else:
        pct_mujeres = 0
        pct_hombres = 0
    
    es_femenino = pct_mujeres > 50
    es_top = es_top20(row['seccion'])
    
    prioridades = []
    if row['pct_sin_agua'] > 10:
        prioridades.append("agua potable")
    if row['pct_sin_drenaje'] > 10:
        prioridades.append("drenaje")
    if row['pct_sin_electricidad'] > 5:
        prioridades.append("electricidad")
    
    mensaje += f"👥 **Población:** {poblacion:,} electores ({pct_mujeres:.1f}% mujeres, {pct_hombres:.1f}% hombres).\n"
    mensaje += f"📉 **Rezago:** {row['rezago']:.1f}% de carencias básicas.\n"
    mensaje += f"😊 **Satisfacción ciudadana:** {row['isc']:.1f} puntos (ISC).\n"
    
    if row['ganador_2024']:
        mensaje += f"🏛️ **Ganador 2024:** {row['ganador_2024']} con {row['pct_votos']:.1f}% de votos.\n"
    
    mensaje += "\n**💧 Prioridades de inversión FAISMUN:**\n"
    if prioridades:
        for p in prioridades:
            mensaje += f"- Mejorar infraestructura de **{p}**.\n"
        if es_top and row['pct_sin_agua'] > 10:
            mensaje += f"\n🚨 **PROPUESTA PRIORITARIA:** En esta sección estratégica (Top 20), destinaremos recursos del FAISMUN 2025 para resolver el problema de agua potable. ¡Es una de nuestras prioridades!\n"
    else:
        mensaje += "- No se detectan carencias críticas en servicios básicos.\n"
    
    if es_femenino:
        mensaje += "\n👩 **Enfoque de género:** Esta sección tiene mayoría femenina. Priorizaremos mensajes sobre salud, seguridad social y programas de apoyo a madres trabajadoras.\n"
        if es_top:
            mensaje += "🩺 **Acción específica:** Implementaremos jornadas de salud y fortalecimiento de programas sociales en esta zona.\n"
    else:
        mensaje += "\n👨 **Enfoque de género:** Sección con mayoría masculina. Enfatizaremos empleo, infraestructura y seguridad.\n"
    
    if prioridades:
        tema = prioridades[0]
        mensaje += f"\n🎯 **Mensaje clave:** 'Vamos a llevar **{tema}** a tu colonia con el FAISMUN 2025. ¡Ya es hora de resolverlo!'"
    elif row['isc'] < 40:
        mensaje += "\n🎯 **Mensaje clave:** 'Escuchamos tu descontento. Iniciamos mesas de trabajo para mejorar los servicios en tu sector.'"
    else:
        mensaje += "\n🎯 **Mensaje clave:** 'Seguimos trabajando por tu bienestar. Gracias por tu confianza.'"
    
    return mensaje
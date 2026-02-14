# ============================================
# DASHBOARD ELECTORAL TAXCO 2024
# Sistema de Inteligencia Política
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path
import os

# Configurar path
DASHBOARD_PATH = Path(__file__).parent
sys.path.insert(0, str(DASHBOARD_PATH))

# Imports locales
try:
    from config import *
    from queries import *
except ImportError as e:
    st.error(f"Error al importar módulos: {e}")
    st.stop()

# ============================================
# CONFIGURACIÓN DE PÁGINA
# ============================================
st.set_page_config(
    page_title="Dashboard Electoral Taxco 2024",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# TEMA OSCURO PREMIUM - GLASSMORPHISM
# ============================================
st.markdown("""
<style>
    /* Fondo general oscuro */
    .stApp {
        background: #0a0c0e;
        background-image: radial-gradient(circle at 15% 50%, rgba(66, 66, 66, 0.2) 0%, transparent 25%),
                          radial-gradient(circle at 85% 30%, rgba(100, 100, 100, 0.15) 0%, transparent 30%);
    }
    
    /* Tarjetas con efecto glassmorphism */
    div[data-testid="stMetric"], 
    div[data-testid="stMetricDelta"],
    div.stDataFrame,
    div[data-testid="stHorizontalBlock"] > div,
    section[data-testid="stSidebar"] {
        background: rgba(18, 22, 25, 0.75) !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        color: #f0f2f6;
    }
    
    /* Sidebar específico */
    section[data-testid="stSidebar"] {
        background: rgba(10, 12, 14, 0.95) !important;
        backdrop-filter: blur(12px);
        border-right: 1px solid rgba(192, 192, 192, 0.2);
    }
    
    /* Texto y métricas - SIN TRUNCAMIENTO */
    .stMetric label, .stMetric [data-testid="stMetricLabel"] {
        color: #c0c4cc !important;
        font-weight: 500;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        font-size: 0.8rem;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        word-break: break-word;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        color: white !important;
        font-size: 2.2rem !important;
        font-weight: 600;
        line-height: 1.2;
        text-shadow: 0 2px 10px rgba(255,255,255,0.1);
        white-space: normal !important;
        overflow: visible !important;
    }
    
    .stMetric [data-testid="stMetricDelta"] {
        background: rgba(255,255,255,0.05);
        padding: 4px 8px;
        border-radius: 20px;
        font-size: 0.8rem;
    }
    
    /* Títulos estratégicos */
    h1, h2, h3 {
        color: white !important;
        font-weight: 600;
        letter-spacing: -0.5px;
        border-bottom: 2px solid rgba(192, 192, 192, 0.3) !important;
        padding-bottom: 12px;
    }
    
    h1 {
        background: linear-gradient(135deg, #ffffff, #c0c0c0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        border-bottom: none !important;
    }
    
    /* Selectores y controles */
    .stSelectbox, .stSlider, .stRadio {
        background: rgba(30, 34, 40, 0.6);
        border-radius: 12px;
        padding: 10px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    
    /* Mapas - bordes y sombra */
    .js-plotly-plot {
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Alertas y cajas de insight */
    .alert-box, .success-box, .info-box {
        background: rgba(25, 30, 35, 0.8) !important;
        backdrop-filter: blur(8px);
        border-left-width: 6px !important;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    
    .alert-box {
        border-left-color: #ff4b4b !important;
    }
    .success-box {
        border-left-color: #00d4aa !important;
    }
    .info-box {
        border-left-color: #3b9eff !important;
    }
    
    /* Scrollbar personalizada */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
        background: #1a1e22;
    }
    ::-webkit-scrollbar-thumb {
        background: #4a4e54;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #6b6f76;
    }
    
    /* Ocultar divisor blanco (st.divider) */
    hr {
        display: none !important;
    }
    
    /* Ocultar botón de pantalla completa */
    button[title="View fullscreen"] {
        display: none !important;
    }
    
    /* Responsive para móvil */
    @media (max-width: 768px) {
        div[data-testid="stMetric"] {
            padding: 12px !important;
        }
        .stMetric [data-testid="stMetricValue"] {
            font-size: 1.6rem !important;
        }
        h1 {
            font-size: 1.8rem !important;
        }
    }
            /* FORZAR QUE LOS VALORES Y ETIQUETAS NO SE TRUNQUEN */
div[data-testid="stMetric"] {
    overflow: visible !important;
}
div[data-testid="stMetric"] > div {
    overflow: visible !important;
}
div[data-testid="stMetricLabel"] p,
div[data-testid="stMetricValue"] p,
div[data-testid="stMetricDelta"] p {
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
}
/* Ajuste específico para el partido (MORENA) */
div[data-testid="stMetricValue"] p {
    font-size: 1.9rem !important; /* un poco más pequeño si es necesario */
}
            /* Estilo consistente para las tarjetas personalizadas */
div[data-testid="column"] > div {
    width: 100% !important;
}
            /* Forzar que las columnas no oculten contenido */
div[data-testid="column"] {
    overflow: visible !important;
}
div[data-testid="column"] > div {
    overflow: visible !important;
}
/* Evitar cualquier restricción de ancho en los contenedores de st.markdown */
.element-container {
    overflow: visible !important;
}
            /* ============================================
   ESTILOS PARA LOS KPIS PERSONALIZADOS
   ============================================ */
.kpi-card {
    background: rgba(18, 22, 25, 0.75);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.kpi-label {
    color: #c0c4cc;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
    white-space: nowrap;
}

.kpi-value {
    color: white;
    font-size: 1.8rem;
    font-weight: 600;
    line-height: 1.2;
    white-space: nowrap;
}

.kpi-delta {
    background: rgba(255,255,255,0.05);
    padding: 4px 8px;
    border-radius: 20px;
    font-size: 0.8rem;
    margin-top: 8px;
    display: inline-block;
    white-space: nowrap;
    align-self: flex-start;
}

/* ============================================
   OCULTAR ELEMENTOS DE LA INTERFAZ DE STREAMLIT
   ============================================ */
header[data-testid="stHeader"] {
    display: none !important;
}
footer {
    display: none !important;
}
#MainMenu {
    display: none !important;
}
.stApp > header {
    display: none !important;
}

/* ============================================
   MEJORAS DE RESPONSIVE
   ============================================ */
@media (max-width: 768px) {
    .kpi-value {
        font-size: 1.4rem;
    }
    .kpi-label {
        font-size: 0.6rem;
    }
    .kpi-delta {
        font-size: 0.7rem;
    }
    .kpi-card {
        padding: 12px;
    }
}

/* Para pantallas muy pequeñas, apilar columnas */
@media (max-width: 480px) {
    div[data-testid="column"] {
        min-width: 100% !important;
        margin-bottom: 10px;
    }
}
</style>
""", unsafe_allow_html=True)

# ============================================
# HEADER CON ESCUDO DE TAXCO
# ============================================
col_logo, col_titulo = st.columns([1, 4])


with col_logo:
    # Intentar cargar el escudo; si no existe, mostrar un placeholder
    escudo_path = Path(__file__).parent / "escudo_taxco.png"
    if escudo_path.exists():
        st.image(str(escudo_path), width=80)
    else:
        # Placeholder: círculo con iniciales (no rompe la app)
        st.markdown("""
        <div style="background: linear-gradient(135deg, #B8242B, #8B1A1A); 
                    width: 80px; height: 80px; border-radius: 50%; 
                    display: flex; align-items: center; justify-content: center;
                    font-size: 32px; color: white; font-weight: bold;">
            T
        </div>
        """, unsafe_allow_html=True)

with col_titulo:
    st.title(f"🗳️ Dashboard Electoral Gobierno - {MUNICIPIO_NOMBRE}")
    st.caption(f"Sistema de Inteligencia Política | Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ============================================
# SIDEBAR - PANEL DE CONTROL + ACCIONES 24H
# ============================================
with st.sidebar:
    st.header("⚙️ Panel de Control")
    
    anio_seleccionado = st.selectbox(
        "📅 Elección",
        ANIOS_DISPONIBLES,
        index=len(ANIOS_DISPONIBLES)-1,
        key='selector_anio',
        help="Selecciona el año electoral"
    )
    
    st.divider()
    
    vista_mapa = st.radio(
        "🗺️ Vista del Mapa",
        [
            "Electoral (Ganadores)", 
            "Social (Rezago INEGI)", 
            "Demográfico (Género)",
            "Sentimiento Social (ISC)"
        ],
        key='radio_vista_mapa',
        help="Cambia la capa del mapa"
    )
    
    st.divider()
    
    st.subheader("🔍 Filtros")
    filtro_participacion = st.slider(
        "Participación mínima (%)",
        0, 100, 0,
        key='slider_participacion'
    )
    mostrar_outliers = st.checkbox(
        "⚠️ Solo anomalías",
        help="Casillas con >100% participación",
        key='chk_outliers'
    )
    
    st.divider()
    
    st.subheader("📊 Indicador de Desigualdad")
    st.metric("Coeficiente de Gini", "0.417", help="Nivel de desigualdad económica")
    st.caption("**Interpretación:** Desigualdad moderada-alta.")
    
    # ========================================
    # PANEL DE ACCIONES PRIORITARIAS 24H
    # ========================================
    st.divider()
    st.subheader("⚡ ACCIONES PRIORITARIAS 24h")
    # TODO: Reemplazar con implementación que no use vistas
    # df_acciones = get_acciones_prioritarias_24h(top_n=3)
    df_acciones = pd.DataFrame()  # DataFrame vacío temporalmente    if not df_acciones.empty:
        for _, row in df_acciones.iterrows():
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.05); border-left: 4px solid #00d4aa; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 24px;">📍</span>
                    <span style="font-weight: 600;">Sección {int(row['seccion'])}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 8px;">
                    <span style="color: #c0c0c0;">Peso electoral</span>
                    <span style="font-weight: 600;">{row['peso_electoral']:,}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #c0c0c0;">Rezago</span>
                    <span style="font-weight: 600; color: {'#ff4b4b' if row['rezago'] > 40 else '#ff9800' if row['rezago'] > 20 else '#4caf50'};">{row['rezago']:.1f}%</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #c0c0c0;">ISC</span>
                    <span style="font-weight: 600; color: {'#ff4b4b' if row['isc'] < 40 else '#ff9800' if row['isc'] < 60 else '#4caf50'};">{row['isc']:.1f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No hay secciones prioritarias urgentes.")

# ============================================
# TABS PRINCIPALES
# ============================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard Electoral", 
    "💰 Prioridades de Inversión 2025",
    "👥 Análisis de Género",
    "🚨 Riesgo Electoral",
    "📥 Reportes y Exportación"
])

# ============================================
# TAB 1: DASHBOARD ELECTORAL
# ============================================
with tab1:
    st.header("🎯 Indicadores Estratégicos de Mando")
    
    # Cargar datos
    df_participacion = get_kpis_participacion()
    df_fuerza = get_fuerza_electoral(anio_seleccionado)
    df_outliers = get_outliers_integridad()
    
    # Validar datos del año seleccionado
    df_year = df_participacion[df_participacion['anio'] == anio_seleccionado]
    if df_year.empty:
        st.warning(f"⚠️ No hay datos de padrón INE para {anio_seleccionado}. Solo disponible 2024")
        participacion_actual = None
        delta_participacion = None
        votos_totales = None
        lista_nominal = None
    else:
        participacion_actual = df_year['participacion_pct'].values[0]
        df_anterior = df_participacion[df_participacion['anio'] < anio_seleccionado]
        if not df_anterior.empty:
            participacion_anterior = df_anterior.iloc[-1]['participacion_pct']
            delta_participacion = participacion_actual - participacion_anterior
        else:
            delta_participacion = None
        votos_totales = df_year['total_votos'].values[0]
        lista_nominal = df_year['lista_nominal'].values[0]
    
    num_outliers = len(df_outliers[df_outliers['anio'] == anio_seleccionado])
    num_outliers_criticos = len(df_outliers[(df_outliers['anio'] == anio_seleccionado) & (df_outliers['participacion_pct'] > 100)])
    
  
       # ============================================
    # KPIS PERSONALIZADOS - VERSIÓN PROFESIONAL
    # ============================================
    col1, col2, col3, col4, col5 = st.columns([1.2, 1.3, 1.2, 1.1, 0.9])

    with col1:
        valor_part = f"{participacion_actual:.1f}%" if participacion_actual is not None and participacion_actual > 0 else "N/D"
        delta_part = f"{delta_participacion:+.1f}%" if delta_participacion is not None and abs(delta_participacion) > 0.01 else None
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">📊 Legitimidad</div>
            <div class="kpi-value">{valor_part}</div>
            {f'<div class="kpi-delta">{delta_part}</div>' if delta_part else ''}
        </div>
        """, unsafe_allow_html=True)

    with col2:
        valor_votos = f"{int(votos_totales):,}" if votos_totales is not None and votos_totales > 0 else "N/D"
        delta_votos = f"de {int(lista_nominal):,}" if lista_nominal is not None and lista_nominal > 0 else None
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">🗳️ Fuerza</div>
            <div class="kpi-value">{valor_votos}</div>
            {f'<div class="kpi-delta">{delta_votos}</div>' if delta_votos else ''}
        </div>
        """, unsafe_allow_html=True)

    with col3:
        if not df_fuerza.empty:
            ganador = df_fuerza.iloc[0]
            valor_mando = ganador['clave_partido']
            delta_mando = f"{ganador['porcentaje']:.1f}%"
        else:
            valor_mando = "N/D"
            delta_mando = None
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">🏆 Mando</div>
            <div class="kpi-value">{valor_mando}</div>
            {f'<div class="kpi-delta">{delta_mando}</div>' if delta_mando else ''}
        </div>
        """, unsafe_allow_html=True)

    with col4:
        delta_outliers = f"{num_outliers_criticos} críticas" if num_outliers_criticos > 0 else "OK"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">⚠️ Incidencias</div>
            <div class="kpi-value">{num_outliers}</div>
            <div class="kpi-delta" style="color: {'#ff4b4b' if num_outliers_criticos > 0 else '#00d4aa'};">{delta_outliers}</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        try:
            total_secciones = get_total_secciones()
        except:
            total_secciones = 87
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">📍 Secciones</div>
            <div class="kpi-value">{total_secciones}</div>
            <div class="kpi-delta">2 s/c</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========================================
    # FUERZA ELECTORAL
    # ========================================
    st.header(f"🏛️ Fuerza Electoral {anio_seleccionado}")
    if not df_fuerza.empty:
        col_grafica, col_tabla = st.columns([2, 1])
        with col_grafica:
            top_partidos = df_fuerza.head(7)
            colores = [COLORES_PARTIDOS.get(p, '#888888') for p in top_partidos['clave_partido']]
            fig_fuerza = go.Figure()
            fig_fuerza.add_trace(go.Bar(
                y=top_partidos['clave_partido'],
                x=top_partidos['votos'],
                orientation='h',
                text=[f"{v:,} ({p:.1f}%)" for v, p in zip(top_partidos['votos'], top_partidos['porcentaje'])],
                textposition='outside',
                marker=dict(color=colores),
                hovertemplate="<b>%{y}</b><br>Votos: %{x:,}<extra></extra>"
            ))
            fig_fuerza.update_layout(
                title=f"Distribución de Votos - {anio_seleccionado}",
                xaxis_title="Votos",
                height=400,
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig_fuerza, use_container_width=True)
        with col_tabla:
            st.subheader("📋 Detalle")
            df_tabla = df_fuerza[['clave_partido', 'votos', 'porcentaje']].copy()
            df_tabla.columns = ['Partido', 'Votos', '%']
            df_tabla['Votos'] = df_tabla['Votos'].apply(lambda x: f"{x:,}")
            df_tabla['%'] = df_tabla['%'].apply(lambda x: f"{x:.2f}")
            st.dataframe(df_tabla, hide_index=True, height=380, use_container_width=True)
    else:
        st.info(f"ℹ️ No hay datos de votos por partido para {anio_seleccionado}")
    
    # ========================================
    # MAPA ELECTORAL GEORREFERENCIADO
    # ========================================
    st.header("🗺️ Mapa Electoral Georreferenciado")
    
    if vista_mapa == "Electoral (Ganadores)":
        gdf_mapa = get_mapa_ganadores(anio_seleccionado)
        if not gdf_mapa.empty and 'geometry' in gdf_mapa.columns:
            # Íconos y popup
            gdf_mapa['icono_partido'] = gdf_mapa['ganador'].map({
                'MORENA': '🟡', 'PAN': '🔵', 'PRI': '🔴', 'PRD': '🟡',
                'MC': '🟠', 'PT': '🔴', 'PVEM': '🟢', 'NA': '🔵',
                'SIN DATOS': '⚪'
            }).fillna('⚪')
            
            gdf_mapa['hover_text'] = gdf_mapa.apply(lambda row:
                f"""
                <div style='font-family: "Inter", sans-serif; padding: 8px;'>
                    <b style='font-size: 16px;'>🗳️ Sección {row['seccion']}</b><br>
                    <span style='color: #c0c0c0;'>{row['icono_partido']} Ganador: <b>{row['ganador']}</b></span><br>
                    <span>📊 Votos: <b>{row['votos_ganador']:,.0f}</b></span><br>
                    <span>📋 Lista Nominal: <b>{f"{row['lista_nominal_oficial']:,.0f}" if pd.notna(row['lista_nominal_oficial']) else 'N/D'}</b></span><br>
                    <span>📈 Participación: <b>{f"{row['participacion_pct']:.1f}%" if pd.notna(row['participacion_pct']) else 'N/D'}</b></span><br>
                    { '⚠️ <span style="color: #ff9800;">AUDITORÍA REQUERIDA</span>' if pd.notna(row.get('votos_ganador')) and pd.notna(row.get('lista_nominal_oficial')) and row['votos_ganador'] > row['lista_nominal_oficial'] else '✅ <span style="color: #4caf50;">OK</span>' }
                </div>
                """,
                axis=1
            )
            
            # Crear mapa base
            fig_mapa = px.choropleth_mapbox(
                gdf_mapa,
                geojson=gdf_mapa.geometry.__geo_interface__,
                locations=gdf_mapa.index,
                color='ganador',
                color_discrete_map=COLORES_PARTIDOS,
                mapbox_style="open-street-map",
                zoom=ZOOM_INICIAL,
                center={"lat": CENTRO_MAPA["lat"], "lon": CENTRO_MAPA["lon"]},
                opacity=0.65,
                custom_data=['hover_text']
            )
            
            # Etiquetas de sección (centroides)
            gdf_mapa['centroid'] = gdf_mapa.geometry.centroid
            fig_mapa.add_trace(go.Scattermapbox(
                lat=gdf_mapa.centroid.y,
                lon=gdf_mapa.centroid.x,
                mode='text',
                text=gdf_mapa['seccion'].astype(str),
                textfont=dict(size=10, color='white', family='Inter, sans-serif'),
                textposition='middle center',
                hoverinfo='none',
                showlegend=False
            ))
            
            fig_mapa.update_traces(hovertemplate='%{customdata[0]}<extra></extra>')
            fig_mapa.update_layout(
                title=f"Partido Ganador por Sección - {anio_seleccionado}",
                height=600,
                margin={"r":0,"t":40,"l":0,"b":0},
                font_color='white',
                paper_bgcolor='rgba(0,0,0,0)',
                geo=dict(bgcolor='rgba(0,0,0,0)')
            )
            st.plotly_chart(fig_mapa, use_container_width=True)
            
            # Estadísticas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("MORENA", len(gdf_mapa[gdf_mapa['ganador'] == 'MORENA']))
            with col2:
                st.metric("PAN", len(gdf_mapa[gdf_mapa['ganador'] == 'PAN']))
            with col3:
                st.metric("MC", len(gdf_mapa[gdf_mapa['ganador'] == 'MC']))
        else:
            st.warning(f"⚠️ No hay datos geográficos para {anio_seleccionado}")
    
    elif vista_mapa == "Social (Rezago INEGI)":
        gdf_rezago = get_mapa_rezago()
        if gdf_rezago.empty:
            st.warning("⚠️ No hay datos de rezago social disponibles para el municipio.")
        else:
            # Popup con íconos
            gdf_rezago['icono_agua'] = gdf_rezago['pct_sin_agua'].apply(lambda x: '💧🚫' if x > 30 else '💧')
            gdf_rezago['hover_text'] = gdf_rezago.apply(lambda row:
                f"""
                <div style='font-family: "Inter", sans-serif; padding: 8px;'>
                    <b style='font-size: 16px;'>🏘️ Sección {row['seccion']}</b><br>
                    <span>{row['icono_agua']} Sin agua: <b>{row['pct_sin_agua']:.1f}%</b></span><br>
                    <span>🚽 Sin drenaje: <b>{row['pct_sin_drenaje']:.1f}%</b></span><br>
                    <span>⚡ Sin electricidad: <b>{row['pct_sin_electricidad']:.1f}%</b></span><br>
                    <span>📊 Rezago global: <b style='color: {"#ff4b4b" if row["pct_sin_servicios_basicos"]>40 else "#ff9800" if row["pct_sin_servicios_basicos"]>20 else "#4caf50"};'>{row['pct_sin_servicios_basicos']:.1f}%</b></span>
                </div>
                """,
                axis=1
            )
            fig_rezago = px.choropleth_mapbox(
                gdf_rezago,
                geojson=gdf_rezago.geometry.__geo_interface__,
                locations=gdf_rezago.index,
                color='pct_sin_servicios_basicos',
                color_continuous_scale="Reds",
                range_color=[0, gdf_rezago['pct_sin_servicios_basicos'].max()],
                mapbox_style="open-street-map",
                zoom=ZOOM_INICIAL,
                center={"lat": CENTRO_MAPA["lat"], "lon": CENTRO_MAPA["lon"]},
                opacity=0.65,
                custom_data=['hover_text']
            )
            fig_rezago.update_traces(hovertemplate='%{customdata[0]}<extra></extra>')
            fig_rezago.update_layout(
                title="Índice de Rezago Social (INEGI)",
                height=600,
                margin={"r":0,"t":40,"l":0,"b":0},
                font_color='white',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_rezago, use_container_width=True)
            st.markdown("""
            <div class="success-box">
                <strong>💡 INSIGHT:</strong> Zonas rojas = mayor rezago. Priorizar en FAISMUN 2025.
            </div>
            """, unsafe_allow_html=True)
    
    elif vista_mapa == "Demográfico (Género)":
        df_genero = get_perfil_genero()
        gdf_mapa_base = get_mapa_ganadores(2024)
        if not gdf_mapa_base.empty and not df_genero.empty:
            gdf_genero = gdf_mapa_base.merge(
                df_genero[['seccion', 'pct_mujeres', 'predominancia_genero']],
                on='seccion'
            )
            # Popup con íconos de género
            gdf_genero['icono_genero'] = gdf_genero['predominancia_genero'].map({
                'Femenino': '👩', 'Masculino': '👨', 'Equilibrado': '👥'
            })
            gdf_genero['hover_text'] = gdf_genero.apply(lambda row:
                f"""
                <div style='font-family: "Inter", sans-serif; padding: 8px;'>
                    <b style='font-size: 16px;'>👥 Sección {row['seccion']}</b><br>
                    <span>{row['icono_genero']} Predominancia: <b>{row['predominancia_genero']}</b></span><br>
                    <span>👩 %Mujeres: <b>{row['pct_mujeres']:.1f}%</b></span><br>
                    <span>👨 %Hombres: <b>{100-row['pct_mujeres']:.1f}%</b></span>
                </div>
                """,
                axis=1
            )
            fig_genero = px.choropleth_mapbox(
                gdf_genero,
                geojson=gdf_genero.geometry.__geo_interface__,
                locations=gdf_genero.index,
                color='pct_mujeres',
                color_continuous_scale="Purples",
                range_color=[48, 52],
                mapbox_style="open-street-map",
                zoom=ZOOM_INICIAL,
                center={"lat": CENTRO_MAPA["lat"], "lon": CENTRO_MAPA["lon"]},
                opacity=0.65,
                custom_data=['hover_text']
            )
            fig_genero.update_traces(hovertemplate='%{customdata[0]}<extra></extra>')
            fig_genero.update_layout(
                title="Predominancia de Género (% Mujeres en Padrón)",
                height=600,
                font_color='white',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_genero, use_container_width=True)
    
    elif vista_mapa == "Sentimiento Social (ISC)":
        gdf_sentimiento = get_mapa_sentimiento()
        if not gdf_sentimiento.empty and 'geometry' in gdf_sentimiento.columns:
            # Popup con nivel de satisfacción
            gdf_sentimiento['hover_text'] = gdf_sentimiento.apply(lambda row:
                f"""
                <div style='font-family: "Inter", sans-serif; padding: 8px;'>
                    <b style='font-size: 16px;'>😊 Sección {row['seccion']}</b><br>
                    <span>📊 ISC: <b style='color: {"#ff4b4b" if row["indice_satisfaccion_ciudadana"]<40 else "#ff9800" if row["indice_satisfaccion_ciudadana"]<60 else "#4caf50"};'>{row['indice_satisfaccion_ciudadana']:.1f}</b></span><br>
                    <span>🏷️ Nivel: <b>{row['nivel_satisfaccion']}</b></span><br>
                    <span>🗣️ Opiniones: <b>{row['total_opiniones']}</b></span>
                </div>
                """,
                axis=1
            )
            fig_sentimiento = px.choropleth_mapbox(
                gdf_sentimiento,
                geojson=gdf_sentimiento.geometry.__geo_interface__,
                locations=gdf_sentimiento.index,
                color='indice_satisfaccion_ciudadana',
                color_continuous_scale=px.colors.diverging.RdYlGn,
                range_color=[0, 100],
                mapbox_style="open-street-map",
                zoom=ZOOM_INICIAL,
                center={"lat": CENTRO_MAPA["lat"], "lon": CENTRO_MAPA["lon"]},
                opacity=0.65,
                custom_data=['hover_text']
            )
            fig_sentimiento.update_traces(hovertemplate='%{customdata[0]}<extra></extra>')
            fig_sentimiento.update_layout(
                title="Índice de Satisfacción Ciudadana (ISC) - Escala 0-100",
                height=600,
                margin={"r":0,"t":40,"l":0,"b":0},
                font_color='white',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_sentimiento, use_container_width=True)
            
            # Estadísticas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                excelente = len(gdf_sentimiento[gdf_sentimiento['nivel_satisfaccion'] == 'Excelente'])
                st.metric("✅ Excelente (75-100)", excelente)
            with col2:
                bueno = len(gdf_sentimiento[gdf_sentimiento['nivel_satisfaccion'] == 'Bueno'])
                st.metric("👍 Bueno (60-74)", bueno)
            with col3:
                regular = len(gdf_sentimiento[gdf_sentimiento['nivel_satisfaccion'] == 'Regular'])
                st.metric("⚠️ Regular (40-59)", regular)
            with col4:
                deficiente = len(gdf_sentimiento[gdf_sentimiento['nivel_satisfaccion'] == 'Deficiente'])
                st.metric("🚨 Deficiente (<40)", deficiente, help="Requiere intervención urgente")
            
            if deficiente > 0:
                secciones_criticas = gdf_sentimiento[gdf_sentimiento['nivel_satisfaccion'] == 'Deficiente']['seccion'].tolist()
                st.markdown(f"""
                <div class="alert-box">
                    <strong>🚨 ALERTA DE RIESGO ELECTORAL:</strong> {deficiente} secciones con ISC Deficiente (<40). 
                    Requieren operación política de cicatrización URGENTE.<br>
                    <strong>Secciones:</strong> {', '.join(map(str, secciones_criticas[:5]))}{'...' if len(secciones_criticas)>5 else ''}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="info-box">
                <strong>📊 SOBRE EL ISC:</strong> El Índice de Satisfacción Ciudadana (0-100) se calcula a partir de:
                <ul>
                    <li>Encuestas casa por casa (peso 1.0)</li>
                    <li>Foros ciudadanos (peso 0.85)</li>
                    <li>Redes sociales (peso 0.60)</li>
                    <li>Denuncias 911 y solicitudes oficiales (peso 0.90-0.95)</li>
                </ul>
                <strong>Zonas rojas = Baja satisfacción</strong> → Priorizar en estrategia política.
            </div>
            """, unsafe_allow_html=True)
    
    # ========================================
    # ANÁLISIS DE CORRELACIÓN
    # ========================================
    st.header("📊 Análisis de Correlación Social-Electoral")
    df_correlacion = get_correlacion_participacion_carencias(anio_seleccionado)
    if not df_correlacion.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.scatter(
                df_correlacion,
                x='participacion_pct',
                y='pct_sin_agua_drenaje',
                size='pobtot',
                hover_name='seccion',
                color='pct_sin_agua_drenaje',
                color_continuous_scale='Reds',
                title="Participación vs Carencia Agua/Drenaje"
            )
            fig1.update_layout(height=450, font_color='white', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.scatter(
                df_correlacion,
                x='participacion_pct',
                y='grado_prom_escolar',
                size='pobtot',
                hover_name='seccion',
                color='grado_prom_escolar',
                color_continuous_scale='Blues',
                title="Participación vs Educación"
            )
            fig2.update_layout(height=450, font_color='white', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig2, use_container_width=True)
    
    # ========================================
    # ANÁLISIS FODA
    # ========================================
    st.header("🎯 Análisis FODA")
    col_f, col_o = st.columns(2)
    with col_f:
        st.subheader("💪 FORTALEZAS")
        st.markdown("""
        - Ubicación geoestratégica (turística)
        - Participación electoral sólida (56.8%)
        - Base electoral MORENA consolidada (36.6%)
        - Sistema GIS completo
        """)
        st.subheader("⚠️ DEBILIDADES")
        st.markdown("""
        - Desabasto de agua crítico
        - Infraestructura deficiente
        - Nivel educativo bajo
        - Desigualdad económica (Gini 0.417)
        """)
    with col_o:
        st.subheader("🌟 OPORTUNIDADES")
        st.markdown("""
        - FAISMUN 2025: $203.7M
        - Gobierno 4T alineado
        - Mandato ciudadano claro
        - Digitalización gubernamental
        """)
        st.subheader("🚨 AMENAZAS")
        st.markdown("""
        - Inseguridad regional
        - Migración económica
        - Deterioro de servicios
        - Fragmentación electoral
        """)

# ============================================
# TAB 2: PRIORIDADES DE INVERSIÓN
# ============================================
with tab2:
    st.header(f"💰 Prioridades de Inversión FAISMUN 2025 - ${PRESUPUESTO_FAISMUN_2025:,.0f}")
    df_rezago_top = get_seccion_rezago_top10()
    if df_rezago_top is not None and not df_rezago_top.empty:
        total_pob = df_rezago_top['pobtot'].sum()
        df_rezago_top['presupuesto_asignado'] = (df_rezago_top['pobtot'] / total_pob * PRESUPUESTO_FAISMUN_2025).round(0).astype(int)
        df_rezago_top['justificacion'] = df_rezago_top.apply(lambda row:
            f"Atender a {row['pobtot']:,} habitantes con {row['pct_sin_servicios']:.1f}% sin servicios básicos. " +
            f"Prioridad {'ALTA' if row['pct_sin_servicios'] > 30 else 'MEDIA'}",
            axis=1
        )
        st.markdown("""
        <div class="info-box">
            <strong>📋 CRITERIOS DE ASIGNACIÓN:</strong>
            <ul>
                <li>Principio de equidad: Mayor presupuesto a secciones con mayor población y rezago</li>
                <li>Cumplimiento PbR: Resultados medibles (reducción de carencias)</li>
                <li>Normativa ASE: Justificación técnica según LGCG</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        col_tabla, col_grafica = st.columns([2, 1])
        with col_tabla:
            st.subheader("🎯 Top 10 Secciones Prioritarias")
            df_display = df_rezago_top[['seccion', 'pobtot', 'pct_sin_servicios', 'presupuesto_asignado', 'justificacion']].copy()
            df_display.columns = ['Sección', 'Población', '% Sin Servicios', 'Presupuesto', 'Justificación Técnica']
            df_display['Presupuesto'] = df_display['Presupuesto'].apply(lambda x: f"${x:,.0f}")
            df_display['% Sin Servicios'] = df_display['% Sin Servicios'].apply(lambda x: f"{x:.1f}%")
            st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)
        with col_grafica:
            st.subheader("📊 Distribución")
            fig_pres = go.Figure(data=[go.Pie(
                labels=df_rezago_top['seccion'].astype(str),
                values=df_rezago_top['presupuesto_asignado'],
                hole=.4,
                marker=dict(colors=px.colors.sequential.Reds_r)
            )])
            fig_pres.update_layout(height=400, font_color='white', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pres, use_container_width=True)
        st.subheader("📋 Resumen Ejecutivo")
        total_beneficiarios = df_rezago_top['pobtot'].sum()
        promedio_rezago = df_rezago_top['pct_sin_servicios'].mean()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👥 Beneficiarios Directos", f"{total_beneficiarios:,}")
        with col2:
            st.metric("📉 Rezago Promedio", f"{promedio_rezago:.1f}%")
        with col3:
            st.metric("💵 Inversión Total", f"${PRESUPUESTO_FAISMUN_2025:,.0f}")

# ============================================
# TAB 3: ANÁLISIS DE GÉNERO
# ============================================
with tab3:
    st.header("👥 Análisis Demográfico y Género")
    df_genero = get_perfil_genero()
    df_estrategicas = get_secciones_estrategicas_20()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⚖️ Brecha de Género Municipal")
        if not df_genero.empty:
            total_mujeres = df_genero['lista_mujeres'].sum()
            total_hombres = df_genero['lista_hombres'].sum()
            total_padron = total_mujeres + total_hombres
            fig_genero = go.Figure(data=[
                go.Bar(name='Mujeres', x=['Padrón'], y=[total_mujeres], marker_color='#E91E63'),
                go.Bar(name='Hombres', x=['Padrón'], y=[total_hombres], marker_color='#2196F3')
            ])
            fig_genero.update_layout(
                title=f"Total: {total_padron:,}",
                barmode='group',
                height=300,
                font_color='white',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_genero, use_container_width=True)
            pct_mujeres = (total_mujeres / total_padron * 100)
            pct_hombres = (total_hombres / total_padron * 100)
            st.metric(
                "🎯 Predominancia General",
                "Femenino" if total_mujeres > total_hombres else "Masculino",
                f"M: {pct_mujeres:.1f}% | H: {pct_hombres:.1f}%"
            )
        st.subheader("📊 Predominancia por Sección")
        df_genero_display = df_genero[['seccion', 'lista_nominal_oficial', 'pct_mujeres', 'pct_hombres', 'predominancia_genero']].copy()
        df_genero_display.columns = ['Sección', 'Lista Nominal', '% Mujeres', '% Hombres', 'Predominancia']
        df_genero_display['% Mujeres'] = df_genero_display['% Mujeres'].apply(lambda x: f"{x:.1f}%")
        df_genero_display['% Hombres'] = df_genero_display['% Hombres'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(df_genero_display, use_container_width=True, hide_index=True, height=400)
    with col2:
        st.subheader("🎯 Top 20 Secciones Estratégicas")
        if df_estrategicas is not None and not df_estrategicas.empty:
            peso_acumulado = df_estrategicas['pct_peso_electoral'].sum()
            st.metric("🎯 Concentración Electoral", f"{peso_acumulado:.1f}%", "en 20 secciones")
            st.markdown("""
            <div class="info-box">
                <strong>📊 ESTRATEGIA:</strong> Estas 20 secciones concentran el ~80% del peso electoral. 
                Enfocar recursos de campaña aquí maximiza el impacto.
            </div>
            """, unsafe_allow_html=True)
            df_est_display = df_estrategicas[['seccion', 'lista_nominal_oficial', 'pct_peso_electoral']].copy()
            df_est_display.columns = ['Sección', 'Lista Nominal', '% Peso']
            df_est_display['% Peso'] = df_est_display['% Peso'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(df_est_display, use_container_width=True, hide_index=True, height=400)

# ============================================
# TAB 4: RIESGO ELECTORAL
# ============================================
with tab4:
    st.header("🚨 Análisis de Riesgo Electoral - Operación Cicatrización")
    df_riesgo = get_riesgo_electoral()
    if df_riesgo is not None and not df_riesgo.empty:
        alto_riesgo = len(df_riesgo[df_riesgo['nivel_riesgo_electoral'] == 'ALTO RIESGO'])
        medio_riesgo = len(df_riesgo[df_riesgo['nivel_riesgo_electoral'] == 'RIESGO MEDIO'])
        bajo_riesgo = len(df_riesgo[df_riesgo['nivel_riesgo_electoral'] == 'BAJO RIESGO'])
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🚨 ALTO RIESGO", alto_riesgo, delta="Intervención URGENTE", delta_color="inverse")
        with col2:
            st.metric("⚠️ RIESGO MEDIO", medio_riesgo, delta="Reforzar operación")
        with col3:
            st.metric("✅ BAJO RIESGO", bajo_riesgo, delta="Mantener presencia")
        st.subheader("🎯 Secciones Críticas - Plan de Acción")
        nivel_filtro = st.selectbox("Filtrar por nivel de riesgo", ["Todos", "ALTO RIESGO", "RIESGO MEDIO", "BAJO RIESGO"])
        if nivel_filtro != "Todos":
            df_mostrar = df_riesgo[df_riesgo['nivel_riesgo_electoral'] == nivel_filtro]
        else:
            df_mostrar = df_riesgo
        df_display = df_mostrar[[
            'seccion', 'ganador_2024', 'pct_votos', 
            'indice_satisfaccion', 'num_opiniones',
            'nivel_riesgo_electoral', 'accion_recomendada'
        ]].copy()
        df_display.columns = [
            'Sección', 'Ganador 2024', '% Votos', 
            'ISC', 'Opiniones',
            'Nivel Riesgo', 'Acción Recomendada'
        ]
        df_display['% Votos'] = df_display['% Votos'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/D")
        df_display['ISC'] = df_display['ISC'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "50")
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)
        st.subheader("📋 Plan de Cicatrización Política")
        if alto_riesgo > 0:
            secciones_urgentes = df_riesgo[df_riesgo['nivel_riesgo_electoral'] == 'ALTO RIESGO']
            st.markdown(f"""
            <div class="alert-box">
                <strong>🚨 PROTOCOLO DE INTERVENCIÓN URGENTE</strong><br><br>
                <strong>{alto_riesgo} secciones requieren cicatrización inmediata:</strong><br>
                {', '.join(map(str, secciones_urgentes['seccion'].tolist()))}
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            ### 🎯 Estrategia de Intervención (48-72 hrs)
            **FASE 1: Diagnóstico Inmediato**
            - 🔍 Levantamiento de campo casa por casa
            - 📊 Identificar problema principal (agua, seguridad, basura)
            - 👥 Mapear líderes locales y grupos organizados
            **FASE 2: Respuesta Rápida**
            - 🚧 Acción gubernamental visible (obra menor, limpieza, bacheo)
            - 📢 Comunicación directa con vecinos
            - 🤝 Reunión con líderes de sección
            **FASE 3: Seguimiento**
            - 📅 Cronograma de solución a problemas mayores
            - 📱 Canal directo de atención (WhatsApp/teléfono)
            - 📈 Re-medición de satisfacción en 15 días
            """)
        st.subheader("📊 Satisfacción por Tipo de Servicio")
        df_servicios = get_satisfaccion_por_servicio_agregado()
        if df_servicios is not None and not df_servicios.empty:
            fig_servicios = px.bar(
                df_servicios,
                x='calificacion_promedio',
                y='nombre_categoria',
                orientation='h',
                color='nivel',
                color_discrete_map={
                    'Excelente': '#1a9850',
                    'Bueno': '#91cf60',
                    'Regular': '#fee08b',
                    'Deficiente': '#d73027'
                },
                text='calificacion_promedio',
                title="Calificación Promedio por Servicio (1-5)"
            )
            fig_servicios.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig_servicios.update_layout(
                height=500,
                showlegend=True,
                font_color='white',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_servicios, use_container_width=True)

# ============================================
# TAB 5: REPORTES Y EXPORTACIÓN
# ============================================
with tab5:
    st.header("📥 Exportación de Datos y Reportes")
    st.info("📌 Módulo en desarrollo. Próximamente:")
    st.markdown("""
    - **📊 Reporte Excel Ejecutivo**: KPIs + tablas dinámicas
    - **🗺️ GeoJSON de Secciones**: Para integración con otros sistemas GIS
    - **📄 PDF Análisis Completo**: Documento para presentación institucional
    - **📱 Dashboard Móvil**: Versión optimizada para tablets en campo
    """)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📊 Generar Excel", use_container_width=True):
            st.warning("Función próximamente")
    with col2:
        if st.button("🗺️ Exportar GeoJSON", use_container_width=True):
            st.warning("Función próximamente")
    with col3:
        if st.button("📄 Crear PDF", use_container_width=True):
            st.warning("Función próximamente")

# ============================================
# FOOTER (sin línea divisoria)
# ============================================
st.caption("Dashboard Electoral Taxco 2024 | PostgreSQL + PostGIS | Datos: INE, INEGI, IEPAC")

# -*- coding: utf-8 -*-
# modulos_nuevos.py — Centro de Comando
# Ruta: C:\Users\campe\Desktop\taxco\dashboard\modulos_nuevos.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

BACKEND_URL = os.getenv("BACKEND_URL", "https://taxco-backend-api.onrender.com")

def _sql(query, params=None):
    try:
        from queries import sql
        return sql(query, params)
    except Exception:
        return pd.DataFrame()

ZONAS_GUERRA = [2178,2181,2186,2191,2194,2197,2200,2203,2205,2207,2208,2185,2193,2196,2199,2202]

def render_crm_brigadistas():
    st.markdown("## 👥 CRM de Brigadistas — Centro de Movilización")
    st.caption("Seguimiento en tiempo real de visitas domiciliarias y captación de simpatizantes.")
    df_simp = _sql("""
        SELECT DATE(sim.fecha_registro) as fecha,
               COUNT(*) as captados,
               COUNT(CASE WHEN sim.es_mujer=TRUE THEN 1 END) as mujeres,
               COUNT(CASE WHEN sim.es_mujer=FALSE THEN 1 END) as hombres
        FROM simpatizantes sim
        JOIN seccion s ON s.pk_seccion=sim.pk_seccion
        WHERE s.id_municipio=56 AND sim.fecha_registro>=NOW()-INTERVAL '30 days'
        GROUP BY DATE(sim.fecha_registro) ORDER BY fecha
    """)
    df_sec = _sql("""
        SELECT s.seccion, COUNT(sim.pk_simpatizante) as visitas, pi.lista_nominal_oficial
        FROM seccion s
        LEFT JOIN simpatizantes sim ON sim.pk_seccion=s.pk_seccion
        LEFT JOIN padron_ine pi ON pi.pk_seccion=s.pk_seccion AND pi.anio_padron=2024
        WHERE s.id_municipio=56 GROUP BY s.seccion, pi.lista_nominal_oficial
    """)
    total = int(df_simp['captados'].sum()) if not df_simp.empty else 0
    muj   = int(df_simp['mujeres'].sum())  if not df_simp.empty else 0
    sec_a = len(df_sec[df_sec['visitas']>0]) if not df_sec.empty else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🤝 Simpatizantes",f"{total:,}")
    c2.metric("👩 Mujeres",f"{muj:,}")
    c3.metric("👨 Hombres",f"{total-muj:,}")
    c4.metric("📍 Secciones activas",f"{sec_a}/89")
    st.divider()
    col1, col2 = st.columns([1.3,1])
    with col1:
        st.markdown("### 📊 Captación últimos 30 días")
        if not df_simp.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_simp['fecha'],y=df_simp['mujeres'],name='Mujeres',marker_color='#e94560'))
            fig.add_trace(go.Bar(x=df_simp['fecha'],y=df_simp['hombres'],name='Hombres',marker_color='#1a4a2e'))
            fig.update_layout(barmode='stack',height=280,margin=dict(t=10,b=10),
                               plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',
                               legend=dict(orientation='h',y=-0.25))
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.info("Sin datos de captación aún.")
    with col2:
        st.markdown("### 🚨 Zona de Guerra")
        if not df_sec.empty:
            df_g = df_sec[df_sec['seccion'].isin(ZONAS_GUERRA)][['seccion','visitas','lista_nominal_oficial']].copy()
            df_g['lista_nominal_oficial'] = df_g['lista_nominal_oficial'].fillna(1)
            df_g['cobertura'] = (df_g['visitas']/df_g['lista_nominal_oficial']*100).round(1)
            df_g['estado'] = df_g['cobertura'].apply(lambda x:'🔴 Urgente' if x<2 else('🟡 En proceso' if x<10 else '🟢 Cubierta'))
            df_g.columns=['Sección','Visitas','Padrón','Cobertura %','Estado']
            st.dataframe(df_g[['Sección','Visitas','Cobertura %','Estado']],use_container_width=True,height=260)
    st.divider()
    st.markdown("### 🗺️ Secciones prioritarias HOY")
    if not df_sec.empty:
        urgentes = df_sec[df_sec['seccion'].isin(ZONAS_GUERRA)&(df_sec['visitas']==0)].head(3)
        if not urgentes.empty:
            cols = st.columns(len(urgentes))
            for i,(_,r) in enumerate(urgentes.iterrows()):
                p = int(r['lista_nominal_oficial']) if r['lista_nominal_oficial'] else 0
                cols[i].error(f"**🚨 PRIORIDAD {i+1}**\n\n**Sección {int(r['seccion'])}**\n\nSin visitas\nPadrón: {p:,}\n\n👉 Brigada HOY")
        else:
            st.success("✅ Todas las secciones de guerra tienen al menos una visita.")

def render_sentimiento_social():
    st.markdown("## 😤 Monitor de Sentimiento Social")
    st.caption("Alerta automática cuando el sentimiento negativo sube +20% en una hora.")
    df = _sql("""
        SELECT cs.nombre_categoria,
               ROUND(AVG(ss.calificacion),2) AS cal,
               COUNT(*) AS n,
               ROUND(AVG(CASE WHEN ss.sentimiento_polaridad<0 THEN 1 ELSE 0 END)*100,1) AS neg,
               ROUND(AVG(CASE WHEN ss.sentimiento_polaridad>0 THEN 1 ELSE 0 END)*100,1) AS pos
        FROM sentimiento_social ss
        JOIN categoria_servicio cs ON cs.id_categoria=ss.id_categoria
        GROUP BY cs.nombre_categoria ORDER BY neg DESC
    """)
    df_al = _sql("""
        WITH a AS (
            SELECT cs.nombre_categoria,
                   ROUND(AVG(CASE WHEN ss.sentimiento_polaridad<0 THEN 1 ELSE 0 END)*100,1) AS na, COUNT(*) AS n
            FROM sentimiento_social ss JOIN categoria_servicio cs ON cs.id_categoria=ss.id_categoria
            WHERE ss.fecha_registro>=NOW()-INTERVAL '1 hour' GROUP BY cs.nombre_categoria),
        b AS (
            SELECT cs.nombre_categoria,
                   ROUND(AVG(CASE WHEN ss.sentimiento_polaridad<0 THEN 1 ELSE 0 END)*100,1) AS nb
            FROM sentimiento_social ss JOIN categoria_servicio cs ON cs.id_categoria=ss.id_categoria
            WHERE ss.fecha_registro BETWEEN NOW()-INTERVAL '2 hours' AND NOW()-INTERVAL '1 hour'
            GROUP BY cs.nombre_categoria)
        SELECT a.nombre_categoria, a.na, COALESCE(b.nb,0) AS nb, (a.na-COALESCE(b.nb,0)) AS inc
        FROM a LEFT JOIN b ON b.nombre_categoria=a.nombre_categoria WHERE (a.na-COALESCE(b.nb,0))>=20
    """)
    if not df_al.empty:
        for _,r in df_al.iterrows():
            st.error(f"🚨 **ALERTA ROJA — {r['nombre_categoria']}** | {r['na']}% (+{r['inc']:.0f}% en 1h)")
    else:
        st.success("✅ Sin alertas — Sentimiento estable")
    st.divider()
    if not df.empty:
        c1,c2,c3 = st.columns(3)
        c1.metric("⭐ Calificación prom.",f"{df['cal'].mean():.1f}/5")
        c2.metric("💬 Opiniones",f"{int(df['n'].sum()):,}")
        c3.metric("😤 % Negativo prom.",f"{df['neg'].mean():.1f}%")
        st.divider()
        col1,col2 = st.columns(2)
        with col1:
            st.markdown("### 📊 Calificación por servicio")
            fig=px.bar(df.sort_values('cal'),x='cal',y='nombre_categoria',orientation='h',
                       color='cal',color_continuous_scale=['#e63946','#ffd166','#06d6a0'],range_color=[1,5])
            fig.add_vline(x=3,line_dash='dash',line_color='gray',annotation_text='Neutral')
            fig.update_layout(height=320,margin=dict(t=10,b=10),plot_bgcolor='rgba(0,0,0,0)',
                               paper_bgcolor='rgba(0,0,0,0)',coloraxis_showscale=False)
            st.plotly_chart(fig,use_container_width=True)
        with col2:
            st.markdown("### 🌡️ Positivo vs Negativo")
            fig2=px.scatter(df,x='pos',y='neg',size='n',hover_name='nombre_categoria',
                            color='neg',color_continuous_scale=['#06d6a0','#ffd166','#e63946'],
                            labels={'pos':'% Positivo','neg':'% Negativo'})
            fig2.add_hline(y=30,line_dash='dash',line_color='red',annotation_text='Umbral 30%')
            fig2.update_layout(height=320,margin=dict(t=10,b=10),plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',coloraxis_showscale=False)
            st.plotly_chart(fig2,use_container_width=True)
        df_s=df[['nombre_categoria','cal','n','neg','pos']].copy()
        df_s.columns=['Servicio','Calificación','Opiniones','% Negativo','% Positivo']
        def cn(v): return 'background-color:#f8d7da;color:#721c24' if v>=50 else ('background-color:#fff3cd;color:#856404' if v>=30 else 'background-color:#d4edda;color:#155724')
        st.dataframe(df_s.style.applymap(cn,subset=['% Negativo']),use_container_width=True)
    else:
        st.info("Sin datos de sentimiento aún.")

HUMANO=[
    {"s":1,"d":"Lun","t":"Tradición","i":"Video en taller de platería — 'Estas manos construyen Guerrero'","f":"Reels 60s","h":"#PlateríaTaxco"},
    {"s":1,"d":"Mié","t":"Comunidad","i":"Desayuno en mercado con mujeres comerciantes","f":"Historia","h":"#TaxcoUnido"},
    {"s":1,"d":"Vie","t":"Cultura","i":"Procesión Semana Santa — presencia en tradición religiosa","f":"Live 15min","h":"#TaxcoTradición"},
    {"s":2,"d":"Mar","t":"Tradición","i":"Artesanos de máscara de laca — 'El arte que no puede perderse'","f":"Reels 30s","h":"#ArtesaníaGuerrero"},
    {"s":2,"d":"Jue","t":"Comunidad","i":"Recorrido barrio Bermeja — escuchar vecinos zona norte","f":"Vlog 3min","h":"#EscuchamosTaxco"},
    {"s":2,"d":"Sáb","t":"Familia","i":"Futbol con jóvenes sección 2208 — zona crítica","f":"Historia","h":"#JuventudTaxco"},
    {"s":3,"d":"Lun","t":"Gastronomía","i":"Pozole rojo con abuela del centro — receta familiar","f":"Reels 45s","h":"#SaborDeTaxco"},
    {"s":3,"d":"Mié","t":"Educación","i":"Visita preparatoria — 'Qué necesitas para quedarte en Taxco'","f":"Entrevista","h":"#FuturoGuerrero"},
    {"s":3,"d":"Vie","t":"Comunidad","i":"Limpieza de barranca con vecinos zona rezago","f":"Video","h":"#TaxcoLimpio"},
    {"s":4,"d":"Mar","t":"Tradición","i":"Festival de la Plata — premiación artesanos","f":"Story+post","h":"#FestivalPlata"},
    {"s":4,"d":"Jue","t":"Salud","i":"Jornada de salud gratuita sección 2191","f":"Cobertura","h":"#SaludParaTodos"},
    {"s":4,"d":"Sáb","t":"Familia","i":"Mañana deportiva adultos mayores sección 2186","f":"Historia","h":"#TaxcoActivo"},
    {"s":5,"d":"Lun","t":"Cultura","i":"Noche de Plata — recorrido nocturno histórico","f":"Live 20min","h":"#TaxcoMágico"},
    {"s":5,"d":"Mié","t":"Mujer","i":"Mesa redonda mujeres emprendedoras — 'Tu negocio, tu poder'","f":"Transmisión","h":"#MujerGuerrero"},
    {"s":5,"d":"Vie","t":"Comunidad","i":"Brigada agua potable colonia Pedregal","f":"Antes/después","h":"#AguaParaTaxco"},
    {"s":6,"d":"Mar","t":"Tradición","i":"Maestro platero 40 años — legado e identidad","f":"Mini doc","h":"#HerederosDeTaxco"},
    {"s":6,"d":"Jue","t":"Juventud","i":"Hackathon — 'Diseña la app que necesita Taxco'","f":"Cobertura","h":"#InovaciónTaxco"},
    {"s":6,"d":"Sáb","t":"Familia","i":"Kermés barrial sección 2200 sin agenda política visible","f":"Historia","h":"#ViveTaxco"},
    {"s":7,"d":"Lun","t":"Comunidad","i":"Siembra árboles zona escolar sección 2194","f":"Acción","h":"#TaxcoVerde"},
    {"s":7,"d":"Vie","t":"Cultura","i":"Presentación libro local — escritores guerrerenses","f":"Foto+quote","h":"#CulturaTaxco"},
]
GUIONES=[
    {"n":1,"t":"El Fondo de Primer Empleo","tg":"Desempleados 20-35","g":"'Tres de cada diez jóvenes de Taxco no tienen empleo formal. El Fondo de Primer Empleo da 6 meses de salario a empresas que contraten jóvenes locales. Sin burocracia.'","c":"Regístrate"},
    {"n":2,"t":"Agua — FAISMUN 2025","tg":"Zonas sin agua","g":"'Estos puntos rojos son casas sin agua. Con $203M del FAISMUN hay dinero. Lo que falta es voluntad. Yo ya sé a qué colonias va primero.'","c":"Ver mapa"},
    {"n":3,"t":"El Algoritmo del Voto","tg":"Indecisos zona guerra","g":"'La sección 2208 se perdió por 47 votos. Esta pantalla muestra cuántos electores aún no deciden. ¿Tu voto puede mover el resultado?'","c":"Ver tu sección"},
    {"n":4,"t":"Rescate Educativo","tg":"Estudiantes apáticos","g":"'14% de estudiantes de Taxco no van a votar. Pero el presupuesto de tu escuela depende de quién gobierne. Tu voto no es para mí. Es para ti.'","c":"Comparte"},
    {"n":5,"t":"Mujer Segura","tg":"Mujeres zona rural","g":"'Caminar de noche en Taxco no debería dar miedo. El protocolo de alumbrado cuesta menos que un espectacular. Yo sé cuáles 12 secciones van primero.'","c":"Ver protocolo"},
    {"n":6,"t":"Drenaje — La Promesa","tg":"Colonias sin drenaje","g":"'Esta colonia lleva 8 años esperando drenaje. Si no está terminado en 18 meses me presentaré en tu puerta a explicarte por qué.'","c":"Ver compromiso"},
    {"n":7,"t":"El CRM del Ciudadano","tg":"Tech-savvy","g":"'Tenemos un sistema que sabe cuántas casas en tu sección no tienen agua. No es magia. Son datos del gobierno federal. La diferencia es que los usamos para gobernar.'","c":"Ver dashboard"},
    {"n":8,"t":"Primer Empleo — Caso Real","tg":"Familias","g":"'[Joven]: Llevo dos años buscando trabajo en Taxco. El Fondo de Primer Empleo cambia eso. Ya me inscribí. ¿Y tú?'","c":"Inscríbete"},
    {"n":9,"t":"Platería — Motor Económico","tg":"Artesanos","g":"'La plata genera 60% del empleo de Taxco. En 4 años, 120 talleres cerraron. Tengo el convenio FONART firmado.'","c":"Ver convenio"},
    {"n":10,"t":"Activación Final","tg":"Apáticos","g":"'Taxco se decidió por 200 votos. 200 familias pudieron cambiar el resultado. Tú eres una de esas familias.'","c":"Comparte y activa"},
]

def render_contenido_7030():
    st.markdown("## 📅 Calendario de Contenido — Modelo 70/30")
    tab_h,tab_t = st.tabs(["🤝 70% Contenido Humano","🎯 30% Guiones 60s"])
    ICONS={"Tradición":"🏺","Comunidad":"🤝","Cultura":"🎭","Familia":"👨‍👩‍👧","Gastronomía":"🍲","Educación":"📚","Mujer":"👩","Salud":"🏥","Juventud":"🎮"}
    with tab_h:
        st.info("Objetivo: Conectar emocionalmente antes de hablar de gestión.")
        sel=st.selectbox("Semana:",["Todas"]+[f"Semana {i}" for i in range(1,8)])
        items=HUMANO if sel=="Todas" else [x for x in HUMANO if x['s']==int(sel.split()[-1])]
        for r in items:
            ic=ICONS.get(r['t'],"📸")
            st.markdown(f"**{ic} Sem {r['s']} — {r['d']}** | `{r['f']}` | {r['h']}")
            st.markdown(f"&nbsp;&nbsp;{r['i']}")
            st.divider()
    with tab_t:
        st.warning("Objetivo: Activar al votante apático con datos reales.")
        for g in GUIONES:
            with st.expander(f"📹 #{g['n']}: {g['t']} — {g['tg']}"):
                st.info(f"**Guión:** {g['g']}")
                st.success(f"**CTA:** {g['c']}")
                st.code(g['g'],language=None)

PROTOCOLO=[
    {"p":1,"t":"Documentar el ataque","pl":"2 horas","r":"Equipo digital","a":["Captura con fecha/hora","Guardar URL original","Registrar cuenta atacante","Anotar plataforma"]},
    {"p":2,"t":"Clasificar la violencia","pl":"3 horas","r":"Asesora jurídica","a":["Determinar si es VPMRG","Evaluar amenazas físicas","Verificar si es deepfake","Revisar Caso Irimbo"]},
    {"p":3,"t":"Notificar autoridades","pl":"6 horas","r":"Coord. jurídica","a":["Denuncia ante INE-UTCE","Queja ante TEPJF","Reporte a plataforma digital","Notificar a Fiscalía si hay amenaza"]},
    {"p":4,"t":"Respuesta pública","pl":"8 horas","r":"Comunicación","a":["Comunicado con evidencias","Responder narrativa no al agresor","Activar red de mujeres aliadas","Solicitar pronunciamiento civil"]},
    {"p":5,"t":"Seguimiento","pl":"72 horas","r":"Equipo legal","a":["Monitoreo de menciones","Archivo con hash SHA-256","Preparar expediente impugnación","Documentar alcance e impacto"]},
]

def render_blindaje_genero():
    st.markdown("## 🛡️ Blindaje de Género — Protocolo Legal")
    st.caption("Basado en Caso Irimbo (TEPJF-SUP-JDC-1146/2020).")
    tab_p,tab_r,tab_l=st.tabs(["📋 Protocolo 72h","📝 Registrar incidente","⚖️ Marco legal"])
    with tab_p:
        st.error("**CASO IRIMBO:** Documentar correctamente puede definir el resultado de una impugnación.")
        for item in PROTOCOLO:
            with st.expander(f"⏰ PASO {item['p']}: {item['t']} — {item['pl']} | {item['r']}"):
                for a in item['a']: st.markdown(f"☐ {a}")
        st.markdown("### 📱 Contactos")
        df_c=pd.DataFrame([["INE-UTCE","800 433 2000","Ataque electoral"],["TEPJF","55 5134 1100","Impugnación"],["Fiscalía GRO","800 890 3900","Amenaza física"],["INMUJERES","800 900 4100","Violencia género"]],columns=["Institución","Contacto","Cuándo"])
        st.dataframe(df_c,use_container_width=True,hide_index=True)
    with tab_r:
        with st.form("f_incidente"):
            c1,c2=st.columns(2)
            fecha=c1.date_input("Fecha",value=datetime.today())
            tipo=c2.selectbox("Tipo",["Fake news","Amenaza","Deepfake","Acoso en redes","Intimidación","Otro"])
            plat=st.selectbox("Plataforma",["Facebook","Twitter/X","TikTok","Instagram","WhatsApp","Medios","Presencial"])
            desc=st.text_area("Descripción *",height=100)
            url=st.text_input("URL evidencia")
            agr=st.text_input("Agresor")
            pri=st.select_slider("Prioridad",["🟢 Baja","🟡 Media","🔴 Alta","🚨 Crítica"])
            if st.form_submit_button("🔐 Registrar"):
                if not desc: st.error("La descripción es obligatoria.")
                else:
                    import hashlib
                    h=hashlib.sha256(f"{fecha}{tipo}{desc}{url}".encode()).hexdigest()
                    _sql("INSERT INTO incidente_genero (fecha_incidente,tipo_violencia,plataforma,descripcion,url_evidencia,agresor,prioridad,hash_evidencia,id_municipio) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,56)",(str(fecha),tipo,plat,desc,url,agr,pri,h))
                    st.success(f"✅ Hash SHA-256: `{h[:32]}...`")
        df_i=_sql("SELECT fecha_incidente,tipo_violencia,plataforma,prioridad FROM incidente_genero WHERE id_municipio=56 ORDER BY fecha_incidente DESC LIMIT 20")
        if not df_i.empty: st.dataframe(df_i,use_container_width=True,hide_index=True)
        else: st.info("Sin incidentes registrados.")
    with tab_l:
        for t,d in [("📜 Caso Irimbo","Primer precedente VPMRG como causal de nulidad. Aplica en ataques coordinados y sistemáticos."),("📋 Ley AMVLV","Art. 20 Bis — Violencia política como toda acción que discrimine o impida el ejercicio del cargo."),("🏛️ Protocolo INE","Medidas cautelares en 24-48h. Requiere: evidencia, descripción del daño y nexo causal."),("⚡ Cautelares TEPJF","Sin esperar sentencia. Ordenan remoción de contenido y rectificaciones en las mismas plataformas.")]:
            with st.expander(t): st.write(d)

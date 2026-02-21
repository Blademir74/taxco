from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from datetime import datetime, timezone, timedelta
from database import engine
from models import DiagnosticoTerritorio
import base64, os, uvicorn, tempfile, uuid, logging, io
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, validator
from fastapi import Header
from typing import Optional, List
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Taxco")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"mensaje": "API Activa", "doc": "/docs"}

@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/secciones")
async def listar_secciones():
    query = """
    SELECT s.seccion,
        CASE
            WHEN r.pct_sin_agua > 10 THEN 'Zona con rezago de agua'
            WHEN r.pct_sin_servicios_basicos > 20 THEN 'Zona con rezago social'
            ELSE 'Zona sin rezago critico'
        END AS insight
    FROM seccion s
    LEFT JOIN vw_rezago_secciones r ON r.seccion = s.seccion
    WHERE s.id_municipio = 56
    ORDER BY s.seccion
    """
    df = pd.read_sql(query, engine)
    return df.to_dict(orient='records')

@app.post("/api/recoleccion", status_code=201)
async def guardar_diagnostico(diagnostico: DiagnosticoTerritorio):
    conn = engine.raw_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT pk_seccion FROM seccion WHERE seccion = %s AND id_municipio = 56",
            (diagnostico.seccion,)
        )
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Seccion no encontrada")
        pk_seccion = result[0]

        cursor.execute("SELECT id_fuente FROM fuente_sentimiento WHERE nombre_fuente = 'Encuesta de Campo'")
        row_fuente = cursor.fetchone()
        if not row_fuente:
            cursor.execute("INSERT INTO fuente_sentimiento (nombre_fuente) VALUES ('Encuesta de Campo') RETURNING id_fuente")
            row_fuente = cursor.fetchone()
        id_fuente = row_fuente[0]

        for servicio, calif in [("Agua", diagnostico.sentimiento.agua), ("Basura", diagnostico.sentimiento.basura), ("Seguridad", diagnostico.sentimiento.seguridad)]:
            cursor.execute("SELECT id_categoria FROM categoria_servicio WHERE nombre_categoria = %s", (servicio,))
            row_cat = cursor.fetchone()
            if not row_cat:
                cursor.execute("INSERT INTO categoria_servicio (nombre_categoria) VALUES (%s) RETURNING id_categoria", (servicio,))
                row_cat = cursor.fetchone()
            polaridad = 0.8 if calif >= 4 else (0.3 if calif >= 3 else -0.5)
            cursor.execute(
                "INSERT INTO sentimiento_social (pk_seccion, id_fuente, id_categoria, calificacion, sentimiento_polaridad, validado, fecha_registro) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (pk_seccion, id_fuente, row_cat[0], calif, polaridad, True, diagnostico.fecha_recoleccion)
            )

        cursor.execute(
            "INSERT INTO simpatizantes (pk_seccion, nombre, contacto, es_mujer, notas, fecha_registro) VALUES (%s,%s,%s,%s,%s,%s)",
            (pk_seccion, diagnostico.simpatizante.nombre, diagnostico.simpatizante.contacto,
             diagnostico.simpatizante.es_mujer, diagnostico.simpatizante.notas, diagnostico.fecha_recoleccion)
        )

        if diagnostico.evidencia and diagnostico.evidencia.foto_base64:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            evidencias_dir = os.path.join(base_dir, "evidencias")
            os.makedirs(evidencias_dir, exist_ok=True)
            filename = f"evidencia_{diagnostico.seccion}_{uuid.uuid4()}.jpg"
            filepath = os.path.join(evidencias_dir, filename)
            foto_data = diagnostico.evidencia.foto_base64
            if ',' in foto_data:
                foto_data = foto_data.split(',')[1]
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(foto_data))
            cursor.execute(
                "INSERT INTO evidencias (pk_seccion, ruta_archivo, comentario, fecha_registro) VALUES (%s,%s,%s,%s)",
                (pk_seccion, filepath, diagnostico.evidencia.comentario, diagnostico.fecha_recoleccion)
            )

        if diagnostico.latitud is not None and diagnostico.longitud is not None:
            cursor.execute(
                "INSERT INTO logs_gps (pk_seccion, latitud, longitud, fecha_registro) VALUES (%s,%s,%s,%s)",
                (pk_seccion, diagnostico.latitud, diagnostico.longitud, diagnostico.fecha_recoleccion)
            )

        conn.commit()
        return {"mensaje": "Diagnostico guardado correctamente"}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.exception("Error en guardar_diagnostico")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/exportar-excel")
async def exportar_excel():
    conn = engine.raw_connection()
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    output_path = tmp.name
    tmp.close()
    try:
        df_sent = pd.read_sql("SELECT s.seccion, cs.nombre_categoria, ss.calificacion, ss.sentimiento_polaridad, ss.fecha_registro FROM sentimiento_social ss JOIN seccion s ON ss.pk_seccion=s.pk_seccion JOIN categoria_servicio cs ON ss.id_categoria=cs.id_categoria ORDER BY ss.fecha_registro DESC", conn)
        df_simp = pd.read_sql("SELECT s.seccion, sim.nombre, sim.contacto, sim.es_mujer, sim.notas, sim.fecha_registro FROM simpatizantes sim JOIN seccion s ON sim.pk_seccion=s.pk_seccion ORDER BY sim.fecha_registro DESC", conn)
        df_evid = pd.read_sql("SELECT s.seccion, e.ruta_archivo, e.comentario, e.fecha_registro FROM evidencias e JOIN seccion s ON e.pk_seccion=s.pk_seccion ORDER BY e.fecha_registro DESC", conn)
        df_gps  = pd.read_sql("SELECT s.seccion, g.latitud, g.longitud, g.fecha_registro FROM logs_gps g JOIN seccion s ON g.pk_seccion=s.pk_seccion ORDER BY g.fecha_registro DESC", conn)
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df_sent.to_excel(writer, sheet_name="Sentimiento", index=False)
            df_simp.to_excel(writer, sheet_name="Simpatizantes", index=False)
            df_evid.to_excel(writer, sheet_name="Evidencias", index=False)
            df_gps.to_excel(writer, sheet_name="GPS", index=False)
        return FileResponse(path=output_path, filename="diagnosticos_campo.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            background=BackgroundTask(lambda: os.unlink(output_path)))
    except Exception as e:
        if os.path.exists(output_path):
            os.unlink(output_path)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

class InvitacionRequest(BaseModel):
    email: EmailStr
    tenant_id: str
    dias_validez: int = 7

class InvitacionResponse(BaseModel):
    token: str
    link: str

API_ADMIN_KEY = os.getenv("API_ADMIN_KEY", "cambia_esto_en_produccion")

@app.post("/api/admin/invitacion", response_model=InvitacionResponse)
async def crear_invitacion(inv: InvitacionRequest, admin_key: str = Header(...)):
    if admin_key != API_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="No autorizado")
    token = str(uuid.uuid4())
    expiracion = datetime.now(timezone.utc) + timedelta(days=inv.dias_validez)
    conn = engine.raw_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO invitaciones (token, email, tenant_id, fecha_expiracion) VALUES (%s,%s,%s,%s)",
                       (token, inv.email, inv.tenant_id, expiracion))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
    base_url = os.getenv("DASHBOARD_URL", "https://5mefjgvsuazhayejhm92vk.streamlit.app")
    return InvitacionResponse(token=token, link=f"{base_url}?invite={token}")

@app.get("/api/validate-invite/{token}")
async def validate_invite(token: str):
    conn = engine.raw_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT email, tenant_id FROM invitaciones WHERE token = %s", (token,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Token no encontrado")
        return {"email": row[0], "tenant_id": row[1]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

class AfiliadoIn(BaseModel):
    nombre_completo:    str
    telefono:           str
    edad:               Optional[int]       = None
    genero:             Optional[str]       = None
    municipio:          str
    colonia:            Optional[str]       = None
    seccion_electoral:  Optional[int]       = None
    tipo_participacion: Optional[str]       = "Simpatizante"
    temas_interes:      Optional[List[str]] = []
    como_se_entero:     Optional[str]       = None
    acepta_aviso:       bool
    acepta_contacto:    bool

    @validator('nombre_completo')
    def nombre_valido(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Nombre muy corto')
        return v.strip()

    @validator('telefono')
    def telefono_valido(cls, v):
        digits = ''.join(filter(str.isdigit, v))
        if len(digits) < 10:
            raise ValueError('Telefono invalido')
        return v.strip()

    @validator('acepta_aviso')
    def debe_aceptar(cls, v):
        if not v:
            raise ValueError('Debe aceptar aviso de privacidad')
        return v

@app.post("/api/afiliados")
async def registrar_afiliado(afiliado: AfiliadoIn, request: Request):
    conn = engine.raw_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT pk_afiliado FROM afiliados_dudu WHERE telefono = %s AND municipio = %s LIMIT 1",
                       (afiliado.telefono, afiliado.municipio))
        if cursor.fetchone():
            return {"ok": False, "mensaje": "Este numero ya esta registrado en tu municipio.", "duplicado": True}
        ip_cliente = request.client.host if request.client else "0.0.0.0"
        cursor.execute("""
            INSERT INTO afiliados_dudu
                (nombre_completo, telefono, edad, genero, municipio, colonia,
                 seccion_electoral, tipo_participacion, temas_interes, como_se_entero,
                 acepta_aviso, acepta_contacto, ip_registro)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (afiliado.nombre_completo, afiliado.telefono, afiliado.edad, afiliado.genero,
              afiliado.municipio, afiliado.colonia, afiliado.seccion_electoral,
              afiliado.tipo_participacion, afiliado.temas_interes, afiliado.como_se_entero,
              afiliado.acepta_aviso, afiliado.acepta_contacto, ip_cliente))
        conn.commit()
        return {"ok": True, "mensaje": "Gracias! Tu registro fue recibido correctamente."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/afiliados/kpis")
async def kpis_afiliados():
    conn = engine.raw_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(CASE WHEN genero = 'Mujer'  THEN 1 END) AS mujeres,
                COUNT(CASE WHEN genero = 'Hombre' THEN 1 END) AS hombres,
                COUNT(CASE WHEN municipio = 'Taxco de Alarcon' THEN 1 END) AS taxco,
                COUNT(CASE WHEN municipio = 'Pilcaya'  THEN 1 END) AS pilcaya,
                COUNT(CASE WHEN municipio = 'Tetipac'  THEN 1 END) AS tetipac,
                COUNT(CASE WHEN fecha_registro >= NOW() - INTERVAL '24 hours' THEN 1 END) AS ultimas_24h,
                COUNT(CASE WHEN fecha_registro >= NOW() - INTERVAL '7 days'  THEN 1 END) AS ultima_semana
            FROM afiliados_dudu WHERE activo = TRUE
        """)
        r = cursor.fetchone()
        return {"total": r[0], "mujeres": r[1], "hombres": r[2],
                "taxco": r[3], "pilcaya": r[4], "tetipac": r[5],
                "ultimas_24h": r[6], "ultima_semana": r[7]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/afiliados/exportar")
async def exportar_afiliados(request: Request):
    if request.headers.get("admin-key", "") != os.getenv("API_ADMIN_KEY", ""):
        raise HTTPException(status_code=403, detail="No autorizado")
    conn = engine.raw_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT nombre_completo, telefono, edad, genero, municipio, colonia,
                   seccion_electoral, tipo_participacion, como_se_entero, DATE(fecha_registro)
            FROM afiliados_dudu WHERE activo = TRUE ORDER BY fecha_registro DESC
        """)
        rows = cursor.fetchall()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Afiliados Dudu"
        headers = ["Nombre","Telefono","Edad","Genero","Municipio","Colonia","Seccion","Tipo","Como se entero","Fecha"]
        verde = PatternFill("solid", fgColor="2E7D32")
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = verde
            cell.alignment = Alignment(horizontal="center")
            ws.column_dimensions[chr(64+col)].width = 20
        for r_num, row in enumerate(rows, 2):
            for c_num, val in enumerate(row, 1):
                ws.cell(row=r_num, column=c_num, value=str(val) if val else "")
        ws.append([])
        ws.append([f"Total: {len(rows)} registros", "", "", "", "", "", "", "", "",
                   f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"])
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return StreamingResponse(output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=afiliados_dudu.xlsx"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
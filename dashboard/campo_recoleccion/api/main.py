from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from datetime import datetime
from database import engine
from models import DiagnosticoTerritorio
import base64
import os
import uvicorn
import tempfile
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse
import uuid
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from fastapi import Header, HTTPException

app = FastAPI()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)


# CORS para permitir el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringir al dominio del frontend
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/secciones")
async def listar_secciones():
    """Devuelve todas las secciones del municipio 56 con un mini‑insight de rezago."""
    query = """
    SELECT 
        s.seccion,
        CASE 
            WHEN r.pct_sin_agua > 10 THEN 'Zona con rezago de agua'
            WHEN r.pct_sin_servicios_basicos > 20 THEN 'Zona con rezago social'
            ELSE 'Zona sin rezago crítico'
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
    """
    Recibe el diagnóstico, valida la sección y guarda:
    - sentimiento_social (tres registros)
    - simpatizante
    - evidencia (si existe)
    - log de GPS (opcional)
    """
    conn = engine.raw_connection()
    cursor = conn.cursor()
    try:
        # 1. Validar existencia de la sección
        cursor.execute(
            "SELECT pk_seccion FROM seccion WHERE seccion = %s AND id_municipio = 56",
            (diagnostico.seccion,)
        )
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Sección no encontrada")
        pk_seccion = result[0]

        # 2. Asegurar que existe la fuente "Encuesta de Campo"
        cursor.execute("SELECT id_fuente FROM fuente_sentimiento WHERE nombre_fuente = 'Encuesta de Campo'")
        row_fuente = cursor.fetchone()
        if not row_fuente:
            cursor.execute("INSERT INTO fuente_sentimiento (nombre_fuente) VALUES ('Encuesta de Campo') RETURNING id_fuente")
            row_fuente = cursor.fetchone()
        id_fuente = row_fuente[0]

        # 3. Insertar los tres sentimientos (Agua, Basura, Seguridad)
        sentimientos = [
            ("Agua", diagnostico.sentimiento.agua),
            ("Basura", diagnostico.sentimiento.basura),
            ("Seguridad", diagnostico.sentimiento.seguridad),
        ]
        for servicio, calif in sentimientos:
            # Obtener o crear categoría
            cursor.execute("SELECT id_categoria FROM categoria_servicio WHERE nombre_categoria = %s", (servicio,))
            row_cat = cursor.fetchone()
            if not row_cat:
                cursor.execute("INSERT INTO categoria_servicio (nombre_categoria) VALUES (%s) RETURNING id_categoria", (servicio,))
                row_cat = cursor.fetchone()
            id_categoria = row_cat[0]

            # Calcular polaridad (simplificada para FastAPI)
            if calif >= 4:
                polaridad = 0.8
            elif calif >= 3:
                polaridad = 0.3
            else:
                polaridad = -0.5

            cursor.execute("""
                INSERT INTO sentimiento_social 
                (pk_seccion, id_fuente, id_categoria, calificacion, sentimiento_polaridad, validado, fecha_registro)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                pk_seccion, id_fuente, id_categoria, calif,
                polaridad, True, diagnostico.fecha_recoleccion
            ))

        # 4. Insertar simpatizante
        cursor.execute("""
            INSERT INTO simpatizantes (pk_seccion, nombre, contacto, es_mujer, notas, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            pk_seccion,
            diagnostico.simpatizante.nombre,
            diagnostico.simpatizante.contacto,
            diagnostico.simpatizante.es_mujer,
            diagnostico.simpatizante.notas,
            diagnostico.fecha_recoleccion
        ))

        # 5. Guardar evidencia fotográfica (si se proporcionó)
        if diagnostico.evidencia and diagnostico.evidencia.foto_base64:
            import uuid
            import os
            import base64

            # Crear carpeta 'evidencias' en el mismo directorio que main.py
            base_dir = os.path.dirname(os.path.abspath(__file__))
            evidencias_dir = os.path.join(base_dir, "evidencias")
            os.makedirs(evidencias_dir, exist_ok=True)

            # Generar nombre único
            filename = f"evidencia_{diagnostico.seccion}_{uuid.uuid4()}.jpg"
            filepath = os.path.join(evidencias_dir, filename)

            # Decodificar base64 (si viene como data URL, limpiar)
            foto_data = diagnostico.evidencia.foto_base64
            if ',' in foto_data:
                foto_data = foto_data.split(',')[1]

            with open(filepath, "wb") as f:
                f.write(base64.b64decode(foto_data))

            # Insertar referencia en la tabla evidencias
            cursor.execute("""
                INSERT INTO evidencias (pk_seccion, ruta_archivo, comentario, fecha_registro)
                VALUES (%s, %s, %s, %s)
            """, (
                pk_seccion,
                filepath,
                diagnostico.evidencia.comentario,
                diagnostico.fecha_recoleccion
            ))

        # 6. Guardar coordenadas GPS (si se proporcionaron)
        if diagnostico.latitud is not None and diagnostico.longitud is not None:
            cursor.execute("""
                INSERT INTO logs_gps (pk_seccion, latitud, longitud, fecha_registro)
                VALUES (%s, %s, %s, %s)
            """, (
                pk_seccion,
                diagnostico.latitud,
                diagnostico.longitud,
                diagnostico.fecha_recoleccion
            ))

        conn.commit()
        return {"mensaje": "Diagnóstico guardado correctamente"}

    except HTTPException:
        # Re-lanzar excepciones HTTP (404, etc.) para que FastAPI las maneje
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        # Imprimir traceback completo en la consola para depuración
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/exportar-excel")
async def exportar_excel():
    """
    Genera un archivo Excel con todos los datos de recolección:
    - sentimiento_social (con número de sección)
    - simpatizantes
    - evidencias
    - logs_gps
    """
    conn = engine.raw_connection()
    # Crear archivo temporal (no se borra automáticamente al cerrar)
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    output_path = tmp.name
    tmp.close()  # Cerramos para poder escribir con ExcelWriter

    try:
        # 1. Sentimiento social con número de sección
        df_sentimiento = pd.read_sql("""
            SELECT 
                s.seccion,
                cs.nombre_categoria as servicio,
                ss.calificacion,
                ss.sentimiento_polaridad,
                ss.fecha_registro
            FROM sentimiento_social ss
            JOIN seccion s ON ss.pk_seccion = s.pk_seccion
            JOIN categoria_servicio cs ON ss.id_categoria = cs.id_categoria
            ORDER BY ss.fecha_registro DESC
        """, conn)

        # 2. Simpatizantes
        df_simpatizantes = pd.read_sql("""
            SELECT 
                s.seccion,
                sim.nombre,
                sim.contacto,
                sim.es_mujer,
                sim.notas,
                sim.fecha_registro
            FROM simpatizantes sim
            JOIN seccion s ON sim.pk_seccion = s.pk_seccion
            ORDER BY sim.fecha_registro DESC
        """, conn)

        # 3. Evidencias
        df_evidencias = pd.read_sql("""
            SELECT 
                s.seccion,
                e.ruta_archivo,
                e.comentario,
                e.fecha_registro
            FROM evidencias e
            JOIN seccion s ON e.pk_seccion = s.pk_seccion
            ORDER BY e.fecha_registro DESC
        """, conn)

        # 4. Logs GPS
        df_gps = pd.read_sql("""
            SELECT 
                s.seccion,
                g.latitud,
                g.longitud,
                g.fecha_registro
            FROM logs_gps g
            JOIN seccion s ON g.pk_seccion = s.pk_seccion
            ORDER BY g.fecha_registro DESC
        """, conn)

        # Escribir todas las hojas en el Excel
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df_sentimiento.to_excel(writer, sheet_name="Sentimiento Social", index=False)
            df_simpatizantes.to_excel(writer, sheet_name="Simpatizantes", index=False)
            df_evidencias.to_excel(writer, sheet_name="Evidencias", index=False)
            df_gps.to_excel(writer, sheet_name="GPS", index=False)

        # Devolver el archivo y programar su eliminación después de enviarlo
        return FileResponse(
            path=output_path,
            filename="diagnosticos_campo.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            background=BackgroundTask(lambda: os.unlink(output_path))
        )

    except Exception as e:
        # Si hay error, eliminar el archivo temporal si existe
        if os.path.exists(output_path):
            os.unlink(output_path)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al generar Excel: {str(e)}")
    finally:
        conn.close()
# Modelos Pydantic
class InvitacionRequest(BaseModel):
    email: EmailStr
    tenant_id: str
    dias_validez: int = 7  # por defecto 7 días

class InvitacionResponse(BaseModel):
    token: str
    link: str
API_ADMIN_KEY = os.getenv("API_ADMIN_KEY", "cambia_esto_en_produccion")

@app.post("/api/admin/invitacion", response_model=InvitacionResponse)
async def crear_invitacion(inv: InvitacionRequest, admin_key: str = Header(...)):
    if admin_key != API_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="No autorizado")
    """
    Genera un token de invitación para un email y tenant.
    Este endpoint debería estar protegido con una clave de administrador.
    """
    token = str(uuid.uuid4())
    expiracion = datetime.utcnow() + timedelta(days=inv.dias_validez)
    
    conn = engine.raw_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO invitaciones (token, email, tenant_id, fecha_expiracion)
            VALUES (%s, %s, %s, %s)
        """, (token, inv.email, inv.tenant_id, expiracion))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
    
    # Construir el link (cuando el dashboard esté desplegado, será https://...)
    # En local usamos localhost:8501
    dashboard_url = os.getenv("DASHBOARD_URL", "https://5mefjgvsuazhayejhm92vk.streamlit.app")
    link = f"{dashboard_url}?invite={token}"
    return InvitacionResponse(token=token, link=link)
@app.get("/api/validate-invite/{token}")
async def validate_invite(token: str):
    from sqlalchemy import text
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT email, tenant_id, fecha_expiracion, usada FROM invitaciones WHERE token = :token"),
            {"token": token}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Token no encontrado")
        email, tenant_id, expiracion, usada = row
        if usada:
            raise HTTPException(status_code=400, detail="Invitación ya utilizada")
        if datetime.utcnow() > expiracion:
            raise HTTPException(status_code=400, detail="Invitación expirada")
        conn.execute(text("UPDATE invitaciones SET usada = TRUE WHERE token = :token"), {"token": token})
        conn.execute(text("""
            INSERT INTO usuarios_tenant (email, tenant_id, fecha_expiracion)
            VALUES (:email, :tenant_id, :exp)
            ON CONFLICT (email) DO UPDATE 
            SET tenant_id = EXCLUDED.tenant_id, fecha_expiracion = EXCLUDED.fecha_expiracion
        """), {"email": email, "tenant_id": tenant_id, "exp": expiracion})
        conn.commit()
        return {"email": email, "tenant_id": tenant_id}
        conn.close()

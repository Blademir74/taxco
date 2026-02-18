from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import uuid
from ..database import engine
from ..auth import get_current_admin  # Asumiendo que tienes autenticación de admin

router = APIRouter(prefix="/admin", tags=["admin"])

class InviteRequest(BaseModel):
    email: EmailStr
    tenant_id: str
    days_valid: int = 7  # días de validez

class InviteResponse(BaseModel):
    invite_link: str

@router.post("/invites", response_model=InviteResponse)
async def crear_invitacion(
    request: InviteRequest,
    admin=Depends(get_current_admin)  # Solo administradores pueden crear
):
    token = str(uuid.uuid4())
    expiracion = datetime.utcnow() + timedelta(days=request.days_valid)

    conn = engine.raw_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO invitaciones (token, email, tenant_id, fecha_expiracion)
            VALUES (%s, %s, %s, %s)
        """, (token, request.email, request.tenant_id, expiracion))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

    # Construir el link (cambia la URL base por la de tu dashboard)
    base_url = "https://tudashboard.streamlit.app"
    invite_link = f"{base_url}?invite={token}"
    return InviteResponse(invite_link=invite_link)

@router.get("/invites")
async def listar_invitaciones(admin=Depends(get_current_admin)):
    conn = engine.raw_connection()
    df = pd.read_sql("SELECT * FROM invitaciones ORDER BY fecha_creacion DESC", conn)
    conn.close()
    return df.to_dict(orient="records")
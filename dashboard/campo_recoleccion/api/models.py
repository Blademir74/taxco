from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class SentimientoServicio(BaseModel):
    agua: int = Field(..., ge=1, le=5)
    basura: int = Field(..., ge=1, le=5)
    seguridad: int = Field(..., ge=1, le=5)

class Carencias(BaseModel):
    falta_agua: bool = False
    falta_drenaje: bool = False
    rezago_educativo: bool = False

class Simpatizante(BaseModel):
    nombre: str
    contacto: str
    es_mujer: bool                         # Campo obligatorio para segmentación
    notas: Optional[str] = None

class Evidencia(BaseModel):
    foto_base64: Optional[str] = None       # Imagen en base64 (opcional)
    comentario: Optional[str] = None

class DiagnosticoTerritorio(BaseModel):
    seccion: int
    sentimiento: SentimientoServicio
    carencias: Carencias
    simpatizante: Simpatizante
    evidencia: Optional[Evidencia] = None
    latitud: Optional[float] = None         # GPS
    longitud: Optional[float] = None
    fecha_recoleccion: datetime = Field(default_factory=datetime.now)
    usuario: Optional[str] = None

    # Validación personalizada: si falta_agua es True, no puede ser nulo (ya es bool)
    @validator('seccion')
    def seccion_debe_existir(cls, v):
        # La validación de existencia se hará en la BD, pero podemos agregar una básica
        if v <= 0:
            raise ValueError('La sección debe ser un número positivo')
        return v
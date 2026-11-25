"""
Esquemas de entrada/salida (Pydantic).

FastAPI usa estos esquemas para dos cosas automaticamente:
1) Validar que lo que llega en el body de una peticion tenga los campos
   obligatorios y el tipo correcto (esto es, literalmente, el RF-004).
2) Dar forma a lo que se devuelve en las respuestas, sin exponer campos
   internos que no queremos mostrar.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models import Rol, EstadoSolicitud, TipoConcepto


# ---------------------------------------------------------------------
# Usuarios / login simulado (RF-001, RF-002)
# ---------------------------------------------------------------------

class UsuarioOut(BaseModel):
    id: int
    nombre: str
    rol: Rol
    area_id: Optional[int] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------
# Solicitudes (RF-003 a RF-007)
# ---------------------------------------------------------------------

class SolicitudCreate(BaseModel):
    # str_strip_whitespace: "   " (solo espacios) cuenta como vacio.
    # min_length=1: un campo obligatorio no puede quedar en blanco (RF-004).
    model_config = ConfigDict(str_strip_whitespace=True)

    peticionario_nombre: str = Field(min_length=1)
    peticionario_documento: str = Field(min_length=1)
    peticionario_correo: EmailStr
    tipo_intervencion: str = Field(min_length=1)
    descripcion: Optional[str] = None


class AreaOut(BaseModel):
    id: int
    nombre: str
    sla_dias: int

    class Config:
        from_attributes = True


class SolicitudOut(BaseModel):
    id: int
    numero_radicado: str
    peticionario_nombre: str
    peticionario_documento: str
    peticionario_correo: str
    tipo_intervencion: str
    descripcion: Optional[str]
    estado: EstadoSolicitud
    area: Optional[AreaOut]
    fecha_radicacion: datetime
    fecha_ultimo_cambio: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------
# Historial / auditoria (RF-008, RF-009, RF-010)
# ---------------------------------------------------------------------

class CambioEstadoOut(BaseModel):
    estado_anterior: Optional[EstadoSolicitud]
    estado_nuevo: EstadoSolicitud
    usuario: str
    comentario: Optional[str]
    fecha: datetime

    class Config:
        from_attributes = True


class AdjuntoOut(BaseModel):
    id: int
    nombre_original: str
    tipo_contenido: Optional[str]
    tamano_bytes: int
    fecha_subida: datetime

    class Config:
        from_attributes = True


class SolicitudConHistorialOut(SolicitudOut):
    cambios_estado: List[CambioEstadoOut] = []
    adjuntos: List[AdjuntoOut] = []


# ---------------------------------------------------------------------
# Conceptos tecnicos (RF-011, RF-012)
# ---------------------------------------------------------------------

class ConceptoCreate(BaseModel):
    tipo: TipoConcepto
    observacion: Optional[str] = None
    usuario: str  # nombre de quien registra el concepto (del login simulado)


# ---------------------------------------------------------------------
# Alertas (RF-013, RF-014)
# ---------------------------------------------------------------------

class AlertaOut(BaseModel):
    id: int
    solicitud_id: int
    area_id: int
    dias_transcurridos: int
    fecha_generada: datetime
    atendida: bool

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------
# Indicadores / panel de control (RF-015, RF-016)
# ---------------------------------------------------------------------

class TiempoPromedioPorArea(BaseModel):
    area: str
    tiempo_promedio_dias: float
    solicitudes_consideradas: int


class VencidasPorArea(BaseModel):
    area: str
    solicitudes_vencidas: int

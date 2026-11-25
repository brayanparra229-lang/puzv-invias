"""
Modelos de datos (tablas) del sistema de trazabilidad PUZV - INVIAS.

Cada clase es una tabla. Los nombres de los campos estan en espanol para
que coincidan con el lenguaje que usamos en los requisitos funcionales
(RF) y en la matriz de trazabilidad del trabajo de grado.
"""

import enum
from datetime import datetime
from app.utils import ahora_colombia

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ---------------------------------------------------------------------
# Catalogos (enums)
# ---------------------------------------------------------------------

class Rol(str, enum.Enum):
    PETICIONARIO = "peticionario"
    GESTOR = "gestor"
    AREA_TECNICA = "area_tecnica"
    ADMINISTRADOR = "administrador"


class EstadoSolicitud(str, enum.Enum):
    RADICADA = "radicada"
    EN_REVISION = "en_revision"
    CONCEPTO_PENDIENTE = "concepto_pendiente"
    SUBSANACION = "subsanacion"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


class TipoConcepto(str, enum.Enum):
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    REQUIERE_SUBSANACION = "requiere_subsanacion"


# ---------------------------------------------------------------------
# Tablas
# ---------------------------------------------------------------------

class Area(Base):
    """Las 4 areas tecnicas que emiten concepto: pavimentos, geotecnica,
    diseno geometrico, hidraulica."""

    __tablename__ = "areas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    sla_dias = Column(Integer, nullable=False, default=5)  # RF-013

    usuarios = relationship("Usuario", back_populates="area")
    solicitudes = relationship("Solicitud", back_populates="area")


class Usuario(Base):
    """Representa a cualquier persona que entra al sistema. Para el
    prototipo el login es simulado (RF-001): no hay password real, solo
    se elige un usuario/rol existente."""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    rol = Column(SQLEnum(Rol), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)  # solo si rol = area_tecnica
    activo = Column(Boolean, default=True)

    area = relationship("Area", back_populates="usuarios")


class TipoIntervencionArea(Base):
    """Tabla de reglas para la asignacion automatica (RF-007): a que area
    va cada tipo de intervencion."""

    __tablename__ = "tipos_intervencion_area"

    id = Column(Integer, primary_key=True, index=True)
    tipo_intervencion = Column(String(150), unique=True, nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)

    area = relationship("Area")


class Solicitud(Base):
    """Una solicitud de Permiso de Uso de Zona de Via (PUZV)."""

    __tablename__ = "solicitudes"

    id = Column(Integer, primary_key=True, index=True)
    numero_radicado = Column(String(20), unique=True, index=True, nullable=False)  # RF-005

    peticionario_nombre = Column(String(150), nullable=False)
    peticionario_documento = Column(String(30), nullable=False)
    peticionario_correo = Column(String(150), nullable=False)

    tipo_intervencion = Column(String(150), nullable=False)
    descripcion = Column(String(1000), nullable=True)

    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)  # se llena en RF-007
    estado = Column(SQLEnum(EstadoSolicitud), nullable=False, default=EstadoSolicitud.RADICADA)

    fecha_radicacion = Column(DateTime, default=ahora_colombia)
    fecha_ultimo_cambio = Column(DateTime, default=ahora_colombia)  # usado para calcular el SLA (RF-013)

    area = relationship("Area", back_populates="solicitudes")
    cambios_estado = relationship("CambioEstado", back_populates="solicitud", order_by="CambioEstado.fecha")
    conceptos = relationship("Concepto", back_populates="solicitud")
    alertas = relationship("Alerta", back_populates="solicitud")
    adjuntos = relationship("Adjunto", back_populates="solicitud", order_by="Adjunto.fecha_subida")


class CambioEstado(Base):
    """Historial / auditoria de cada cambio de estado (RF-009, RF-010)."""

    __tablename__ = "cambios_estado"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), nullable=False)

    estado_anterior = Column(SQLEnum(EstadoSolicitud), nullable=True)
    estado_nuevo = Column(SQLEnum(EstadoSolicitud), nullable=False)
    usuario = Column(String(150), nullable=False)  # quien hizo el cambio
    comentario = Column(String(500), nullable=True)
    fecha = Column(DateTime, default=ahora_colombia)

    solicitud = relationship("Solicitud", back_populates="cambios_estado")


class Concepto(Base):
    """El concepto que emite un area tecnica sobre una solicitud (RF-011)."""

    __tablename__ = "conceptos"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)

    tipo = Column(SQLEnum(TipoConcepto), nullable=False)
    observacion = Column(String(1000), nullable=True)
    fecha = Column(DateTime, default=ahora_colombia)

    solicitud = relationship("Solicitud", back_populates="conceptos")
    area = relationship("Area")


class Alerta(Base):
    """Una alerta generada cuando una solicitud supera el SLA de su area
    (RF-013, RF-014)."""

    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)

    dias_transcurridos = Column(Integer, nullable=False)
    fecha_generada = Column(DateTime, default=ahora_colombia)
    atendida = Column(Boolean, default=False)

    solicitud = relationship("Solicitud", back_populates="alertas")
    area = relationship("Area")


class Adjunto(Base):
    """Documento de soporte que sube el peticionario (planos, formatos,
    etc.) al radicar o despues de radicar la solicitud (RF-021)."""

    __tablename__ = "adjuntos"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), nullable=False)

    nombre_original = Column(String(255), nullable=False)   # como se llamaba el archivo
    nombre_guardado = Column(String(255), nullable=False, unique=True)  # nombre unico en disco
    tipo_contenido = Column(String(100), nullable=True)
    tamano_bytes = Column(Integer, nullable=False)
    fecha_subida = Column(DateTime, default=ahora_colombia)

    solicitud = relationship("Solicitud", back_populates="adjuntos")

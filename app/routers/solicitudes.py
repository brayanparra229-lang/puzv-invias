"""
RF-003: Registrar solicitud de PUZV.
RF-004: Validar campos obligatorios al radicar (lo hace Pydantic solo:
         si falta un campo del esquema SolicitudCreate, FastAPI responde
         automaticamente con error 422 antes de que este codigo corra).
RF-005: Generar numero de radicado unico.
RF-006: Confirmar la radicacion al peticionario (se hace devolviendo el
         objeto completo, incluido el numero de radicado, en la misma
         respuesta de crear la solicitud).
RF-007: Asignar automaticamente el area tecnica segun el tipo de
         intervencion.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.utils import ahora_colombia
from app import models, schemas
from app.state_machine import transicion_valida

router = APIRouter(prefix="/solicitudes", tags=["Solicitudes (RF-003 a RF-007)"])


def _generar_numero_radicado(db: Session) -> str:
    """RF-005: PUZV-<anio>-<consecutivo de 4 digitos>, por ejemplo PUZV-2026-0001."""
    anio = ahora_colombia().year
    total_existentes = db.query(models.Solicitud).count()
    consecutivo = total_existentes + 1
    return f"PUZV-{anio}-{consecutivo:04d}"


def _asignar_area(db: Session, tipo_intervencion: str) -> Optional[models.Area]:
    """RF-007: busca en la tabla de reglas a que area corresponde el tipo
    de intervencion. Si no hay una regla definida para ese tipo, la
    solicitud queda sin area (para que el gestor la asigne manualmente
    mas adelante, cuando construyamos esa parte)."""
    regla = (
        db.query(models.TipoIntervencionArea)
        .filter(models.TipoIntervencionArea.tipo_intervencion == tipo_intervencion)
        .first()
    )
    if regla:
        return db.query(models.Area).filter(models.Area.id == regla.area_id).first()
    return None


@router.post("/", response_model=schemas.SolicitudOut, status_code=201)
def registrar_solicitud(datos: schemas.SolicitudCreate, db: Session = Depends(get_db)):
    """
    Punto de entrada principal del sistema: un peticionario radica una
    solicitud. Aqui se encadenan RF-003 a RF-007 en un solo paso, porque
    en la practica ocurren juntos cuando alguien envia el formulario.
    """
    numero_radicado = _generar_numero_radicado(db)
    area = _asignar_area(db, datos.tipo_intervencion)

    nueva = models.Solicitud(
        numero_radicado=numero_radicado,
        peticionario_nombre=datos.peticionario_nombre,
        peticionario_documento=datos.peticionario_documento,
        peticionario_correo=datos.peticionario_correo,
        tipo_intervencion=datos.tipo_intervencion,
        descripcion=datos.descripcion,
        area_id=area.id if area else None,
        estado=models.EstadoSolicitud.RADICADA,
    )
    db.add(nueva)
    db.flush()  # para que 'nueva' tenga id antes de usarla abajo

    # Primer registro de auditoria: nace la solicitud (RF-009, RF-010)
    primer_cambio = models.CambioEstado(
        solicitud_id=nueva.id,
        estado_anterior=None,
        estado_nuevo=models.EstadoSolicitud.RADICADA,
        usuario=datos.peticionario_nombre,
        comentario="Solicitud radicada por el peticionario.",
    )
    db.add(primer_cambio)

    # Si se pudo asignar un area automaticamente, la solicitud pasa de
    # una vez a "Concepto pendiente": ya esta lista para que el area
    # registre su concepto (RF-011/RF-012, siguiente modulo).
    if area and transicion_valida(nueva.estado, models.EstadoSolicitud.CONCEPTO_PENDIENTE):
        segundo_cambio = models.CambioEstado(
            solicitud_id=nueva.id,
            estado_anterior=nueva.estado,
            estado_nuevo=models.EstadoSolicitud.CONCEPTO_PENDIENTE,
            usuario="Sistema",
            comentario=f"Asignada automaticamente al area {area.nombre}, pendiente de concepto tecnico.",
        )
        db.add(segundo_cambio)
        nueva.estado = models.EstadoSolicitud.CONCEPTO_PENDIENTE
        nueva.fecha_ultimo_cambio = ahora_colombia()

    db.commit()
    db.refresh(nueva)
    return nueva


@router.get("/", response_model=List[schemas.SolicitudOut])
def listar_solicitudes(db: Session = Depends(get_db)):
    """Util para probar en /docs mientras no tenemos frontend todavia."""
    return db.query(models.Solicitud).all()


@router.get("/{numero_radicado}", response_model=schemas.SolicitudConHistorialOut)
def consultar_solicitud(numero_radicado: str, db: Session = Depends(get_db)):
    """
    RF-008: estado actual de la solicitud.
    RF-009: historial completo (linea de tiempo) de cambios de estado,
            incluido en la misma respuesta.
    """
    solicitud = (
        db.query(models.Solicitud)
        .filter(models.Solicitud.numero_radicado == numero_radicado)
        .first()
    )
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return solicitud

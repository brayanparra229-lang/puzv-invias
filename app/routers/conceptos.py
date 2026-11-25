"""
RF-011: Registrar el concepto tecnico del area (aprobado / rechazado /
         requiere subsanacion).
RF-012: Actualizar el estado de la solicitud segun el concepto
         registrado, de forma automatica.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.utils import ahora_colombia
from app import models, schemas
from app.state_machine import transicion_valida

router = APIRouter(prefix="/solicitudes", tags=["Conceptos tecnicos (RF-011, RF-012)"])


# A que estado pasa la solicitud segun el tipo de concepto que registra el area
MAPA_CONCEPTO_A_ESTADO = {
    models.TipoConcepto.APROBADO: models.EstadoSolicitud.APROBADA,
    models.TipoConcepto.RECHAZADO: models.EstadoSolicitud.RECHAZADA,
    models.TipoConcepto.REQUIERE_SUBSANACION: models.EstadoSolicitud.SUBSANACION,
}


@router.post("/{numero_radicado}/concepto", response_model=schemas.SolicitudConHistorialOut)
def registrar_concepto(
    numero_radicado: str,
    datos: schemas.ConceptoCreate,
    db: Session = Depends(get_db),
):
    solicitud = (
        db.query(models.Solicitud)
        .filter(models.Solicitud.numero_radicado == numero_radicado)
        .first()
    )
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != models.EstadoSolicitud.CONCEPTO_PENDIENTE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se puede registrar un concepto: la solicitud esta en "
                f"estado '{solicitud.estado.value}', no en 'concepto_pendiente'."
            ),
        )

    if not solicitud.area_id:
        raise HTTPException(status_code=400, detail="La solicitud no tiene un area asignada.")

    # RF-011: registrar el concepto
    concepto = models.Concepto(
        solicitud_id=solicitud.id,
        area_id=solicitud.area_id,
        tipo=datos.tipo,
        observacion=datos.observacion,
    )
    db.add(concepto)

    # RF-012: actualizar el estado automaticamente segun el concepto
    nuevo_estado = MAPA_CONCEPTO_A_ESTADO[datos.tipo]
    if not transicion_valida(solicitud.estado, nuevo_estado):
        raise HTTPException(
            status_code=400,
            detail=f"Transicion de '{solicitud.estado.value}' a '{nuevo_estado.value}' no permitida.",
        )

    cambio = models.CambioEstado(
        solicitud_id=solicitud.id,
        estado_anterior=solicitud.estado,
        estado_nuevo=nuevo_estado,
        usuario=datos.usuario,
        comentario=f"Concepto '{datos.tipo.value}' registrado. {datos.observacion or ''}".strip(),
    )
    db.add(cambio)

    solicitud.estado = nuevo_estado
    solicitud.fecha_ultimo_cambio = ahora_colombia()

    db.commit()
    db.refresh(solicitud)
    return solicitud

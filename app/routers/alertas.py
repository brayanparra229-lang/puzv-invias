"""
RF-013: Calcular si una solicitud supero el SLA de su area actual.
RF-014: Generar alerta cuando se vence el SLA.

Para el prototipo, la revision del SLA se dispara manualmente llamando
a POST /alertas/revisar (pensado para que lo llame un boton "Revisar
alertas" en el panel, o para probarlo directo en /docs). En una version
real de produccion, esto se programaria para correr solo cada cierto
tiempo (por ejemplo con APScheduler), pero eso queda documentado como
RF-030 (trabajo futuro) para no complicar la demo.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.utils import ahora_colombia
from app import models, schemas

router = APIRouter(prefix="/alertas", tags=["Alertas por SLA (RF-013, RF-014)"])

# Estados en los que una solicitud esta "esperando" a un area tecnica,
# y por lo tanto puede llegar a vencer el SLA
ESTADOS_SUJETOS_A_SLA = [
    models.EstadoSolicitud.CONCEPTO_PENDIENTE,
    models.EstadoSolicitud.SUBSANACION,
]


@router.post("/revisar", response_model=List[schemas.AlertaOut])
def revisar_sla(db: Session = Depends(get_db)):
    """
    RF-013 + RF-014: recorre todas las solicitudes activas, calcula
    cuantos dias llevan en su area actual, y genera una alerta nueva
    para las que superan el SLA de esa area (si no tienen ya una
    alerta sin atender).
    """
    ahora = ahora_colombia()
    alertas_generadas = []

    solicitudes_activas = (
        db.query(models.Solicitud)
        .filter(models.Solicitud.estado.in_(ESTADOS_SUJETOS_A_SLA))
        .filter(models.Solicitud.area_id.isnot(None))
        .all()
    )

    for solicitud in solicitudes_activas:
        dias_transcurridos = (ahora - solicitud.fecha_ultimo_cambio).days
        if dias_transcurridos <= solicitud.area.sla_dias:
            continue  # todavia dentro del tiempo permitido

        # No duplicar: si ya hay una alerta sin atender para esta
        # solicitud, no se genera otra
        ya_tiene_alerta = (
            db.query(models.Alerta)
            .filter(models.Alerta.solicitud_id == solicitud.id)
            .filter(models.Alerta.atendida == False)
            .first()
        )
        if ya_tiene_alerta:
            continue

        nueva_alerta = models.Alerta(
            solicitud_id=solicitud.id,
            area_id=solicitud.area_id,
            dias_transcurridos=dias_transcurridos,
        )
        db.add(nueva_alerta)
        alertas_generadas.append(nueva_alerta)

    db.commit()
    for a in alertas_generadas:
        db.refresh(a)
    return alertas_generadas


@router.get("/", response_model=List[schemas.AlertaOut])
def listar_alertas(solo_sin_atender: bool = True, db: Session = Depends(get_db)):
    """Lista las alertas generadas. Por defecto solo muestra las que
    todavia no han sido atendidas por el area responsable."""
    query = db.query(models.Alerta)
    if solo_sin_atender:
        query = query.filter(models.Alerta.atendida == False)
    return query.all()


@router.post("/{alerta_id}/atender", response_model=schemas.AlertaOut)
def marcar_alerta_atendida(alerta_id: int, db: Session = Depends(get_db)):
    """Permite al area marcar una alerta como revisada."""
    alerta = db.query(models.Alerta).filter(models.Alerta.id == alerta_id).first()
    if not alerta:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    alerta.atendida = True
    db.commit()
    db.refresh(alerta)
    return alerta

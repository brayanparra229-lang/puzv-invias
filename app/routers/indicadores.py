"""
RF-015: Mostrar tiempo promedio de respuesta por area.
RF-016: Mostrar solicitudes vencidas por area.

Este es el router que alimenta el panel de control: las dos consultas
que un lider de INVIAS necesita ver de un vistazo para saber donde
estan los cuellos de botella del tramite PUZV.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.utils import ahora_colombia
from app import models
from app import schemas
from app.routers.alertas import ESTADOS_SUJETOS_A_SLA

router = APIRouter(prefix="/indicadores", tags=["Panel de control (RF-015, RF-016)"])


@router.get("/tiempo-promedio-por-area", response_model=List[schemas.TiempoPromedioPorArea])
def tiempo_promedio_por_area(db: Session = Depends(get_db)):
    """
    RF-015. Para cada area, promedia cuantos dias tardo en emitir
    concepto en las solicitudes que ya resolvio (desde que se radico la
    solicitud hasta la fecha del concepto). Las areas sin conceptos
    registrados todavia no aparecen en la lista.
    """
    resultados = []
    areas = db.query(models.Area).all()

    for area in areas:
        conceptos = (
            db.query(models.Concepto)
            .join(models.Solicitud, models.Concepto.solicitud_id == models.Solicitud.id)
            .filter(models.Concepto.area_id == area.id)
            .all()
        )
        if not conceptos:
            continue

        dias_totales = 0
        for concepto in conceptos:
            solicitud = concepto.solicitud
            dias_totales += (concepto.fecha - solicitud.fecha_radicacion).days

        promedio = dias_totales / len(conceptos)
        resultados.append(
            schemas.TiempoPromedioPorArea(
                area=area.nombre,
                tiempo_promedio_dias=round(promedio, 1),
                solicitudes_consideradas=len(conceptos),
            )
        )

    return resultados


@router.get("/vencidas-por-area", response_model=List[schemas.VencidasPorArea])
def vencidas_por_area(db: Session = Depends(get_db)):
    """
    RF-016. Para cada area, cuenta cuantas solicitudes activas (todavia
    esperando concepto) ya superaron el SLA definido para esa area.
    """
    ahora = ahora_colombia()
    resultados = []
    areas = db.query(models.Area).all()

    for area in areas:
        solicitudes_activas = (
            db.query(models.Solicitud)
            .filter(models.Solicitud.area_id == area.id)
            .filter(models.Solicitud.estado.in_(ESTADOS_SUJETOS_A_SLA))
            .all()
        )
        vencidas = sum(
            1 for s in solicitudes_activas
            if (ahora - s.fecha_ultimo_cambio).days > area.sla_dias
        )
        resultados.append(schemas.VencidasPorArea(area=area.nombre, solicitudes_vencidas=vencidas))

    return resultados

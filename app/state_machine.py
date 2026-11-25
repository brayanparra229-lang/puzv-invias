"""
Maquina de estados de una solicitud PUZV.

Aqui se define, de un solo lugar, a que estados puede pasar una
solicitud desde su estado actual. Esto evita que por un error de codigo
una solicitud "salte" a un estado que no tiene sentido (por ejemplo, de
Radicada directo a Aprobada, sin pasar por el concepto tecnico).
"""

from app.models import EstadoSolicitud

TRANSICIONES_VALIDAS = {
    EstadoSolicitud.RADICADA: [EstadoSolicitud.CONCEPTO_PENDIENTE],
    EstadoSolicitud.CONCEPTO_PENDIENTE: [
        EstadoSolicitud.APROBADA,
        EstadoSolicitud.RECHAZADA,
        EstadoSolicitud.SUBSANACION,
    ],
    EstadoSolicitud.SUBSANACION: [EstadoSolicitud.CONCEPTO_PENDIENTE],
    EstadoSolicitud.EN_REVISION: [EstadoSolicitud.CONCEPTO_PENDIENTE],
    EstadoSolicitud.APROBADA: [],   # estado final
    EstadoSolicitud.RECHAZADA: [],  # estado final
}


def transicion_valida(estado_actual: EstadoSolicitud, estado_nuevo: EstadoSolicitud) -> bool:
    """Responde si se puede pasar de estado_actual a estado_nuevo."""
    return estado_nuevo in TRANSICIONES_VALIDAS.get(estado_actual, [])

"""
RF-021: Adjuntar archivos (planos, documentos de soporte) a la solicitud.

Como se guardan los archivos:
- En disco, dentro de la carpeta `uploads/` del proyecto.
- Con un nombre unico generado por el sistema (uuid), nunca con el
  nombre que trae el archivo: asi dos personas pueden subir
  "plano.pdf" sin que se pisen, y nadie puede colar un nombre raro
  tipo "../../algo" para escribir fuera de la carpeta.
- En la base de datos queda el registro (tabla `adjuntos`) con el
  nombre original, el tamano y a que solicitud pertenece.
"""

import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.utils import UPLOAD_DIR

router = APIRouter(prefix="/solicitudes", tags=["Documentos adjuntos (RF-021)"])

EXTENSIONES_PERMITIDAS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx",
    ".xls", ".xlsx", ".dwg", ".zip",
}
TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB por archivo

# En estos estados la solicitud ya esta cerrada: no se aceptan mas documentos
ESTADOS_CERRADOS = [models.EstadoSolicitud.APROBADA, models.EstadoSolicitud.RECHAZADA]


def _buscar_solicitud(db: Session, numero_radicado: str) -> models.Solicitud:
    solicitud = (
        db.query(models.Solicitud)
        .filter(models.Solicitud.numero_radicado == numero_radicado)
        .first()
    )
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return solicitud


@router.post(
    "/{numero_radicado}/adjuntos",
    response_model=List[schemas.AdjuntoOut],
    status_code=201,
)
def subir_adjuntos(
    numero_radicado: str,
    archivos: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Sube uno o varios documentos a una solicitud ya radicada."""
    solicitud = _buscar_solicitud(db, numero_radicado)

    if solicitud.estado in ESTADOS_CERRADOS:
        raise HTTPException(
            status_code=400,
            detail="La solicitud ya esta cerrada: no se pueden agregar mas documentos.",
        )

    # 1) Validar TODOS los archivos antes de guardar alguno, para no dejar
    #    una subida a medias si el tercer archivo esta mal.
    validados = []
    for archivo in archivos:
        extension = Path(archivo.filename or "").suffix.lower()
        if extension not in EXTENSIONES_PERMITIDAS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"'{archivo.filename}': tipo de archivo no permitido. "
                    f"Permitidos: {', '.join(sorted(EXTENSIONES_PERMITIDAS))}"
                ),
            )
        contenido = archivo.file.read(TAMANO_MAXIMO_BYTES + 1)
        if len(contenido) == 0:
            raise HTTPException(status_code=400, detail=f"'{archivo.filename}' esta vacio.")
        if len(contenido) > TAMANO_MAXIMO_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"'{archivo.filename}' supera el maximo de 10 MB.",
            )
        validados.append((archivo.filename, extension, archivo.content_type, contenido))

    # 2) Guardar en disco y registrar en la base de datos
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    creados = []
    for nombre_original, extension, tipo, contenido in validados:
        nombre_guardado = f"{uuid.uuid4().hex}{extension}"
        (UPLOAD_DIR / nombre_guardado).write_bytes(contenido)

        adjunto = models.Adjunto(
            solicitud_id=solicitud.id,
            nombre_original=nombre_original,
            nombre_guardado=nombre_guardado,
            tipo_contenido=tipo,
            tamano_bytes=len(contenido),
        )
        db.add(adjunto)
        creados.append(adjunto)

    db.commit()
    for a in creados:
        db.refresh(a)
    return creados


@router.get("/{numero_radicado}/adjuntos/{adjunto_id}")
def descargar_adjunto(numero_radicado: str, adjunto_id: int, db: Session = Depends(get_db)):
    """Descarga un documento adjunto con su nombre original."""
    solicitud = _buscar_solicitud(db, numero_radicado)
    adjunto = (
        db.query(models.Adjunto)
        .filter(models.Adjunto.id == adjunto_id)
        .filter(models.Adjunto.solicitud_id == solicitud.id)
        .first()
    )
    if not adjunto:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    ruta = UPLOAD_DIR / adjunto.nombre_guardado
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="El archivo ya no esta en el servidor")

    return FileResponse(
        path=ruta,
        filename=adjunto.nombre_original,
        media_type=adjunto.tipo_contenido or "application/octet-stream",
    )

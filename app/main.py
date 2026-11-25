"""
Punto de entrada de la aplicacion.

Para correrlo (con el entorno virtual activado):
    uvicorn app.main:app --reload

Luego abre http://127.0.0.1:8000/docs para ver y probar todos los
endpoints desde el navegador (FastAPI genera esa pantalla solo).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, SessionLocal
from app import models
from app.routers import auth, solicitudes, conceptos, alertas, indicadores, adjuntos
from app.utils import UPLOAD_DIR

app = FastAPI(
    title="Sistema de Trazabilidad PUZV - INVIAS",
    description="Prototipo de trabajo de grado para el seguimiento del "
                 "tramite del Permiso de Uso de Zona de Via.",
    version="0.1.0",
)

# Permite que un frontend corriendo en otro puerto (ej. React en :5173)
# pueda llamar a esta API sin que el navegador lo bloquee.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(solicitudes.router)
app.include_router(adjuntos.router)
app.include_router(conceptos.router)
app.include_router(alertas.router)
app.include_router(indicadores.router)


@app.on_event("startup")
def iniciar():
    # Crea las tablas si no existen todavia
    Base.metadata.create_all(bind=engine)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    _precargar_datos_iniciales()


def _precargar_datos_iniciales():
    """Crea las 4 areas tecnicas (con su SLA) y las reglas de asignacion
    automatica, solo si la base de datos esta vacia. Asi no tienes que
    crearlas a mano cada vez que pruebes el sistema."""

    db = SessionLocal()
    try:
        if db.query(models.Area).count() > 0:
            return  # ya existen, no hacer nada

        areas = {
            "Pavimentos": 5,
            "Geotecnica": 5,
            "Diseno Geometrico": 4,
            "Hidraulica": 6,
        }
        area_objs = {}
        for nombre, sla in areas.items():
            area = models.Area(nombre=nombre, sla_dias=sla)
            db.add(area)
            db.flush()  # para obtener el id antes de hacer commit
            area_objs[nombre] = area

        reglas = {
            "Cruce de redes": "Hidraulica",
            "Acceso vehicular": "Diseno Geometrico",
            "Obra de drenaje": "Hidraulica",
            "Excavacion": "Geotecnica",
            "Reparcheo / pavimento": "Pavimentos",
        }
        for tipo, area_nombre in reglas.items():
            db.add(models.TipoIntervencionArea(
                tipo_intervencion=tipo,
                area_id=area_objs[area_nombre].id,
            ))

        db.commit()

        # Usuarios de prueba, uno por cada rol, para poder "iniciar
        # sesion" (RF-001) sin tener que crearlos a mano.
        db.add(models.Usuario(nombre="Laura Gomez (Gestora)", rol=models.Rol.GESTOR))
        db.add(models.Usuario(nombre="Admin Sistema", rol=models.Rol.ADMINISTRADOR))
        for nombre_area, area in area_objs.items():
            db.add(models.Usuario(
                nombre=f"Responsable {nombre_area}",
                rol=models.Rol.AREA_TECNICA,
                area_id=area.id,
            ))
        db.add(models.Usuario(nombre="Juan Perez (Peticionario de prueba)", rol=models.Rol.PETICIONARIO))

        db.commit()
        print("Datos iniciales creados: 4 areas tecnicas, reglas de asignacion y usuarios de prueba.")
    finally:
        db.close()


@app.get("/")
def raiz():
    return {
        "mensaje": "Sistema de Trazabilidad PUZV - INVIAS",
        "documentacion": "/docs",
    }

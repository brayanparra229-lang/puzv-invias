"""
RF-001: Iniciar sesion segun el rol (simulado: no hay password, se elige
         un usuario existente de una lista).
RF-002: Cerrar sesion.

Como el login es simulado, no manejamos tokens ni contrasenas. El
"login" es simplemente: el frontend pide la lista de usuarios de
prueba, el usuario elige uno, y a partir de ahi el frontend recuerda
ese usuario (su id y su rol) para saber que pantallas mostrar y que
mandar en cada peticion.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/auth", tags=["Autenticacion (RF-001, RF-002)"])


@router.get("/usuarios", response_model=List[schemas.UsuarioOut])
def listar_usuarios_para_login(db: Session = Depends(get_db)):
    """
    Devuelve los usuarios de prueba disponibles para 'iniciar sesion'.
    El frontend usa esta lista para mostrar la pantalla de seleccion de
    rol/usuario (RF-001).
    """
    return db.query(models.Usuario).filter(models.Usuario.activo == True).all()


@router.post("/login/{usuario_id}", response_model=schemas.UsuarioOut)
def iniciar_sesion(usuario_id: int, db: Session = Depends(get_db)):
    """
    'Inicia sesion' simplemente confirmando que el usuario existe y esta
    activo, y devolviendo sus datos (incluido el rol) para que el
    frontend sepa que mostrar.
    """
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    return usuario


@router.post("/logout")
def cerrar_sesion():
    """
    RF-002. Como no hay sesion real guardada en el servidor (el login es
    simulado), cerrar sesion es responsabilidad del frontend: simplemente
    olvida el usuario que tenia guardado y vuelve a la pantalla de
    seleccion de rol. Este endpoint existe para que ese flujo quede
    explicito y documentado.
    """
    return {"mensaje": "Sesion cerrada"}

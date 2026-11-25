"""
Conexion a la base de datos.

Para el desarrollo local usamos SQLite (un solo archivo, sin instalar nada).
Cuando se despliegue la demo final en un servicio como Render, basta con
cambiar DATABASE_URL por la cadena de conexion de PostgreSQL; el resto del
codigo (modelos, routers) no necesita cambiar porque SQLAlchemy habla con
ambos motores de la misma forma.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# --- SQLite (desarrollo local) ---
DATABASE_URL = "sqlite:///./puzv.db"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # solo necesario para SQLite
)

# --- PostgreSQL (para cuando despleguemos) ---
# DATABASE_URL = "postgresql://usuario:password@host:5432/puzv_db"
# engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependencia de FastAPI: entrega una sesion de base de datos a cada
    endpoint y la cierra automaticamente cuando termina la peticion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

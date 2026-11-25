"""
Utilidades compartidas.

Usamos la hora de Colombia (America/Bogota) en toda la aplicacion, en
vez de UTC, para que las fechas que ve el usuario en pantalla
coincidan con su reloj. Para un prototipo de un solo pais esto es mas
simple que guardar en UTC y convertir cada vez que se muestra algo.
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ZONA_COLOMBIA = ZoneInfo("America/Bogota")

# Carpeta donde se guardan los documentos que suben los peticionarios.
# Queda en la raiz del proyecto: puzv-invias/uploads/
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"


def ahora_colombia() -> datetime:
    """Fecha y hora actual en Colombia, sin informacion de zona horaria
    adjunta (naive) para que se pueda guardar y comparar facilmente en
    SQLite."""
    return datetime.now(ZONA_COLOMBIA).replace(tzinfo=None)

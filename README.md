# Sistema de Trazabilidad y Coordinación — Trámite PUZV (INVÍAS)

Prototipo web desarrollado como trabajo de grado en **Ingeniería de Sistemas** (Institución Universitaria Politécnico Grancolombiano) para mejorar el seguimiento interno y el control de tiempos límite (SLA) del **Permiso de Uso de Zona de Vía (PUZV)** en el Instituto Nacional de Vías (INVÍAS).

- **Autor:** Brayan Parra
- **Asesor:** Luis Fernando Quiroga Peláez
- **Alcance:** Prueba de concepto local con datos simulados (17 requisitos implementados: RF-001 a RF-016 y RF-021).

---

## Funcionalidades principales

- **Radicación y enrutamiento automático:** Genera un radicado único (`PUZV-AAAA-NNNN`) y asigna automáticamente la solicitud según el tipo de intervención a una de las cuatro áreas técnicas delimitadas:
  - **Hidráulica** (SLA: 6 días) — Cruce de redes, Obra de drenaje.
  - **Pavimentos** (SLA: 5 días) — Reparcheo / pavimento.
  - **Geotécnica** (SLA: 5 días) — Excavación.
  - **Diseño Geométrico** (SLA: 4 días) — Acceso vehicular.
- **Máquina de estados finitos:** Controla transiciones válidas (`radicada` → `concepto_pendiente` → `aprobada`, `rechazada` o `subsanacion`).
- **Auditoría inmutable en hora de Colombia:** Registra cada cambio de estado usando `America/Bogota` sin rutas de edición ni borrado.
- **Gestión documental (RF-021):** Carga y descarga de soportes (máx. 10 MB, 10 extensiones permitidas) almacenados con identificador único UUID; bloquea nuevas cargas en estados cerrados.
- **Alertas de SLA e indicadores:** Detecta expedientes vencidos sin duplicar alertas y muestra gráficas de tiempo promedio de respuesta y solicitudes vencidas por área.

---

## Tecnologías utilizadas

- **Backend:** Python 3.11.9, FastAPI 0.115.0, Uvicorn 0.30.6, Pydantic 2.9.2, python-multipart 0.0.12
- **Persistencia:** SQLAlchemy 2.0.35 sobre SQLite (`puzv.db`)
- **Frontend:** Streamlit 1.39.0, Requests 2.32.3

---

## Instalación y ejecución local

### 1. Clonar el repositorio e instalar dependencias
```bash
git clone [https://github.com/brayanparra229-lang/puzv-invias.git](https://github.com/brayanparra229-lang/puzv-invias.git)
cd puzv-invias
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Iniciar el backend (Terminal 1)
```bash
uvicorn app.main:app --reload
```
Al arrancar, el sistema crea automáticamente `puzv.db`, la carpeta `uploads/` y precarga las 4 áreas técnicas, 5 reglas de enrutamiento y 7 usuarios de prueba.
- Documentación interactiva Swagger: `http://127.0.0.1:8000/docs`

### 3. Iniciar la interfaz web (Terminal 2)
Con el entorno virtual activo, ejecuta:
```bash
streamlit run frontend/streamlit_app.py
```
La aplicación quedará disponible en `http://localhost:8501`.

---

## Estructura del proyecto

```text
puzv-invias/
├── app/
│   ├── main.py              # Configuración FastAPI, CORS y precarga de datos
│   ├── database.py          # Conexión SQLAlchemy / SQLite
│   ├── models.py            # Modelos ORM (8 tablas relacionales)
│   ├── schemas.py           # Validación de esquemas con Pydantic
│   ├── state_machine.py     # Reglas de transición de estados
│   ├── utils.py             # Zona horaria Colombia y directorio uploads/
│   └── routers/             # Endpoints REST (auth, solicitudes, adjuntos, conceptos, alertas, indicadores)
├── frontend/
│   └── streamlit_app.py     # Interfaz web por roles (Peticionario, Área Técnica, Gestor, Administrador)
├── requirements.txt
└── .gitignore
```

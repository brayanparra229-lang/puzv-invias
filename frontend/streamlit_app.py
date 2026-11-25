"""
Frontend del Sistema de Trazabilidad PUZV - INVIAS.

Esta app solo CONSUME la API de FastAPI (que debe estar corriendo por
separado en http://127.0.0.1:8000). No tiene logica de negocio propia:
toda la logica (validaciones, asignacion automatica, maquina de estados,
SLA) vive en el backend; aqui solo mostramos pantallas y mandamos
peticiones.

Para correrla (en una SEGUNDA terminal, con el backend ya corriendo en
la primera):
    streamlit run frontend/streamlit_app.py
"""

from datetime import datetime

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

EXTENSIONES_PERMITIDAS = ["pdf", "png", "jpg", "jpeg", "doc", "docx", "xls", "xlsx", "dwg", "zip"]
TAMANO_MAXIMO_MB = 10
ESTADOS_CERRADOS = ["aprobada", "rechazada"]

# Nombres amigables de los campos, para los mensajes de error
NOMBRES_CAMPOS = {
    "peticionario_nombre": "Nombre completo",
    "peticionario_documento": "Número de documento",
    "peticionario_correo": "Correo electrónico",
    "tipo_intervencion": "Tipo de intervención",
}

st.set_page_config(page_title="PUZV - INVIAS", page_icon="🛣️", layout="wide")


# ---------------------------------------------------------------------
# Utilidades de presentación
# ---------------------------------------------------------------------

def formatear_fecha(iso):
    """'2026-10-09T14:35:00' -> '09/10/2026 02:35 PM'"""
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %I:%M %p")
    except (ValueError, TypeError):
        return iso or "—"


def estado_legible(estado):
    """'concepto_pendiente' -> 'Concepto Pendiente'"""
    return estado.replace("_", " ").title()


def mensaje_error(resp):
    """Convierte la respuesta de error del backend en un texto que un
    usuario normal entienda (en vez de mostrar el JSON tecnico)."""
    try:
        detalle = resp.json().get("detail", resp.text)
    except ValueError:
        return resp.text
    if isinstance(detalle, list):  # errores de validacion de campos
        campos = []
        for e in detalle:
            clave = str(e.get("loc", [""])[-1])
            campos.append(f"«{NOMBRES_CAMPOS.get(clave, clave)}»")
        return "Revisa estos campos, están vacíos o no son válidos: " + ", ".join(campos)
    return str(detalle)


def archivos_invalidos(archivos):
    """Revisa el tamaño ANTES de mandar nada al backend. Devuelve un
    mensaje de error o None si todo esta bien."""
    limite = TAMANO_MAXIMO_MB * 1024 * 1024
    for a in archivos:
        if len(a.getvalue()) > limite:
            return f"El archivo «{a.name}» supera el máximo de {TAMANO_MAXIMO_MB} MB."
    return None


def subir_archivos(numero_radicado, archivos):
    files = [
        ("archivos", (a.name, a.getvalue(), a.type or "application/octet-stream"))
        for a in archivos
    ]
    return requests.post(f"{API_URL}/solicitudes/{numero_radicado}/adjuntos", files=files)


def mostrar_adjuntos(numero_radicado, adjuntos, clave):
    """Lista los documentos de una solicitud, cada uno con su boton de descarga."""
    if not adjuntos:
        st.caption("Esta solicitud no tiene documentos adjuntos.")
        return
    for a in adjuntos:
        resp = requests.get(f"{API_URL}/solicitudes/{numero_radicado}/adjuntos/{a['id']}")
        if resp.status_code == 200:
            kb = a["tamano_bytes"] / 1024
            st.download_button(
                f"📎 {a['nombre_original']}  ({kb:,.0f} KB · subido {formatear_fecha(a['fecha_subida'])})",
                data=resp.content,
                file_name=a["nombre_original"],
                key=f"descarga_{clave}_{a['id']}",
            )
        else:
            st.caption(f"⚠️ No se pudo cargar «{a['nombre_original']}».")


def mostrar_flash():
    """Mensaje que sobrevive a un st.rerun() (ej. 'documentos subidos')."""
    flash = st.session_state.pop("flash", None)
    if flash:
        tipo, texto = flash
        (st.success if tipo == "success" else st.error)(texto)


# ---------------------------------------------------------------------
# Login simulado (RF-001, RF-002)
# ---------------------------------------------------------------------

def pantalla_login():
    st.title("🛣️ Sistema de Trazabilidad PUZV - INVIAS")
    st.caption("Prototipo de trabajo de grado — login simulado para la demo")

    try:
        usuarios = requests.get(f"{API_URL}/auth/usuarios").json()
    except requests.exceptions.ConnectionError:
        st.error(
            "No se pudo conectar con el backend. Verifica que esté corriendo "
            "`uvicorn app.main:app --reload` en otra terminal."
        )
        return

    st.subheader("Selecciona con qué usuario quieres entrar")
    opciones = {f"{u['nombre']}  —  ({u['rol']})": u for u in usuarios}
    seleccion = st.selectbox("Usuario", list(opciones.keys()))

    if st.button("Iniciar sesión", type="primary"):
        st.session_state["usuario"] = opciones[seleccion]
        st.rerun()


def cerrar_sesion():
    """RF-002: simplemente olvidamos el usuario guardado en la sesión."""
    st.session_state.clear()
    st.rerun()


# ---------------------------------------------------------------------
# Peticionario (RF-003 a RF-009, RF-021)
# ---------------------------------------------------------------------

def vista_peticionario(usuario):
    st.header("Radicar y consultar solicitudes PUZV")
    mostrar_flash()

    tab_radicar, tab_consultar = st.tabs(["📝 Radicar nueva solicitud", "🔍 Consultar estado"])

    # ---------------- Radicar ----------------
    with tab_radicar:
        with st.form("form_radicar"):
            nombre = st.text_input("Nombre completo")
            documento = st.text_input("Número de documento")
            correo = st.text_input("Correo electrónico")
            tipo = st.selectbox(
                "Tipo de intervención",
                ["Cruce de redes", "Acceso vehicular", "Obra de drenaje", "Excavacion", "Reparcheo / pavimento"],
            )
            descripcion = st.text_area("Descripción de la intervención")
            archivos = st.file_uploader(
                f"Documentos de soporte (obligatorio, mínimo 1 archivo, máx. {TAMANO_MAXIMO_MB} MB cada uno)",
                type=EXTENSIONES_PERMITIDAS,
                accept_multiple_files=True,
                help="Planos, formatos diligenciados, cartas, etc. "
                     f"Tipos permitidos: {', '.join(EXTENSIONES_PERMITIDAS)}",
            )
            enviado = st.form_submit_button("Enviar solicitud", type="primary")

        if enviado:
            if not archivos:
                st.error("Debes adjuntar al menos un documento de soporte para radicar la solicitud.")
            elif archivos_invalidos(archivos):
                st.error(archivos_invalidos(archivos))
            else:
                resp = requests.post(
                    f"{API_URL}/solicitudes/",
                    json={
                        "peticionario_nombre": nombre,
                        "peticionario_documento": documento,
                        "peticionario_correo": correo,
                        "tipo_intervencion": tipo,
                        "descripcion": descripcion,
                    },
                )
                if resp.status_code == 201:
                    data = resp.json()
                    resp_docs = subir_archivos(data["numero_radicado"], archivos)
                    if resp_docs.status_code == 201:
                        st.success(
                            f"✅ Solicitud radicada con éxito, con {len(archivos)} documento(s) adjunto(s). "
                            f"Tu número de radicado es **{data['numero_radicado']}** — guárdalo para hacerle seguimiento."
                        )
                    else:
                        st.warning(
                            f"La solicitud quedó radicada con el número **{data['numero_radicado']}**, "
                            f"pero los documentos no se pudieron subir: {mensaje_error(resp_docs)} "
                            "Puedes volver a adjuntarlos desde la pestaña «Consultar estado»."
                        )
                else:
                    st.error(f"No se pudo radicar la solicitud. {mensaje_error(resp)}")

    # ---------------- Consultar ----------------
    with tab_consultar:
        numero = st.text_input("Número de radicado", placeholder="PUZV-2026-0001")
        if st.button("Consultar"):
            st.session_state["radicado_consultado"] = numero.strip()

        radicado = st.session_state.get("radicado_consultado")
        if radicado:
            resp = requests.get(f"{API_URL}/solicitudes/{radicado}")
            if resp.status_code == 200:
                s = resp.json()
                mostrar_detalle_solicitud(s)

                st.subheader("Documentos adjuntos")
                mostrar_adjuntos(s["numero_radicado"], s.get("adjuntos", []), "peticionario")

                if s["estado"] not in ESTADOS_CERRADOS:
                    with st.form("form_mas_documentos", clear_on_submit=True):
                        nuevos = st.file_uploader(
                            "Agregar más documentos a esta solicitud",
                            type=EXTENSIONES_PERMITIDAS,
                            accept_multiple_files=True,
                        )
                        subir = st.form_submit_button("Subir documentos")
                    if subir:
                        if not nuevos:
                            st.error("Selecciona al menos un archivo para subir.")
                        elif archivos_invalidos(nuevos):
                            st.error(archivos_invalidos(nuevos))
                        else:
                            r = subir_archivos(s["numero_radicado"], nuevos)
                            if r.status_code == 201:
                                st.session_state["flash"] = ("success", f"Se subieron {len(nuevos)} documento(s).")
                            else:
                                st.session_state["flash"] = ("error", mensaje_error(r))
                            st.rerun()
            else:
                st.error("No se encontró una solicitud con ese número de radicado.")


def mostrar_detalle_solicitud(s):
    col1, col2, col3 = st.columns(3)
    col1.metric("Estado actual", estado_legible(s["estado"]))
    col2.metric("Área asignada", s["area"]["nombre"] if s.get("area") else "Sin asignar")
    col3.metric("Radicada el", formatear_fecha(s["fecha_radicacion"]))

    st.write(f"**Peticionario:** {s['peticionario_nombre']}")
    st.write(f"**Tipo de intervención:** {s['tipo_intervencion']}")

    st.subheader("Línea de tiempo")
    for cambio in s.get("cambios_estado", []):
        st.write(
            f"🔹 **{formatear_fecha(cambio['fecha'])}** — "
            f"{estado_legible(cambio['estado_nuevo'])}  ·  _{cambio['usuario']}_"
        )
        if cambio.get("comentario"):
            st.caption(cambio["comentario"])


# ---------------------------------------------------------------------
# Área técnica (RF-011, RF-012)
# ---------------------------------------------------------------------

def vista_area_tecnica(usuario):
    st.header("Solicitudes pendientes de concepto en tu área")
    mostrar_flash()

    todas = requests.get(f"{API_URL}/solicitudes/").json()
    pendientes = [
        s for s in todas
        if s.get("area") and s["area"]["id"] == usuario["area_id"]
        and s["estado"] == "concepto_pendiente"
    ]

    if not pendientes:
        st.info("No tienes solicitudes pendientes de concepto en este momento.")
        return

    for s in pendientes:
        numero = s["numero_radicado"]
        with st.expander(f"{numero} — {s['tipo_intervencion']} ({s['peticionario_nombre']})"):
            st.write(f"**Radicada el:** {formatear_fecha(s['fecha_radicacion'])}")
            st.write(f"**Descripción:** {s.get('descripcion') or '—'}")

            st.markdown("**Documentos del peticionario**")
            detalle = requests.get(f"{API_URL}/solicitudes/{numero}").json()
            mostrar_adjuntos(numero, detalle.get("adjuntos", []), f"area_{numero}")

            with st.form(f"concepto_{numero}"):
                tipo_concepto = st.radio(
                    "Concepto",
                    ["aprobado", "rechazado", "requiere_subsanacion"],
                    horizontal=True,
                    key=f"radio_{numero}",
                )
                observacion = st.text_area("Observación", key=f"obs_{numero}")
                enviar = st.form_submit_button("Registrar concepto")

            if enviar:
                resp = requests.post(
                    f"{API_URL}/solicitudes/{numero}/concepto",
                    json={"tipo": tipo_concepto, "observacion": observacion, "usuario": usuario["nombre"]},
                )
                if resp.status_code == 200:
                    st.session_state["flash"] = ("success", f"Concepto registrado en {numero}. La solicitud cambió de estado.")
                    st.rerun()
                else:
                    st.error(mensaje_error(resp))


# ---------------------------------------------------------------------
# Gestor (vista general de todas las solicitudes)
# ---------------------------------------------------------------------

def vista_gestor(usuario):
    st.header("Todas las solicitudes")
    todas = requests.get(f"{API_URL}/solicitudes/").json()
    if not todas:
        st.info("Todavía no hay solicitudes radicadas.")
        return

    filas = [
        {
            "Radicado": s["numero_radicado"],
            "Radicada el": formatear_fecha(s["fecha_radicacion"]),
            "Peticionario": s["peticionario_nombre"],
            "Tipo de intervención": s["tipo_intervencion"],
            "Área": s["area"]["nombre"] if s.get("area") else "Sin asignar",
            "Estado": estado_legible(s["estado"]),
        }
        for s in todas
    ]
    st.dataframe(filas, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------
# Administrador (RF-013 a RF-016: panel de control y alertas)
# ---------------------------------------------------------------------

def vista_administrador(usuario):
    st.header("Panel de control")

    if st.button("🔔 Revisar alertas de SLA ahora"):
        nuevas = requests.post(f"{API_URL}/alertas/revisar").json()
        st.success(f"Revisión completada. Se generaron {len(nuevas)} alerta(s) nueva(s).")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⏱️ Tiempo promedio de respuesta por área")
        tiempos = requests.get(f"{API_URL}/indicadores/tiempo-promedio-por-area").json()
        if tiempos:
            st.bar_chart({t["area"]: t["tiempo_promedio_dias"] for t in tiempos})
        else:
            st.caption("Todavía no hay conceptos registrados para calcular este indicador.")

    with col2:
        st.subheader("⚠️ Solicitudes vencidas por área")
        vencidas = requests.get(f"{API_URL}/indicadores/vencidas-por-area").json()
        st.bar_chart({v["area"]: v["solicitudes_vencidas"] for v in vencidas})

    st.subheader("Alertas sin atender")
    alertas = requests.get(f"{API_URL}/alertas/").json()
    if not alertas:
        st.caption("No hay alertas pendientes por atender.")
    for a in alertas:
        st.write(
            f"🔴 Solicitud #{a['solicitud_id']} — {a['dias_transcurridos']} días transcurridos "
            f"(alerta generada el {formatear_fecha(a['fecha_generada'])})"
        )


# ---------------------------------------------------------------------
# Enrutamiento principal según el rol
# ---------------------------------------------------------------------

def main():
    if "usuario" not in st.session_state:
        pantalla_login()
        return

    usuario = st.session_state["usuario"]

    with st.sidebar:
        st.write(f"👤 **{usuario['nombre']}**")
        st.caption(f"Rol: {usuario['rol']}")
        if st.button("Cerrar sesión"):
            cerrar_sesion()

    rol = usuario["rol"]
    if rol == "peticionario":
        vista_peticionario(usuario)
    elif rol == "area_tecnica":
        vista_area_tecnica(usuario)
    elif rol == "gestor":
        vista_gestor(usuario)
    elif rol == "administrador":
        vista_administrador(usuario)


if __name__ == "__main__":
    main()

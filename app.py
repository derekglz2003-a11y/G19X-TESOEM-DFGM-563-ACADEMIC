from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

from servicios.api import api_get, api_estado
from servicios.seguridad import acceso_configurado, verificar_contrasena
from servicios.login_roles import mostrar_login_roles, mostrar_portal_candidato
from servicios.estilos import aplicar_estilos, aplicar_fondo
from servicios.barra_admin import aplicar_barra_admin, dibujar_marca_admin, cerrar_sesion_admin
from paginas import inicio, vacantes, candidatos, radar, entrevistas, finalistas, configuracion

load_dotenv()
st.set_page_config(
    page_title="CurriculAi | Gestión inteligente de talento",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

aplicar_estilos()
aplicar_fondo()
aplicar_barra_admin()

SECCIONES = ["Inicio", "Vacantes", "Candidatos", "Radar de talentos", "Entrevistas", "Finalistas", "Configuración"]
PANTALLAS = {
    "Inicio": inicio.render,
    "Vacantes": vacantes.render,
    "Candidatos": candidatos.render,
    "Radar de talentos": radar.render,
    "Entrevistas": entrevistas.render,
    "Finalistas": finalistas.render,
    "Configuración": configuracion.render,
}


def cambiar_seccion(destino):
    if destino in SECCIONES:
        st.session_state["cai_menu_pendiente"] = destino
        st.rerun()


def limpiar_sesion_visual():
    """Reinicia filtros y la navegación sin alterar un widget ya creado.

    Los registros permanecen en la base de datos. La selección del menú se
    actualiza en la siguiente ejecución, ANTES de instanciar st.radio.
    """
    for key in list(st.session_state.keys()):
        if key not in ("menu_principal", "cai_autenticado"):
            del st.session_state[key]
    st.session_state["cai_menu_pendiente"] = "Inicio"
    st.rerun()


def buscar_logo():
    raiz = Path(__file__).resolve().parent
    for nombre in ("logo.png", "logo.jpg", "logo.jpeg", "logo.webp", "curriculai_logo.png", "curriculai.png", "logo_curriculai.png"):
        archivo = raiz / nombre
        if archivo.is_file():
            return archivo
    return None


if "cai_menu_pendiente" in st.session_state:
    st.session_state["menu_principal"] = st.session_state.pop("cai_menu_pendiente")
if "menu_principal" not in st.session_state or st.session_state["menu_principal"] not in SECCIONES:
    st.session_state["menu_principal"] = "Inicio"

def cerrar_sesion():
    # No modificar el widget st.radio una vez instanciado en esta ejecución.
    for key in list(st.session_state.keys()):
        if key != "menu_principal":
            del st.session_state[key]
    st.session_state["cai_menu_pendiente"] = "Inicio"
    st.rerun()


# Acceso aislado por roles. Nunca se consulta la API de administración
# mientras la sesión sea de un candidato.
if st.session_state.get("cai_autenticado") and st.session_state.get("cai_usuario_rol") not in ("administrador", "candidato"):
    st.session_state["cai_autenticado"] = False  # sesión previa a la separación de roles

if not st.session_state.get("cai_autenticado", False):
    mostrar_login_roles(Path(__file__).resolve().parent)
    st.stop()

if st.session_state.get("cai_usuario_rol") == "candidato":
    mostrar_portal_candidato()
    st.stop()

if not acceso_configurado():
    st.error("Acceso de administrador sin configurar. Revisa .env y reinicia el sistema.")
    st.stop()

codigo_estado = api_estado()
conectada = codigo_estado == 200

with st.container(key="cai_topbar"):
    marca, nav, acciones = st.columns([2.15, 7.35, 1.30], vertical_alignment="center", gap="small")
    with marca:
        dibujar_marca_admin(buscar_logo())
    with nav:
        # Botones con apariencia de texto: ningún radio ni círculo de selección.
        columnas_menu = st.columns([0.75, 1.05, 1.24, 1.93, 1.37, 1.08, 1.60], gap="small")
        for indice, (columna, nombre) in enumerate(zip(columnas_menu, SECCIONES)):
            con_estilo = "activa" if st.session_state["menu_principal"] == nombre else "normal"
            with columna:
                with st.container(key=f"cai_nav_{con_estilo}_{indice}"):
                    if st.button(nombre, key=f"cai_nav_ir_{indice}", use_container_width=True):
                        cambiar_seccion(nombre)
        seccion = st.session_state["menu_principal"]
    with acciones:
        # El callback se ejecuta ANTES del rerun: el acceso se cierra realmente.
        st.button("Cerrar sesión", key="cai_admin_cerrar_sesion", use_container_width=True,
                  on_click=cerrar_sesion_admin)
        status_class = "ok" if conectada else "error"
        status_text = "● Conectado" if conectada else "● Sin conexión"
        st.markdown(
            f'<div class="cai-top-actions"><span class="cai-status {status_class}">{status_text}</span></div>',
            unsafe_allow_html=True,
        )

st.markdown('<div class="cai-top-divider"></div>', unsafe_allow_html=True)
if not conectada:
    if codigo_estado == 401:
        st.error("El backend rechazó la clave API. Revisa ADMIN_API_KEY y reinicia los dos procesos.")
    elif codigo_estado == 503:
        st.error("La clave del administrador no está configurada en FastAPI.")
    else:
        st.warning("El backend no responde. Revisa FastAPI y API_URL.")

ctx = {
    "candidatos": api_get("/api/v1/candidatos", []),
    "vacantes": api_get("/api/v1/vacantes", []),
    "entrevistas": api_get("/api/v1/entrevistas", []),
    "mensajes_whatsapp": api_get("/api/v1/mensajes-whatsapp", []),
    "api_conectada": conectada,
    "navegar": cambiar_seccion,
    "reiniciar_vista": limpiar_sesion_visual,
    "cerrar_sesion": cerrar_sesion,
}
for clave in ("candidatos", "vacantes", "entrevistas", "mensajes_whatsapp"):
    if not isinstance(ctx[clave], list):
        ctx[clave] = []

PANTALLAS[seccion](ctx)

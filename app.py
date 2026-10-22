from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

from servicios.api import api_get, api_estado
from servicios.seguridad import acceso_configurado, verificar_contrasena
from servicios.estilos import aplicar_estilos, aplicar_fondo
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


# No mostrar ni consultar expedientes antes de autenticar al administrador.
if not acceso_configurado():
    st.error("Falta configurar el acceso administrativo de CurriculAi.")
    st.info("En la carpeta del proyecto ejecuta: python scripts/configurar_acceso.py. Después reinicia FastAPI y Streamlit.")
    st.stop()

if not st.session_state.get("cai_autenticado", False):
    st.markdown('<div style="max-width:500px;margin:38px auto 12px;text-align:center"><h1>CurriculAi</h1><p>Acceso administrativo · Gestión de talento</p></div>', unsafe_allow_html=True)
    with st.form("cai_form_login"):
        contrasena = st.text_input("Contraseña de administrador", type="password")
        entrar = st.form_submit_button("Entrar a CurriculAi", type="primary", use_container_width=True)
    if entrar:
        if verificar_contrasena(contrasena):
            st.session_state["cai_autenticado"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()

codigo_estado = api_estado()
conectada = codigo_estado == 200

with st.container(key="cai_topbar"):
    marca, nav, acciones = st.columns([1.6, 7.4, 0.8], vertical_alignment="center", gap="small")
    with marca:
        logo_cols = st.columns([0.47, 1.1], gap="small", vertical_alignment="center")
        with logo_cols[0]:
            archivo_logo = buscar_logo()
            if archivo_logo:
                st.image(str(archivo_logo), width=54)
            else:
                st.markdown('<div style="width:54px;height:54px;border-radius:10px;background:white;display:flex;align-items:center;justify-content:center;color:#173a62;font-weight:800;font-size:1.4rem;">CA</div>', unsafe_allow_html=True)
        with logo_cols[1]:
            st.markdown('<div class="cai-brand-wrap"><div><div class="cai-brand-title">CurriculAi</div><div class="cai-brand-sub">Talent intelligence</div></div></div>', unsafe_allow_html=True)
    with nav:
        seccion = st.radio("Navegación principal", SECCIONES, horizontal=True, key="menu_principal", label_visibility="collapsed")
    with acciones:
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

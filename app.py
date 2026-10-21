from pathlib import Path
import requests
import streamlit as st
from dotenv import load_dotenv

from servicios.api import API_URL, api_get
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
        if key != "menu_principal":
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

try:
    conectada = requests.get(API_URL + "/openapi.json", timeout=2).ok
except requests.RequestException:
    conectada = False

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
    st.warning("El backend no responde. Los registros podrían no estar disponibles. Verifica FastAPI y API_URL.")

ctx = {
    "candidatos": api_get("/api/v1/candidatos", []),
    "vacantes": api_get("/api/v1/vacantes", []),
    "entrevistas": api_get("/api/v1/entrevistas", []),
    "mensajes_whatsapp": api_get("/api/v1/mensajes-whatsapp", []),
    "api_conectada": conectada,
    "navegar": cambiar_seccion,
    "reiniciar_vista": limpiar_sesion_visual,
}
for clave in ("candidatos", "vacantes", "entrevistas", "mensajes_whatsapp"):
    if not isinstance(ctx[clave], list):
        ctx[clave] = []

PANTALLAS[seccion](ctx)

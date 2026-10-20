import os
import requests
import streamlit as st
from dotenv import load_dotenv
from servicios.api import API_URL, api_get
from servicios.estilos import aplicar_estilos, aplicar_fondo
from paginas import inicio, candidatos, vacantes, radar, entrevistas, finalistas, configuracion

load_dotenv()
st.set_page_config(
    page_title="CurriculAI | Filtrado inteligente de talento",
    page_icon="🤖", layout="wide", initial_sidebar_state="expanded"
)
aplicar_estilos()
aplicar_fondo()

datos = {
    "candidatos": api_get("/api/v1/candidatos", []),
    "vacantes": api_get("/api/v1/vacantes", []),
    "entrevistas": api_get("/api/v1/entrevistas", []),
}
for clave in datos:
    if not isinstance(datos[clave], list):
        datos[clave] = []

def obtener_logo_path():
    """Encuentra el archivo del logo original sin inyectar HTML en el sidebar."""
    nombres = ["logo.png", "logo.jpg", "logo.jpeg", "logo.webp", "curriculai_logo.png", "curriculai.png", "logo_curriculai.png"]
    for nombre in nombres:
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre)
        if os.path.isfile(ruta):
            return ruta
    return None

with st.sidebar:
    st.markdown('<div class="brand">', unsafe_allow_html=True)
    logo_path = obtener_logo_path()
    if logo_path:
        _, centro, _ = st.columns([1, 2, 1])
        with centro:
            st.image(logo_path, width=112)
    else:
        st.markdown("<div class='brand-icon'>C</div>", unsafe_allow_html=True)

    st.markdown("<div class='brand-name'>CurriculAI</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='brand-tagline'>Optimizador de Filtrado Curricular mediante Inteligencia Artificial</div></div>",
        unsafe_allow_html=True,
    )

    menu = st.radio(
        "Navegación",
        [
            "🏠  Inicio",
            "👥  Candidatos",
            "💼  Vacantes",
            "📊  Radar de talentos",
            "📅  Entrevistas",
            "⭐  Finalistas",
            "⚙️  Configuración",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    try:
        _api_respuesta = requests.get(API_URL.rstrip("/") + "/openapi.json", timeout=2)
        _api_conectada = _api_respuesta.ok
    except requests.RequestException:
        _api_conectada = False
    st.caption("🟢 Sistema conectado" if _api_conectada else "🔴 API sin conexión")
    st.caption("CurriculAI · v2.2")

pantallas = {
    "🏠  Inicio": inicio.render,
    "👥  Candidatos": candidatos.render,
    "💼  Vacantes": vacantes.render,
    "📊  Radar de talentos": radar.render,
    "📅  Entrevistas": entrevistas.render,
    "⭐  Finalistas": finalistas.render,
    "⚙️  Configuración": configuracion.render,
}
pantallas[menu](datos)

# -----------------------------
# ESTADO DE ACCIONES RÁPIDAS
# -----------------------------
# Se muestran en Inicio mediante botones; estas banderas permiten
# conservar la intención sin crear una segunda navegación visual.
if st.session_state.get("go_upload"):
    st.session_state["go_upload"] = False
    st.info("Para cargar CVs, entra a **Candidatos** desde el menú lateral.")

if st.session_state.get("go_vacante"):
    st.session_state["go_vacante"] = False
    st.info("Para crear una vacante, entra a **Vacantes** desde el menú lateral.")

if st.session_state.get("go_ranking"):
    st.session_state["go_ranking"] = False
    st.info("El ranking se encuentra en **Radar de talentos**.")

if st.session_state.get("go_interview"):
    st.session_state["go_interview"] = False
    st.info("La agenda se encuentra en **Entrevistas**.")

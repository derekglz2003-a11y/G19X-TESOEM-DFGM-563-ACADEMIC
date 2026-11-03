"""Navegación fija del portal del candidato.

No utiliza ni modifica la barra del administrador, ni sus credenciales.
El contenido laboral sigue dentro de portal_expediente_ui.py.
"""
from __future__ import annotations

import base64
from html import escape
import mimetypes
from pathlib import Path
from typing import Callable

import streamlit as st


SECCIONES = (
    'Inicio', 'Mi perfil', 'Mi CV', 'Vacantes',
    'Mis postulaciones', 'Mis entrevistas', 'Notificaciones',
)

# Todos los estilos se limitan a la barra del portal candidato.
CSS_BARRA_CANDIDATO = r'''
<style>
body:has([class*="st-key-cai_candidate_topbar"]) header[data-testid="stHeader"],
body:has([class*="st-key-cai_candidate_topbar"]) [data-testid="stToolbar"],
body:has([class*="st-key-cai_candidate_topbar"]) [data-testid="stDecoration"] {
    visibility: hidden !important;
    pointer-events: none !important;
}
body:has([class*="st-key-cai_candidate_topbar"]) [data-testid="stMainBlockContainer"] {
    padding-top: 125px !important;
}
[class*="st-key-cai_candidate_topbar"] {
    position: fixed !important;
    inset: 0 0 auto 0 !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    width: 100vw !important;
    max-width: none !important;
    margin: 0 !important;
    padding: 12px clamp(15px, 1.7vw, 32px) !important;
    min-height: 105px !important;
    box-sizing: border-box !important;
    background: #f9fbfd !important;
    border: 0 !important;
    border-bottom: 1px solid #d4dfeb !important;
    border-radius: 0 0 12px 12px !important;
    box-shadow: 0 5px 14px rgba(18, 50, 83, .09) !important;
    z-index: 100001 !important;
}
[class*="st-key-cai_candidate_topbar"] [data-testid="stHorizontalBlock"] {
    gap: .35rem !important;
    align-items: center !important;
}
.cai-candidate-brand {
    display: flex;
    align-items: center;
    gap: 14px;
    white-space: nowrap;
    min-width: 0;
}
.cai-candidate-logo {
    width: 69px;
    height: 69px;
    object-fit: contain;
    flex-shrink: 0;
    padding: 5px;
    background: #fff;
    border: 1px solid #dce6ed;
    border-radius: 13px;
    box-sizing: border-box;
}
.cai-candidate-logo-alt {
    display: grid;
    place-items: center;
    font-size: 26px;
    font-weight: 900;
    color: #173a62;
}
.cai-candidate-brand-title {
    color: #173a62 !important;
    font-size: clamp(1.45rem, 1.7vw, 2.05rem);
    font-weight: 850;
    line-height: 1.15;
    letter-spacing: -.035em;
}
[class*="st-key-cai_candidate_topbar"] [class*="st-key-cai_candidate_nav_"] button {
    background: transparent !important;
    border: 0 !important;
    border-bottom: 3px solid transparent !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 10px 1px 7px !important;
    min-height: 43px !important;
    height: 43px !important;
    width: 100% !important;
    color: #1c4067 !important;
    font-size: clamp(.69rem, .77vw, .86rem) !important;
    font-weight: 720 !important;
    white-space: nowrap !important;
}
[class*="st-key-cai_candidate_topbar"] [class*="st-key-cai_candidate_nav_"] button p,
[class*="st-key-cai_candidate_topbar"] [class*="st-key-cai_candidate_nav_"] button span {
    color: inherit !important;
    font-size: inherit !important;
    font-weight: inherit !important;
    white-space: nowrap !important;
}
[class*="st-key-cai_candidate_topbar"] [class*="st-key-cai_candidate_nav_"] button:hover {
    color: #008be3 !important;
    background: transparent !important;
    border-bottom-color: #8fccec !important;
}
[class*="st-key-cai_candidate_topbar"] [class*="st-key-cai_candidate_nav_activa_"] button {
    color: #173a62 !important;
    border-bottom-color: #008be3 !important;
    font-weight: 850 !important;
}
[class*="st-key-cai_candidate_topbar"] [class*="st-key-cai_candidate_nav_"] button:focus-visible {
    outline: 2px solid #008be3 !important;
}
[class*="st-key-cai_candidate_topbar"] [class*="st-key-cai_candidato_salir"] button {
    background: transparent !important;
    color: #173a62 !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    min-height: 35px !important;
    height: 35px !important;
    font-weight: 800 !important;
    padding: 7px 3px !important;
    font-size: .77rem !important;
    white-space: nowrap !important;
}
[class*="st-key-cai_candidate_topbar"] [class*="st-key-cai_candidato_salir"] button p {
    color: inherit !important;
    white-space: nowrap !important;
}
[class*="st-key-cai_candidate_topbar"] [class*="st-key-cai_candidato_salir"] button:hover {
    color: #b33348 !important;
    text-decoration: underline !important;
}
.cai-candidate-chip {
    margin-top: 4px;
    text-align: right;
    color: #17634c;
    font-size: .69rem;
    font-weight: 750;
}
@media (max-width: 1320px) {
    .cai-candidate-logo {width: 59px;height: 59px;}
    .cai-candidate-brand {gap: 8px;}
    .cai-candidate-brand-title {font-size: 1.35rem;}
    [class*="st-key-cai_candidate_topbar"] [class*="st-key-cai_candidate_nav_"] button {font-size: .68rem !important;}
}
@media (max-width: 1120px) {
    body:has([class*="st-key-cai_candidate_topbar"]) [data-testid="stMainBlockContainer"] {padding-top: 220px !important;}
    [class*="st-key-cai_candidate_topbar"] [data-testid="stHorizontalBlock"] {flex-wrap: wrap !important;row-gap: 4px !important;}
    [class*="st-key-cai_candidate_topbar"] {padding: 9px 12px !important;}
}
@media (max-width: 680px) {
    body:has([class*="st-key-cai_candidate_topbar"]) [data-testid="stMainBlockContainer"] {padding-top: 330px !important;}
    [class*="st-key-cai_candidate_topbar"] [data-testid="stHorizontalBlock"] {flex-wrap: wrap !important;row-gap: 2px !important;}
    [class*="st-key-cai_candidate_topbar"] [data-testid="stHorizontalBlock"] > div {flex: 1 1 100% !important;width: 100% !important;}
    [class*="st-key-cai_candidate_topbar"] [class*="st-key-cai_candidate_nav_"] button {min-height: 31px !important;height: 31px !important;padding: 3px 4px !important;}
    .cai-candidate-logo {width: 48px;height: 48px;}
}
</style>
'''


def _marca_html() -> str:
    """Utiliza el logo ya existente sin guardarlo ni duplicarlo."""
    raiz = Path(__file__).resolve().parents[1]
    nombres = (
        'logo.png', 'logo.jpg', 'logo.jpeg', 'logo.webp',
        'curriculai_logo.png', 'curriculai.png', 'logo_curriculai.png',
    )
    img = '<span class="cai-candidate-logo cai-candidate-logo-alt">CA</span>'
    for nombre in nombres:
        ruta = raiz / nombre
        if ruta.is_file():
            tipo = mimetypes.guess_type(ruta.name)[0]
            if tipo in ('image/png', 'image/jpeg', 'image/webp'):
                contenido = base64.b64encode(ruta.read_bytes()).decode('ascii')
                img = (f'<img class="cai-candidate-logo" alt="Logo CurriculAi" '
                       f'src="data:{escape(tipo)};base64,{contenido}">')
                break
    return f'<div class="cai-candidate-brand">{img}<span class="cai-candidate-brand-title">CurriculAi</span></div>'


def mostrar_barra_candidato(nombre: str, sin_leer: int, cerrar_sesion: Callable[[], None]) -> str:
    """Dibuja la barra superior y devuelve la sección que debe mostrarse."""
    actual = st.session_state.get('cai_candidato_seccion', 'Inicio')
    if actual not in SECCIONES:
        actual = 'Inicio'
        st.session_state['cai_candidato_seccion'] = actual

    st.markdown(CSS_BARRA_CANDIDATO, unsafe_allow_html=True)
    with st.container(key='cai_candidate_topbar'):
        marca, navegacion, salida = st.columns([2.15, 7.4, 1.32], gap='small', vertical_alignment='center')
        with marca:
            st.markdown(_marca_html(), unsafe_allow_html=True)
        with navegacion:
            items = st.columns([.75, 1.05, .68, .91, 1.57, 1.27, 1.19], gap='small')
            for indice, (columna, titulo) in enumerate(zip(items, SECCIONES)):
                texto = {
                    'Mis postulaciones': 'Postulaciones',
                    'Mis entrevistas': 'Entrevistas',
                    'Notificaciones': f'Avisos ({max(0, int(sin_leer))})' if sin_leer else 'Avisos',
                }.get(titulo, titulo)
                estado = 'activa' if actual == titulo else 'normal'
                with columna:
                    with st.container(key=f'cai_candidate_nav_{estado}_{indice}'):
                        if st.button(texto, key=f'cai_candidato_nav_ir_{indice}', use_container_width=True):
                            st.session_state['cai_candidato_seccion'] = titulo
                            st.rerun()
        with salida:
            with st.container(key='cai_candidato_salir'):
                if st.button('Cerrar sesión', key='cai_candidato_cerrar_sesion', use_container_width=True):
                    st.session_state.pop('cai_candidato_seccion', None)
                    cerrar_sesion()
                    st.stop()
            st.markdown('<div class="cai-candidate-chip">● Mi cuenta</div>', unsafe_allow_html=True)
    return actual

"""Barra administrativa de CurriculAi: navegación minimalista y salida real.

Este módulo contiene exclusivamente estilos y funciones de interfaz.
No cambia las cuentas, la API ni los datos almacenados.
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import streamlit as st


CSS_BARRA_ADMIN = r"""
<style>
/* Ocultar los controles de desarrollo de Streamlit solo al abrir el panel
   de administrador. Evita que 'Deploy' se superponga a Cerrar sesión. */
body:has([class*="st-key-cai_topbar"]) header[data-testid="stHeader"],
body:has([class*="st-key-cai_topbar"]) [data-testid="stToolbar"],
body:has([class*="st-key-cai_topbar"]) [data-testid="stDecoration"] {
    visibility: hidden !important;
    pointer-events: none !important;
}

/*
   La barra es hija de varios contenedores de Streamlit. Con position: sticky
   se desplazaba junto a su contenedor inmediato. Fijarla al viewport evita
   ese problema y conserva el desplazamiento normal de las paginas.
*/
body:has([class*="st-key-cai_topbar"]) [data-testid="stMainBlockContainer"] {
    padding-top: 124px !important; /* espacio para que no tape el contenido */
}
[class*="st-key-cai_topbar"] {
    position: fixed !important;
    inset: 0 0 auto 0 !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 100001 !important;
    width: 100vw !important;
    max-width: none !important;
    margin: 0 !important;
    background: #f9fbfd !important;
    border: 0 !important;
    border-bottom: 1px solid #d4dfeb !important;
    border-radius: 0 0 12px 12px !important;
    min-height: 104px !important;
    padding: 11px clamp(15px, 1.7vw, 32px) !important;
    box-shadow: 0 5px 14px rgba(18, 50, 83, 0.09) !important;
}
[class*="st-key-cai_topbar"] [data-testid="stHorizontalBlock"] {
    gap: .45rem !important;
    align-items: center !important;
}
/* Bloque de marca: logo completamente separado de CurriculAi. */
[class*="st-key-cai_topbar"] .cai-admin-brand {
    display: flex !important;
    align-items: center !important;
    flex-wrap: nowrap !important;
    gap: 14px !important;
    width: 100% !important;
    min-width: 0 !important;
}
[class*="st-key-cai_topbar"] .cai-admin-brand-img {
    width: 69px !important;
    height: 69px !important;
    flex-shrink: 0 !important;
    display: block !important;
    object-fit: contain !important;
    box-sizing: border-box !important;
    background: white !important;
    border-radius: 12px !important;
    padding: 5px !important;
    border: 1px solid #dce6ed !important;
}
[class*="st-key-cai_topbar"] .cai-admin-brand-title {
    font-family: Inter, system-ui, sans-serif !important;
    font-size: clamp(1.45rem, 1.7vw, 2.05rem) !important;
    line-height: 1.13 !important;
    letter-spacing: -.035em !important;
    font-weight: 850 !important;
    color: #173a62 !important;
    white-space: nowrap !important;
}
[class*="st-key-cai_topbar"] .cai-brand-sub { display: none !important; }

/* Menú: botones reales, pero solo texto visual y línea activa. 
   Estos selectores sobreescriben los botones globales de servicios/estilos.py. */
[class*="st-key-cai_topbar"] [class*="st-key-cai_nav_"] [data-testid="stButton"] button,
[class*="st-key-cai_topbar"] [class*="st-key-cai_nav_"] button {
    background: transparent !important;
    background-color: transparent !important;
    border: 0 !important;
    border-bottom: 3px solid transparent !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    color: #1c4067 !important;
    font-size: clamp(.70rem, .80vw, .88rem) !important;
    font-weight: 720 !important;
    min-height: 43px !important;
    height: 43px !important;
    padding: 10px 1px 7px !important;
    white-space: nowrap !important;
    width: 100% !important;
    transition: color .15s ease, border-color .15s ease !important;
}
[class*="st-key-cai_topbar"] [class*="st-key-cai_nav_"] button p,
[class*="st-key-cai_topbar"] [class*="st-key-cai_nav_"] button span {
    color: inherit !important;
    font-size: inherit !important;
    font-weight: inherit !important;
    white-space: nowrap !important;
}
[class*="st-key-cai_topbar"] [class*="st-key-cai_nav_"] button:hover {
    color: #008be3 !important;
    background: transparent !important;
    background-color: transparent !important;
    border-bottom-color: #8fccec !important;
}
[class*="st-key-cai_topbar"] [class*="st-key-cai_nav_activa_"] button {
    color: #173a62 !important;
    font-weight: 850 !important;
    border-bottom-color: #008be3 !important;
}
[class*="st-key-cai_topbar"] [class*="st-key-cai_nav_"] button:focus-visible {
    outline: 2px solid #008be3 !important;
    outline-offset: 2px !important;
}

/* Salida a la derecha, sin caja ni borde. La sesión se limpia por callback. */
[class*="st-key-cai_topbar"] [class*="st-key-cai_admin_cerrar_sesion"] button {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    padding: 7px 4px !important;
    min-height: 35px !important;
    height: 35px !important;
    color: #173a62 !important;
    font-weight: 780 !important;
    font-size: .78rem !important;
    white-space: nowrap !important;
    text-decoration: none !important;
}
[class*="st-key-cai_topbar"] [class*="st-key-cai_admin_cerrar_sesion"] button p,
[class*="st-key-cai_topbar"] [class*="st-key-cai_admin_cerrar_sesion"] button span {
    color: inherit !important;
    white-space: nowrap !important;
}
[class*="st-key-cai_topbar"] [class*="st-key-cai_admin_cerrar_sesion"] button:hover {
    background: transparent !important;
    border: 0 !important;
    color: #b33348 !important;
    text-decoration: underline !important;
}
[class*="st-key-cai_topbar"] .cai-top-actions {
    display: flex !important;
    justify-content: flex-end !important;
    margin-top: 3px !important;
}
[class*="st-key-cai_topbar"] .cai-status {
    font-size: .67rem !important;
    padding: 5px 9px !important;
}
[class*="st-key-cai_topbar"] .cai-status.ok {
    background: #dceee7 !important;
    color: #17634c !important;
}
[class*="st-key-cai_topbar"] .cai-status.error {
    background: #f6e2e5 !important;
    color: #8e3642 !important;
}
@media (max-width: 1370px) {
    [class*="st-key-cai_topbar"] .cai-admin-brand-img {
        width: 59px !important;
        height: 59px !important;
    }
    [class*="st-key-cai_topbar"] .cai-admin-brand { gap: 9px !important; }
    [class*="st-key-cai_topbar"] .cai-admin-brand-title { font-size: 1.4rem !important; }
    [class*="st-key-cai_topbar"] [class*="st-key-cai_nav_"] button { font-size: .69rem !important; }
}
/* Pantallas pequeñas: el menu puede ocupar mas alto. Reservar espacio adicional. */
@media (max-width: 1050px) {
    body:has([class*="st-key-cai_topbar"]) [data-testid="stMainBlockContainer"] {
        padding-top: 205px !important;
    }
    [class*="st-key-cai_topbar"] [data-testid="stHorizontalBlock"] {flex-wrap: wrap !important;}
    [class*="st-key-cai_topbar"] {padding: 8px 12px !important;}
}
@media (max-width: 680px) {
    body:has([class*="st-key-cai_topbar"]) [data-testid="stMainBlockContainer"] {
        padding-top: 290px !important;
    }
}
</style>
"""


def aplicar_barra_admin() -> None:
    st.markdown(CSS_BARRA_ADMIN, unsafe_allow_html=True)


def dibujar_marca_admin(logo: Path | None) -> None:
    img = ('<span class="cai-admin-brand-img" style="display:flex;align-items:center;'
           'justify-content:center;color:#173a62;font-size:25px;font-weight:900">CA</span>')
    if logo is not None and Path(logo).is_file():
        ruta = Path(logo)
        mime = mimetypes.guess_type(ruta.name)[0] or 'image/png'
        if mime in {'image/png', 'image/jpeg', 'image/webp'}:
            b64 = base64.b64encode(ruta.read_bytes()).decode('ascii')
            img = f'<img class="cai-admin-brand-img" alt="Logo CurriculAi" src="data:{mime};base64,{b64}">'
    st.markdown(
        f'<div class="cai-admin-brand">{img}<span class="cai-admin-brand-title">CurriculAi</span></div>',
        unsafe_allow_html=True,
    )


def cerrar_sesion_admin() -> None:
    """Callback ANTES del rerun: cierra la sesión aunque existan widgets montados.

    No cambia cuentas, contraseñas, sesión de otras personas ni la base de datos.
    """
    st.session_state.clear()

from datetime import date
import streamlit as st
from servicios.ui_helpers import seguro, es_finalista


def _registros(ctx, clave):
    datos = ctx.get(clave) or []
    return datos if isinstance(datos, list) else []


def _finalista(item):
    estado = str(item.get("estado") or "").casefold()
    return "finalista" in estado or "aceptado" in estado


def _kpi(label, numero, desc, icono):
    return (
        '<div class="cai-kpi">'
        '<div class="cai-kpi-top">'
        f'<span class="cai-kpi-label">{label}</span>'
        f'<span class="cai-kpi-icon">{icono}</span>'
        '</div>'
        f'<div class="cai-kpi-number">{numero}</div>'
        f'<div class="cai-kpi-hint">{desc}</div>'
        '</div>'
    )


def render(ctx):
    candidatos = _registros(ctx, "candidatos")
    vacantes = _registros(ctx, "vacantes")
    entrevistas = _registros(ctx, "entrevistas")
    finalistas = [e for e in entrevistas if es_finalista(e)]
    proximas = [e for e in entrevistas if str(e.get("estado") or "").casefold() not in ("cancelada", "rechazado")]

    st.markdown('<div class="cai-kicker">CENTRO DE OPERACIONES · CURRICULAI</div>', unsafe_allow_html=True)
    if not ctx.get("api_conectada", True):
        st.error("Sin conexión con FastAPI: las cifras de este panel no pueden verificarse.")
        return
    st.markdown('<h1>Panel de control</h1>', unsafe_allow_html=True)
    st.markdown('<p class="cai-descripcion">Vista general del reclutamiento y la gestión de talento.</p>', unsafe_allow_html=True)

    st.markdown(
        '<div class="cai-dashboard-hero">'
        '<div class="cai-hero-pill">Inteligencia de talento</div>'
        '<div class="cai-hero-title">Un reclutamiento claro, visual y fácil de administrar.</div>'
        '<div class="cai-hero-copy">Centraliza vacantes, administra candidatos, programa entrevistas y usa el motor de IA para priorizar talento en un solo lugar. Las decisiones siguen siendo humanas, pero el proceso ahora es más rápido.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4, gap="large")
    with c1:
        st.markdown(_kpi("Vacantes", len(vacantes), "Vacantes registradas", "💼"), unsafe_allow_html=True)
    with c2:
        st.markdown(_kpi("Candidatos", len(candidatos), "Perfiles disponibles", "👥"), unsafe_allow_html=True)
    with c3:
        st.markdown(_kpi("Entrevistas", len(entrevistas), "Entrevistas registradas", "📅"), unsafe_allow_html=True)
    with c4:
        st.markdown(_kpi("Finalistas", len(finalistas), "Registros en etapa final", "⭐"), unsafe_allow_html=True)

    izquierda, derecha = st.columns([1.5, 1], gap="large")
    with izquierda:
        st.markdown('<div class="cai-section">Actividad reciente</div>', unsafe_allow_html=True)
        recientes = sorted(proximas, key=lambda x: (str(x.get("fecha") or ""), str(x.get("hora") or "")), reverse=True)[:6]
        if recientes:
            for item in recientes:
                st.markdown(
                    f'<div class="cai-outline-box"><strong>{seguro(item.get("nombre") or "Candidato")}</strong><br>'
                    f'<span class="cai-subtle">{seguro(item.get("puesto") or "Sin puesto")} · {seguro(item.get("fecha") or "Sin fecha", 15)} {seguro(item.get("hora"), 8)}</span><br>'
                    f'<span class="cai-tag">{seguro(item.get("estado") or "Programada", 40)}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("Aún no hay actividad para mostrar.")

    with derecha:
        st.markdown('<div class="cai-section">Resumen operativo</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="cai-outline-box"><strong>Hoy</strong><br><span class="cai-subtle">{date.today().strftime("%d/%m/%Y")}</span><br><br>'
            f'• {len(vacantes)} vacante(s) activas<br>• {len(candidatos)} expediente(s) disponibles<br>• {len(entrevistas)} entrevista(s) en control<br>• {len(finalistas)} perfil(es) en decisión final</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="cai-outline-box"><strong>Flujo recomendado</strong><br>'
            '<span class="cai-subtle">Vacante → Evaluación con IA → Entrevista → Finalista → Aceptado / Rechazado</span></div>',
            unsafe_allow_html=True,
        )

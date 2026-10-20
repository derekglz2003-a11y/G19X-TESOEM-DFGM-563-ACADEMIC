import streamlit as st
import pandas as pd
import requests
import os
import re
import base64
from datetime import datetime
from urllib.parse import quote
from servicios.api import API_URL, api_get, api_post, api_post_form, api_delete, api_put
from servicios.whatsapp import enviar_whatsapp_ultramsg, registrar_mensaje_whatsapp

HERO_IMAGE_B64 = "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"

def finalistas_count(entrevistas):
    return sum(1 for x in entrevistas if "final" in str(x.get("estado", "")).lower() or "finalista" in str(x.get("tipo_finalista", "")).lower())

def render(ctx):
    candidatos = ctx["candidatos"]
    vacantes = ctx["vacantes"]
    entrevistas = ctx["entrevistas"]
    if True:

        import streamlit.components.v1 as components
        components.html(
            """<!doctype html><html><head><meta charset="utf-8"><style>
            *{box-sizing:border-box} body{margin:0;font-family:Inter,Arial,sans-serif;background:transparent}
            .hero{min-height:280px;border-radius:24px;padding:30px 34px;background:radial-gradient(circle at 82% 18%,rgba(255,173,111,.42),transparent 27%),radial-gradient(circle at 68% 90%,rgba(171,135,255,.35),transparent 31%),linear-gradient(125deg,#fff0e4 0%,#f0e8ff 50%,#e1f2ff 100%);border:1px solid #e4d8fa;position:relative;overflow:hidden;box-shadow:0 10px 30px rgba(43,91,145,.06)}
            .hero h1{color:#123b72;font-size:34px;line-height:1.2;margin:16px 0 22px;font-weight:800}.hero h2{color:#1967d2;font-size:14px;letter-spacing:.8px;margin:0 0 15px;font-weight:700}.hero p{color:#51647c;max-width:560px;line-height:1.6;font-size:14px;margin:0}.eyebrow{color:#3180df;font-size:11px;font-weight:800;letter-spacing:1.2px}
            .hero-art{position:absolute;right:0;top:0;width:46%;height:100%;overflow:hidden;border-radius:0 23px 23px 0;box-shadow:-22px 0 42px rgba(105,83,180,.08);background:linear-gradient(135deg,#dcecff,#f4dcff)}
            .hero-art img{width:100%;height:100%;display:block;object-fit:cover;object-position:center;border-radius:0 23px 23px 0}
            .hero:after{content:"";position:absolute;right:35%;top:0;bottom:0;width:18%;background:linear-gradient(90deg,rgba(240,232,255,0),rgba(240,232,255,.7));pointer-events:none}
            @media(max-width:760px){.hero{padding:24px;min-height:300px}.hero h1{font-size:28px}.hero-art{opacity:.28;width:60%;right:0;top:0}.hero:after{right:35%;width:30%}.hero p{max-width:100%}}
            </style></head><body><div class="hero">
        <div style="position:relative;z-index:2;">
            <div style="color:#3180df;font-size:11px;font-weight:800;letter-spacing:1.2px;">
                OPTIMIZADOR DE FILTRADO CURRICULAR MEDIANTE INTELIGENCIA ARTIFICIAL
            </div>
            <h1>Bienvenido a CurriculAI</h1>
            <h2>INTELIGENCIA ARTIFICIAL PARA ENCONTRAR TALENTO</h2>
            <p>
                Analiza, compara y encuentra los perfiles que mejor encajan
                con cada vacante de forma rápida y eficiente.
            </p>
        </div>

        <div class="hero-art">
            <img src="HERO_IMAGE_PLACEHOLDER" alt="Ilustración de inteligencia artificial analizando currículums">
        </div>
    </div></body></html>""".replace("HERO_IMAGE_PLACEHOLDER", "data:image/webp;base64," + HERO_IMAGE_B64),
            height=325,
            scrolling=False,
        )

        st.write("")

        # Métricas
        m1, m2, m3, m4 = st.columns(4)

        metrics = [
            (m1, "👥", "Candidatos", len(candidatos), "CV registrados"),
            (m2, "💼", "Vacantes activas", len(vacantes), "Puestos publicados"),
            (m3, "📅", "Entrevistas", len(entrevistas), "Procesos programados"),
            (m4, "⭐", "Finalistas", finalistas_count(entrevistas), "Candidatos destacados"),
        ]

        for col, icon, label, value, foot in metrics:
            with col:
                st.markdown(f"""
                <div class="metric">
                    <div class="metric-top">
                        <div class="metric-label">{label}</div>
                        <div class="metric-icon">{icon}</div>
                    </div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-foot">{foot}</div>
                </div>
                """, unsafe_allow_html=True)

        st.write("")

        left, right = st.columns([2.05, 1], gap="large")

        with left:
            st.markdown("""
            <div class="panel">
                <div class="panel-title">👥 Candidatos recientes</div>
                <div class="panel-sub">
                    Los perfiles más recientes incorporados al pool de talento.
                </div>
            </div>
            """, unsafe_allow_html=True)

            if candidatos:
                recientes = candidatos[-6:][::-1]

                for c in recientes:
                    nombre = c.get("nombre", "Candidato")
                    puesto = c.get("perfil_destacado", "Perfil general")
                    email = c.get("email", "")
                    desempeno = c.get("desempeno", "Calificado")

                    if "alto" in desempeno.lower():
                        cls = "pill-green"
                    elif "calific" in desempeno.lower():
                        cls = "pill-blue"
                    else:
                        cls = "pill-orange"

                    st.markdown(f"""
                    <div class="candidate-row">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <div class="candidate-name">{nombre}</div>
                                <div class="candidate-small">{email} · {puesto}</div>
                            </div>
                            <span class="pill {cls}">{desempeno}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="empty">Todavía no hay candidatos. Usa “Analizar CVs” para comenzar.</div>',
                    unsafe_allow_html=True,
                )

        with right:
            st.markdown("""
            <div class="panel">
                <div class="panel-title">⚡ Acciones rápidas</div>
                <div class="panel-sub">Acciones, no una segunda navegación.</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("📤  Analizar CVs", use_container_width=True, type="primary"):
                st.session_state["go_upload"] = True

            if st.button("💼  Crear vacante", use_container_width=True):
                st.session_state["go_vacante"] = True

            if st.button("📊  Ver ranking", use_container_width=True):
                st.session_state["go_ranking"] = True

            if st.button("📅  Programar entrevista", use_container_width=True):
                st.session_state["go_interview"] = True

            st.markdown("<br>", unsafe_allow_html=True)

            if vacantes:
                st.markdown("""
                <div class="panel-title">💼 Últimas vacantes</div>
                """, unsafe_allow_html=True)

                for v in vacantes[:4]:
                    st.markdown(
                        f"""
                        <div class="candidate-row">
                            <div class="candidate-name">{v.get("titulo","Vacante")}</div>
                            <div class="candidate-small">Puesto publicado</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.markdown(
            '<div class="footer">CurriculAI · Optimizador de filtrado curricular mediante inteligencia artificial</div>',
            unsafe_allow_html=True,
        )

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

def render(ctx):
    candidatos = ctx["candidatos"]
    vacantes = ctx["vacantes"]
    entrevistas = ctx["entrevistas"]
    if True:

        st.title("👥 Candidatos")
        st.caption("Pool central de talento analizado por CurriculAI.")

        upload = st.file_uploader(
            "Cargar y analizar currículums",
            type=["pdf", "docx", "doc", "txt", "png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
        )

        if upload:
            if st.button("🤖 Analizar currículums", type="primary"):
                files = [
                    ("files", (f.name, f.getvalue(), f.type or "application/octet-stream"))
                    for f in upload
                ]
                response = api_post("/api/v1/analizar-cvs-masivo", files=files)

                if response is not None and response.ok:
                    st.success(response.json().get("mensaje", "CVs procesados."))
                    st.rerun()
                else:
                    detalle = ""
                    if response is not None:
                        try:
                            payload = response.json()
                            detalle = payload.get("detail") or payload.get("mensaje") or payload.get("detalles_tecnicos") or ""
                        except Exception:
                            detalle = response.text[:500]
                    st.error("No fue posible procesar los CVs. Revisa FastAPI y las dependencias del extractor.")
                    if detalle:
                        st.caption(str(detalle))

        st.divider()

        if candidatos:
            filas = []
            for c in candidatos:
                filas.append({
                    "Candidato": c.get("nombre") or "Sin nombre",
                    "Perfil": c.get("perfil_destacado") or "General",
                    "Desempeño": c.get("desempeno") or "Sin evaluar",
                    "Correo": c.get("email") or "No disponible",
                    "Teléfono": c.get("telefono") or "No disponible",
                })
            st.markdown('''
            <style>
            [data-testid="stDataFrame"] {background:#fffaf7 !important;border:1px solid #e9e2f4;border-radius:16px;overflow:hidden;}
            [data-testid="stDataFrame"] * {color:#293d5b !important;}
            .candidate-card {background:linear-gradient(135deg,#ffffff 0%,#fffaf6 55%,#f5f2ff 100%);border:1px solid #e7e1f3;border-radius:18px;padding:20px 22px;margin:8px 0 14px;box-shadow:0 8px 22px rgba(76,70,130,.06)}
            .candidate-kicker {font-size:11px;font-weight:800;letter-spacing:1px;text-transform:uppercase;color:#7460d8;margin-bottom:5px}
            .candidate-title {font-size:23px;font-weight:800;color:#1b365e;line-height:1.25;margin:0 0 8px}
            .candidate-pill {display:inline-block;padding:5px 10px;border-radius:999px;background:#e7f8f0;color:#177c59;font-weight:700;font-size:12px;margin:3px 4px 3px 0}
            </style>
            ''', unsafe_allow_html=True)
            st.subheader("🧑‍💼 Expediente del candidato")
            selector_opciones = {
                f"{c.get('nombre') or 'Sin nombre'} · #{c.get('id', '?')} · {c.get('perfil_destacado') or 'General'}": c
                for c in candidatos
            }
            seleccionado = st.selectbox("Selecciona el expediente que quieres consultar", list(selector_opciones.keys()))
            candidato = selector_opciones[seleccionado]
            nombre_c = candidato.get("nombre") or "Candidato sin nombre"
            perfil_c = candidato.get("perfil_destacado") or "Perfil general"
            estado_c = candidato.get("desempeno") or "Pendiente de evaluación"
            st.markdown(f'''<div class="candidate-card">
                <div class="candidate-kicker">EXPEDIENTE · ID {candidato.get('id', '—')}</div>
                <div class="candidate-title">{nombre_c}</div>
                <span class="candidate-pill">{perfil_c}</span><span class="candidate-pill">{estado_c}</span>
            </div>''', unsafe_allow_html=True)

            info_tab, perfil_tab, cv_tab = st.tabs(["👤 Datos de contacto", "✨ Perfil profesional", "📄 CV y texto extraído"])
            with info_tab:
                col1, col2 = st.columns(2)
                with col1:
                    with st.container(border=True):
                        st.markdown("#### 📬 Contacto")
                        st.write(f"**Correo:** {candidato.get('email') or 'No disponible'}")
                        st.write(f"**Teléfono:** {candidato.get('telefono') or 'No disponible'}")
                with col2:
                    with st.container(border=True):
                        st.markdown("#### 🪪 Datos generales")
                        st.write(f"**Edad:** {candidato.get('edad') or 'No especificada'}")
                        st.write(f"**Sexo:** {candidato.get('sexo') or 'No especificado'}")
                        st.write(f"**Archivo:** {candidato.get('nombre_archivo') or 'No disponible'}")
            with perfil_tab:
                col1, col2 = st.columns(2)
                with col1:
                    with st.container(border=True):
                        st.markdown("#### 🧰 Habilidades")
                        st.write(candidato.get("skills") or "No se detectaron habilidades en el CV.")
                        st.markdown("#### 💪 Puntos fuertes")
                        st.write(candidato.get("puntos_fuertes") or "Sin puntos fuertes registrados.")
                with col2:
                    with st.container(border=True):
                        st.markdown("#### 🧭 Experiencia")
                        st.write(candidato.get("experiencia") or "No se detectó experiencia laboral.")
                        st.markdown("#### 📊 Evaluación")
                        st.write(estado_c)
            with cv_tab:
                texto_cv = candidato.get("texto_completo") or "No hay texto extraído almacenado para este candidato."
                st.text_area("Texto recuperado del currículum", value=str(texto_cv), height=260, disabled=True, key=f"cv_texto_{candidato.get('id', 'sin_id')}")
                st.caption("El archivo original solo puede descargarse si el backend expone un endpoint para recuperarlo.")

            st.divider()
            st.subheader("🗑️ Administrar expediente")
            st.caption("Puedes quitar solo el CV o eliminar al candidato completo.")

            id_candidato = candidato.get("id")
            tiene_cv = bool(candidato.get("nombre_archivo") or candidato.get("texto_completo"))
            col_cv, col_persona = st.columns(2)
            with col_cv:
                if st.button("📄 Quitar CV", key=f"quitar_cv_{id_candidato}", disabled=not tiene_cv, use_container_width=True):
                    st.session_state[f"confirmar_cv_{id_candidato}"] = True
            with col_persona:
                if st.button("🗑️ Eliminar candidato", key=f"eliminar_candidato_{id_candidato}", use_container_width=True):
                    st.session_state[f"confirmar_candidato_{id_candidato}"] = True

            if st.session_state.get(f"confirmar_cv_{id_candidato}", False):
                st.warning("Se borrarán el archivo, el texto extraído y las evaluaciones del CV. Se conservará el perfil del candidato.")
                a, b = st.columns(2)
                with a:
                    if st.button("Confirmar quitar CV", key=f"confirmar_quitar_cv_{id_candidato}", type="primary"):
                        respuesta = api_delete(f"/api/v1/candidatos/{id_candidato}/cv")
                        if respuesta is not None and respuesta.ok:
                            st.session_state.pop(f"confirmar_cv_{id_candidato}", None)
                            st.success("CV eliminado.")
                            st.rerun()
                        else:
                            st.error(f"No se pudo quitar el CV: {respuesta.text[:300] if respuesta is not None else 'API sin conexión'}")
                with b:
                    if st.button("Cancelar", key=f"cancelar_quitar_cv_{id_candidato}"):
                        st.session_state.pop(f"confirmar_cv_{id_candidato}", None)
                        st.rerun()

            if st.session_state.get(f"confirmar_candidato_{id_candidato}", False):
                st.error(f"Se eliminará definitivamente a {nombre_c}, su CV, evaluaciones y entrevista asociada.")
                a, b = st.columns(2)
                with a:
                    if st.button("Confirmar eliminación definitiva", key=f"confirmar_eliminar_candidato_{id_candidato}", type="primary"):
                        respuesta = api_delete(f"/api/v1/candidatos/{id_candidato}")
                        if respuesta is not None and respuesta.ok:
                            st.session_state.pop(f"confirmar_candidato_{id_candidato}", None)
                            st.success("Candidato eliminado.")
                            st.rerun()
                        else:
                            st.error(f"No se pudo eliminar: {respuesta.text[:300] if respuesta is not None else 'API sin conexión'}")
                with b:
                    if st.button("Cancelar", key=f"cancelar_eliminar_candidato_{id_candidato}"):
                        st.session_state.pop(f"confirmar_candidato_{id_candidato}", None)
                        st.rerun()

            st.divider()
            st.subheader("📋 Resumen de candidatos")
            st.caption("Consulta rápidamente los perfiles que ya fueron procesados.")
            st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True, height=min(420, 42 * (len(filas) + 1)))
        else:
            st.info("No hay candidatos registrados todavía.")

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

        st.title("💼 Vacantes")
        st.caption("Administra los puestos disponibles y prepara el análisis de compatibilidad.")

        with st.expander("➕ Crear nueva vacante", expanded=True):
            titulo = st.text_input("Título del puesto", placeholder="Ej. Desarrollador Full Stack")
            descripcion = st.text_area(
                "Descripción",
                height=180,
                placeholder="Describe responsabilidades, requisitos y habilidades..."
            )

            contexto_ia = st.text_input(
                "Detalles para la IA (opcional)",
                placeholder="Ej. horario, sueldo, experiencia, tipo de contrato, ubicación"
            )
            ia_col, c1, c2 = st.columns([1.7, 1.2, 3.1])
            with ia_col:
                ayudar_ia = st.button("✨ Mejorar descripción con IA", use_container_width=True)
            with c1:
                crear = st.button("Crear vacante", type="primary", use_container_width=True)
            with c2:
                st.caption("La IA puede organizar el objetivo, responsabilidades y requisitos para que la vacante sea más clara.")

            if ayudar_ia:
                if not titulo.strip():
                    st.warning("Escribe primero el título del puesto para que la IA pueda preparar la descripción.")
                else:
                    with st.spinner("Preparando una descripción profesional..."):
                        respuesta_ia = api_post(
                            "/api/v1/generar-descripcion",
                            data={"titulo": titulo.strip(), "contexto": contexto_ia.strip(), "descripcion": descripcion.strip()}
                        )
                    if respuesta_ia is not None and respuesta_ia.ok:
                        try:
                            resultado_ia = respuesta_ia.json()
                            texto_ia = (resultado_ia.get("descripcion") or resultado_ia.get("descripcion_generada")
                                        or resultado_ia.get("contenido") or resultado_ia.get("texto") or "")
                            if not texto_ia and isinstance(resultado_ia, str):
                                texto_ia = resultado_ia
                            if texto_ia:
                                st.session_state["descripcion_vacante_ia"] = texto_ia
                                st.success("Descripción generada. Revísala y edítala antes de crear la vacante.")
                                st.rerun()
                            else:
                                st.error("La API respondió, pero no encontré el campo de descripción en su respuesta. Revisa el formato que devuelve /generar-descripcion.")
                        except ValueError:
                            st.error("La respuesta del generador de IA no es JSON válido.")
                    else:
                        detalle_ia = ""
                        if respuesta_ia is not None:
                            try:
                                detalle_ia = str(respuesta_ia.json().get("detail", ""))
                            except Exception:
                                detalle_ia = respuesta_ia.text[:300]
                        st.error("No se pudo generar la descripción con IA. Comprueba que el endpoint /api/v1/generar-descripcion esté activo. " + detalle_ia)

            if "descripcion_vacante_ia" in st.session_state:
                descripcion = st.text_area(
                    "Descripción sugerida por IA (puedes editarla)",
                    value=st.session_state["descripcion_vacante_ia"],
                    height=220,
                    key="descripcion_ia_editable"
                )
                # Mantener el texto sugerido como valor al crear la vacante.
                st.session_state["descripcion_vacante_actual"] = descripcion
            else:
                st.session_state["descripcion_vacante_actual"] = descripcion

            if crear:
                if not titulo.strip() or not descripcion.strip():
                    st.warning("Completa el título y la descripción.")
                else:
                    response = api_post_form(
                        "/api/v1/vacantes",
                        data={"titulo": titulo.strip(), "descripcion": st.session_state.get("descripcion_vacante_actual", descripcion).strip()}
                    )
                    if response is not None and response.ok:
                        st.success("Vacante creada correctamente.")
                        st.session_state.pop("descripcion_vacante_ia", None)
                        st.session_state.pop("descripcion_vacante_actual", None)
                        st.rerun()
                    else:
                        detalle = "No hubo respuesta del backend. Verifica que FastAPI esté iniciado y que API_URL apunte al servidor correcto."
                        if response is not None:
                            try:
                                detalle = str(response.json().get("detail", response.text[:400]))
                            except Exception:
                                detalle = response.text[:400] or f"HTTP {response.status_code}"
                        st.error(f"No se pudo crear la vacante: {detalle}")

        st.divider()
        st.subheader("📌 Vacantes disponibles")
        st.caption("Consulta, edita o elimina las vacantes registradas.")

        if vacantes:
            for v in vacantes:
                with st.container(border=True):
                    a, b, c = st.columns([4.4, 1.25, 1.15])
                    with a:
                        st.subheader(f"💼 {v.get('titulo', 'Vacante')}")
                        st.caption(f"Vacante #{v.get('id', '—')} · Disponible")
                        descripcion_v = str(v.get("descripcion") or "Sin descripción disponible.")
                        st.write(descripcion_v[:260] + ("…" if len(descripcion_v) > 260 else ""))
                    with b:
                        if st.button("👁️ Ver vacante", key=f"view_{v.get('id')}", use_container_width=True):
                            st.session_state[f"ver_vacante_{v.get('id')}"] = not st.session_state.get(f"ver_vacante_{v.get('id')}", False)
                    with c:
                        if st.button("🗑️ Eliminar", key=f"del_{v.get('id')}", use_container_width=True):
                            st.session_state[f"confirmar_del_vac_{v.get('id')}"] = True
                    if st.session_state.get(f"confirmar_del_vac_{v.get('id')}", False):
                        st.warning("Se eliminará esta vacante y sus evaluaciones de ranking. Esta acción no se puede deshacer.")
                        confirmar, cancelar = st.columns(2)
                        with confirmar:
                            if st.button("Sí, eliminar definitivamente", key=f"yes_del_vac_{v.get('id')}", type="primary"):
                                r = api_delete(f"/api/v1/vacantes/{v.get('id')}")
                                if r is not None and r.ok:
                                    st.session_state.pop(f"confirmar_del_vac_{v.get('id')}", None)
                                    st.success("Vacante eliminada.")
                                    st.rerun()
                                else:
                                    detalle = "No hubo respuesta del backend."
                                    if r is not None:
                                        try:
                                            detalle = str(r.json().get("detail", r.text[:300]))
                                        except Exception:
                                            detalle = r.text[:300]
                                    st.error(f"No se pudo eliminar: {detalle}")
                        with cancelar:
                            if st.button("Cancelar", key=f"cancel_del_vac_{v.get('id')}"):
                                st.session_state.pop(f"confirmar_del_vac_{v.get('id')}", None)
                                st.rerun()
                    if st.session_state.get(f"ver_vacante_{v.get('id')}", False):
                        st.info("Descripción completa y requisitos")
                        st.write(descripcion_v)
                        st.markdown("**¿Qué sigue?** Selecciona esta vacante en Radar de talentos para consultar los mejores candidatos.")
                    with st.expander("✏️ Editar vacante"):
                        with st.form(f"form_editar_vacante_{v.get('id')}"):
                            nuevo_titulo = st.text_input("Título del puesto", value=str(v.get("titulo") or ""), key=f"titulo_edit_{v.get('id')}")
                            nueva_descripcion = st.text_area("Descripción y requisitos", value=descripcion_v, height=180, key=f"desc_edit_{v.get('id')}")
                            guardar_edicion = st.form_submit_button("Guardar cambios", type="primary")
                        if guardar_edicion:
                            if not nuevo_titulo.strip() or not nueva_descripcion.strip():
                                st.warning("El título y la descripción son obligatorios.")
                            else:
                                r = api_put(f"/api/v1/vacantes/{v.get('id')}", {"titulo": nuevo_titulo.strip(), "descripcion": nueva_descripcion.strip()})
                                if r is not None and r.ok:
                                    st.success("Vacante actualizada correctamente.")
                                    st.rerun()
                                else:
                                    detalle = "El backend no respondió."
                                    if r is not None:
                                        try: detalle = str(r.json().get("detail", r.text[:300]))
                                        except Exception: detalle = r.text[:300]
                                    st.error(f"No se pudo editar la vacante: {detalle}. Si aparece 404 o 405, reinicia el backend con el main.py actualizado que te entrego.")
        else:
            st.info("Todavía no hay vacantes.")

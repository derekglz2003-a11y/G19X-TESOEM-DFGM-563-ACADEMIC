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

        st.title("📊 Radar de talentos")
        st.caption("Los cinco perfiles con mayor compatibilidad para la vacante seleccionada.")

        if not vacantes:
            st.info("Primero crea una vacante en la sección Vacantes.")
        elif not candidatos:
            st.info("Primero carga y analiza currículums en Candidatos.")
        else:
            opciones = {f"{v.get('id')} · {v.get('titulo', 'Vacante')}": v for v in vacantes}
            seleccion = st.selectbox("Selecciona una vacante", list(opciones.keys()))
            vacante_sel = opciones[seleccion]
            vacante_id = vacante_sel.get("id")
            if st.button("✨ Encontrar los 5 mejores candidatos", type="primary", use_container_width=True):
                st.session_state["ranking_vacante_id"] = vacante_id
                with st.spinner("Evaluando compatibilidad semántica de los CVs..."):
                    respuesta = api_post(f"/api/v1/evaluar/{vacante_id}")
                if respuesta is not None and respuesta.ok:
                    resultado = respuesta.json()
                    st.session_state["ranking_resultados"] = resultado.get("ranking", [])
                    st.success(f"Evaluados: {resultado.get('evaluados', 0)} candidatos. Revisa los resultados antes de tomar decisiones.")
                    if resultado.get("omitidos_sin_texto"):
                        st.warning(f"Se omitieron {resultado['omitidos_sin_texto']} candidatos sin texto extraído del CV.")
                else:
                    st.session_state["ranking_resultados"] = []
                    detalle = respuesta.text[:500] if respuesta is not None else "API sin conexión"
                    st.error(f"No se pudo generar el ranking: {detalle}")

            ranking = st.session_state.get("ranking_resultados", []) if st.session_state.get("ranking_vacante_id") == vacante_id else []
            if ranking:
                def score_num(item):
                    raw = item.get("score_similitud", item.get("compatibilidad", 0))
                    try:
                        val = float(raw or 0)
                        return val * 100 if val <= 1 else val
                    except (TypeError, ValueError):
                        return 0.0

                ranking_ordenado = sorted(ranking, key=score_num, reverse=True)[:5]
                st.markdown("### 🏆 Top 5 de talento")
                st.caption(f"Vacante: {vacante_sel.get('titulo', '')} · Se muestran únicamente los cinco perfiles con mejor puntuación disponible.")
                for idx, item in enumerate(ranking_ordenado, start=1):
                    candidato_id = item.get("candidato_id", item.get("id_candidato"))
                    nombre = item.get("candidato_nombre", item.get("nombre", "Candidato"))
                    candidato_obj = next((c for c in candidatos if str(c.get("id")) == str(candidato_id)), None)
                    if candidato_obj:
                        nombre = candidato_obj.get("nombre") or nombre
                    score = score_num(item)
                    with st.container(border=True):
                        c1, c2 = st.columns([5, 1])
                        with c1:
                            st.markdown(f"#### {['🥇','🥈','🥉','🏅','🏅'][idx-1]} {idx}. {nombre}")
                            st.progress(max(0.0, min(score / 100, 1.0)), text=f"Compatibilidad: {score:.1f}%")
                            perfil = (candidato_obj or {}).get("perfil_destacado", item.get("perfil_destacado", "Perfil no especificado"))
                            skills = (candidato_obj or {}).get("skills", item.get("skills", ""))
                            st.caption(f"Perfil: {perfil}")
                            if skills:
                                st.write(f"**Habilidades:** {skills}")
                            resumen = item.get("resumen_ejecutivo", item.get("resumen", ""))
                            justificacion = item.get("justificacion_fit", "")
                            if resumen or justificacion:
                                with st.expander("Ver análisis y justificación"):
                                    if resumen: st.write(resumen)
                                    if justificacion: st.write(justificacion)
                        with c2:
                            st.metric("Match", f"{score:.0f}%")
                        if candidato_obj:
                            with st.expander(f"📅 Agendar cita con {nombre}"):
                                with st.form(f"form_radar_cita_{vacante_id}_{candidato_obj.get('id')}"):
                                    fecha_cita = st.date_input("Fecha", key=f"radar_fecha_{vacante_id}_{candidato_obj.get('id')}")
                                    hora_cita = st.time_input("Hora", key=f"radar_hora_{vacante_id}_{candidato_obj.get('id')}")
                                    lugar_cita = st.text_input("Lugar o enlace", value="Google Meet", key=f"radar_lugar_{vacante_id}_{candidato_obj.get('id')}")
                                    enviar_cita = st.form_submit_button("Agendar entrevista", type="primary", use_container_width=True)
                                if enviar_cita:
                                    ya_existe = any(str(e.get("candidato_id")) == str(candidato_obj.get("id")) for e in entrevistas)
                                    if ya_existe:
                                        st.warning("Este candidato ya tiene una entrevista registrada. Adminístrala desde Entrevistas.")
                                    else:
                                        resp = api_post("/api/v1/entrevistas", data={
                                            "candidato_id": candidato_obj.get("id"),
                                            "nombre": candidato_obj.get("nombre", nombre),
                                            "puesto": vacante_sel.get("titulo", ""),
                                            "fecha": fecha_cita.isoformat(),
                                            "hora": hora_cita.strftime("%H:%M"),
                                            "lugar": lugar_cita,
                                        })
                                        if resp is not None and resp.ok:
                                            telefono = re.sub(r"\D", "", str(candidato_obj.get("telefono", "")))
                                            if len(telefono) == 10: telefono = "52" + telefono
                                            msg = (f"Hola {candidato_obj.get('nombre', nombre)}, te contactamos de CurriculAI para invitarte a entrevista. "
                                                   f"Puesto: {vacante_sel.get('titulo', '')}. Fecha: {fecha_cita.isoformat()}. "
                                                   f"Hora: {hora_cita.strftime('%H:%M')}. Lugar/enlace: {lugar_cita}. ¡Esperamos tu confirmación!")
                                            enviado, detalle_envio, respuesta_ultra = enviar_whatsapp_ultramsg(telefono, msg)
                                            log_resp = registrar_mensaje_whatsapp({
                                                "candidato_id": candidato_obj.get("id"),
                                                "telefono": telefono,
                                                "mensaje": msg,
                                                "estado": "Enviado" if enviado else "Fallido",
                                                "proveedor": "UltraMsg",
                                                "detalle": detalle_envio,
                                                "respuesta": respuesta_ultra,
                                            })
                                            st.session_state["cita_agendada_whatsapp"] = {"telefono": telefono, "mensaje": msg, "nombre": candidato_obj.get("nombre", nombre), "enviado": enviado, "detalle": detalle_envio}
                                            st.success("Entrevista agendada correctamente.")
                                            if enviado:
                                                st.success("📲 Invitación enviada automáticamente por WhatsApp mediante UltraMsg.")
                                            else:
                                                st.warning(f"La entrevista se guardó, pero WhatsApp no se envió automáticamente: {detalle_envio}")
                                                st.caption("Revisa ULTRAMSG_INSTANCE_ID y ULTRAMSG_TOKEN en .env y confirma que el endpoint de registro de mensajes exista.")
                                            if log_resp is None or not log_resp.ok:
                                                st.warning("No se pudo guardar el registro del mensaje en la base de datos. Falta habilitar /api/v1/mensajes-whatsapp en FastAPI.")
                                            st.rerun()
                                        else:
                                            st.error("No se pudo agendar. Revisa que el backend acepte los campos de entrevista.")
            elif st.session_state.get("ranking_vacante_id") == vacante_id:
                st.info("No hay evaluaciones registradas para esta vacante todavía.")
            else:
                st.info("Pulsa “Encontrar los 5 mejores candidatos” para consultar el ranking guardado en el backend.")

        cita_whatsapp = st.session_state.get("cita_agendada_whatsapp")
        if cita_whatsapp:
            st.divider()
            st.success(f"Entrevista lista para {cita_whatsapp.get('nombre', 'el candidato')}.")
            tel = cita_whatsapp.get("telefono", "")
            if cita_whatsapp.get("enviado"):
                st.caption("WhatsApp: mensaje enviado mediante UltraMsg.")
            elif tel and len(tel) >= 10:
                st.link_button("💬 Abrir WhatsApp como alternativa", f"https://wa.me/{tel}?text={quote(cita_whatsapp.get('mensaje', ''))}", use_container_width=True)
                st.caption("El envío automático no se completó; puedes enviar la invitación manualmente.")
            else:
                st.warning("La cita se guardó, pero el candidato no tiene un teléfono válido para WhatsApp.")

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

        st.title("📅 Entrevistas")
        st.caption("Agenda y administra los procesos de entrevista.")

        if candidatos:
            candidatos_map = {
                f"{c.get('nombre','Candidato')} · {c.get('perfil_destacado','')}": c
                for c in candidatos
            }

            with st.expander("➕ Programar entrevista", expanded=True):
                seleccionado = st.selectbox("Candidato", list(candidatos_map.keys()))
                candidato = candidatos_map[seleccionado]

                puesto = st.text_input(
                    "Puesto",
                    value=candidato.get("perfil_destacado", "")
                )

                fecha = st.date_input("Fecha")
                hora = st.time_input("Hora")
                lugar = st.text_input("Lugar / enlace", value="Google Meet")

                ya_tiene_entrevista = any(
                    str(e.get("candidato_id", "")) == str(candidato.get("id", ""))
                    for e in entrevistas
                )
                if ya_tiene_entrevista:
                    st.warning("Este candidato ya tiene una entrevista registrada. Para evitar duplicados, actualiza la entrevista existente.")

                if st.button("📅 Agendar entrevista", type="primary", disabled=ya_tiene_entrevista):
                    response = api_post(
                        "/api/v1/entrevistas",
                        data={
                            "candidato_id": candidato.get("id"),
                            "nombre": candidato.get("nombre", ""),
                            "puesto": puesto,
                            "fecha": fecha.isoformat(),
                            "hora": hora.strftime("%H:%M"),
                            "lugar": lugar,
                        },
                    )

                    if response is not None and response.ok:
                        telefono = re.sub(r"\D", "", str(candidato.get("telefono", "")))
                        if len(telefono) == 10:
                            telefono = "52" + telefono
                        mensaje = (f"Hola {candidato.get('nombre', 'candidato')}, te contactamos de CurriculAI para confirmar tu entrevista. "
                                   f"Puesto: {puesto}. Fecha: {fecha.isoformat()}. Hora: {hora.strftime('%H:%M')}. "
                                   f"Lugar o enlace: {lugar}. Por favor, confírmanos tu asistencia. ¡Gracias!")
                        enviado, detalle_envio, respuesta_ultra = enviar_whatsapp_ultramsg(telefono, mensaje)
                        log_resp = registrar_mensaje_whatsapp({
                            "candidato_id": candidato.get("id"), "telefono": telefono, "mensaje": mensaje,
                            "estado": "Enviado" if enviado else "Fallido", "proveedor": "UltraMsg",
                            "detalle": detalle_envio, "respuesta": respuesta_ultra,
                        })
                        st.success("Entrevista agendada.")
                        if enviado:
                            st.success("📲 Invitación enviada automáticamente por WhatsApp mediante UltraMsg.")
                        else:
                            st.warning(f"La entrevista se guardó, pero WhatsApp no se envió: {detalle_envio}")
                        if log_resp is None or not log_resp.ok:
                            st.warning("El backend aún no registra los mensajes en la base de datos. Añade el endpoint /api/v1/mensajes-whatsapp.")
                        st.rerun()
                    else:
                        detalle = ""
                        if response is not None:
                            try:
                                detalle = response.json().get("detail", "")
                            except Exception:
                                pass
                        st.error(f"No se pudo agendar la entrevista. {detalle}")
        else:
            st.info("Carga candidatos antes de programar entrevistas.")

        st.divider()

        if entrevistas:
            for e in entrevistas:
                with st.container(border=True):
                    a, b, c = st.columns([3, 2, 1])

                    with a:
                        st.subheader(e.get("nombre", "Candidato"))
                        st.write(e.get("puesto", "Sin puesto"))

                    with b:
                        st.write(f"📅 {e.get('fecha','')}")
                        st.write(f"🕐 {e.get('hora','')}")
                        st.write(f"📍 {e.get('lugar','')}")

                    with c:
                        st.write(e.get("estado", "🗓️ Programada"))

                        telefono = ""
                        candidato_rel = next(
                            (x for x in candidatos if str(x.get("id", "")) == str(e.get("candidato_id", ""))),
                            None,
                        )
                        if candidato_rel:
                            telefono = str(candidato_rel.get("telefono", ""))
                        telefono_limpio = re.sub(r"\D", "", telefono)
                        if len(telefono_limpio) == 10:
                            telefono_limpio = "52" + telefono_limpio

                        mensaje_whatsapp = (
                            f"Hola {e.get('nombre', 'candidato')}, te contactamos de CurriculAI para confirmar tu entrevista. "
                            f"Puesto: {e.get('puesto', 'por definir')}. Fecha: {e.get('fecha', '')}. "
                            f"Hora: {e.get('hora', '')}. Lugar o enlace: {e.get('lugar', '')}. "
                            "Por favor, confírmanos tu asistencia. ¡Gracias!"
                        )
                        if len(telefono_limpio) >= 10 and "No contiene" not in telefono:
                            st.link_button(
                                "💬 Notificar por WhatsApp",
                                f"https://wa.me/{telefono_limpio}?text={quote(mensaje_whatsapp)}",
                                use_container_width=True,
                            )
                        else:
                            st.caption("Agrega un teléfono válido al CV para abrir WhatsApp.")

                        if st.button("⭐ Finalista", key=f"final_{e.get('id')}"):
                            r = api_put(
                                f"/api/v1/entrevistas/{e.get('id')}/estado",
                                {
                                    "estado": "⭐ Finalista",
                                    "tipo_finalista": "En capacitación",
                                },
                            )
                            if r is not None and r.ok:
                                st.success("Marcado como finalista.")
                                st.rerun()
        else:
            st.info("No hay entrevistas programadas.")

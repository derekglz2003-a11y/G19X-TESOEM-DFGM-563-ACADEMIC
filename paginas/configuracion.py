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

        st.title("⚙️ Configuración")
        st.caption("Preferencias de la plataforma.")

        st.subheader("Conexión")
        st.code(API_URL)

        st.subheader("Motor de IA")
        st.info(
            "La interfaz queda preparada para integrar Gemini y OpenAI. "
            "La conexión de los modelos se hará en el backend para mantener "
            "la lógica de IA separada de la interfaz."
        )

        st.subheader("Mantenimiento")

        if st.button("🧹 Limpiar pool completo de candidatos", type="secondary"):
            st.warning(
                "Esta acción elimina candidatos y evaluaciones de la base de datos."
            )
            if st.button("Confirmar eliminación", type="primary"):
                r = api_delete("/api/v1/limpiar-pool")
                if r is not None and r.ok:
                    st.success("Pool limpiado correctamente.")
                    st.rerun()
                else:
                    st.error("No fue posible limpiar la base de datos.")

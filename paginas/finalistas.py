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

        st.title("⭐ Finalistas")
        st.caption("Candidatos destacados después del proceso de evaluación y entrevista.")

        finalistas = [
            e for e in entrevistas
            if "final" in str(e.get("estado", "")).lower()
            or "finalista" in str(e.get("tipo_finalista", "")).lower()
        ]

        if finalistas:
            for f in finalistas:
                with st.container(border=True):
                    st.subheader(f.get("nombre", "Candidato"))
                    st.write(f"**Puesto:** {f.get('puesto','')}")
                    st.write(f"**Estado:** {f.get('estado','')}")
                    st.write(f"**Etapa:** {f.get('tipo_finalista','En capacitación')}")
        else:
            st.markdown(
                '<div class="empty">Todavía no tienes candidatos marcados como finalistas.</div>',
                unsafe_allow_html=True,
            )

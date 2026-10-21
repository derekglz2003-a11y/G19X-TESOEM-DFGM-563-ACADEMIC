"""Opciones de sistema; operaciones destructivas bajo confirmación explícita."""
import streamlit as st
from servicios.api import API_URL, api_delete

def render(ctx):
    st.markdown('<div class="cai-intro"><div><div class="cai-kicker">ADMINISTRACIÓN</div><h1>Configuración</h1><p class="cai-descripcion">Consulta la conexión, el motor inteligente y las herramientas de mantenimiento.</p></div></div>',unsafe_allow_html=True)
    a,b=st.columns(2,gap="large")
    with a:
        with st.container(border=True):
            st.subheader("Conexión del sistema")
            st.caption("Conexión configurada")
            st.write("Servidor local" if API_URL.startswith(("http://127.0.0.1", "http://localhost")) else "Servidor remoto (dirección oculta por privacidad)")
            st.info("Las credenciales se configuran en variables de entorno y no se muestran en la interfaz.")
    with b:
        with st.container(border=True):
            st.subheader("Motor inteligente")
            st.write("Análisis semántico: modelo de embeddings configurado en el backend.")
            st.write("Generación de descripciones: integración con Gemini cuando está configurada.")
            st.caption("Una integración no debe considerarse operativa hasta realizar pruebas reales.")
    st.markdown('<div class="cai-section">Preferencias de visualización</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.caption("Reinicia los filtros y vuelve a Inicio; no elimina ningún registro de la base de datos.")
        if st.button("Reiniciar vista", key="reiniciar_desde_configuracion"):
            reiniciar = ctx.get("reiniciar_vista")
            if callable(reiniciar):
                reiniciar()
            else:
                st.warning("No fue posible reiniciar la vista.")
    st.markdown('<div class="cai-section">Mantenimiento</div>',unsafe_allow_html=True)
    with st.container(border=True):
        st.warning("La limpieza total del pool elimina expedientes y sus evaluaciones. Esta acción no se puede deshacer.")
        st.caption("No afecta directamente las vacantes creadas.")
        confirmacion=st.checkbox("Confirmo que deseo eliminar TODOS los candidatos",key="conf_borrar_pool")
        palabra=st.text_input('Escribe ELIMINAR para habilitar la acción',key="cai_palabra_borrar")
        if st.button("Limpiar pool completo",disabled=not(confirmacion and palabra=="ELIMINAR")):
            resp=api_delete("/api/v1/limpiar-pool")
            if resp is not None and resp.ok:
                st.success("Pool eliminado de la base de datos.")
                st.rerun()
            else:
                st.error("No se pudo limpiar el pool. Verifica el servidor y los permisos.")
    st.caption("Antes de publicar CurriculAi es necesario implementar autenticación, autorización por roles y protección de los datos personales en FastAPI.")

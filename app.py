import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(
    page_title="Plataforma de Reclutamiento & IA",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección de estilos CSS para componentes visuales
st.markdown("""
<style>
    .skill-badge {
        display: inline-block;
        background-color: #1e293b;
        color: #38bdf8;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin: 2px;
        border: 1px solid #0284c7;
    }
    .metric-card {
        background-color: #0f172a;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE COMUNICACIÓN CON EL BACKEND ---
def obtener_vacantes():
    try:
        res = requests.get(f"{API_URL}/vacantes", timeout=3)
        return res.json() if res.status_code == 200 else []
    except Exception:
        return []

def crear_vacante(titulo, descripcion):
    return requests.post(f"{API_URL}/vacantes", data={"titulo": titulo, "descripcion": descripcion})

def eliminar_vacante(vacante_id):
    return requests.delete(f"{API_URL}/vacantes/{vacante_id}")

def enviar_cvs(vacante_id, archivos, modo="detallado"):
    files = [("files", (f.name, f.getvalue(), f.type or "application/pdf")) for f in archivos]
    return requests.post(f"{API_URL}/analizar-cvs/{vacante_id}", files=files, params={"modo": modo})

def obtener_ranking(vacante_id):
    res = requests.get(f"{API_URL}/ranking/{vacante_id}")
    return res.json() if res.status_code == 200 else []

def obtener_analitica(vacante_id):
    res = requests.get(f"{API_URL}/analytics/{vacante_id}")
    return res.json() if res.status_code == 200 else {}

# --- PANEL LATERAL (SIDEBAR) ---
st.sidebar.title("💼 Panel Principal")
st.sidebar.markdown("---")
st.sidebar.subheader("📋 Vacantes Registradas")

vacantes = obtener_vacantes()

if vacantes:
    opciones = {f"#{v['id']} — {v['titulo']}": v for v in vacantes}
    seleccion = st.sidebar.selectbox("Seleccionar Vacante Activa", list(opciones.keys()))
    vacante_actual = opciones[seleccion]
    
    with st.sidebar.expander("📌 Ver Requisitos de la Vacante", expanded=False):
        st.write(vacante_actual['descripcion'])
    
    if st.sidebar.button("🗑️ Eliminar Vacante", type="secondary"):
        eliminar_vacante(vacante_actual['id'])
        st.sidebar.success("Vacante eliminada.")
        st.rerun()
else:
    vacante_actual = None
    st.sidebar.info("No hay vacantes activas. Registra una abajo.")

st.sidebar.markdown("---")
with st.sidebar.expander("➕ Crear Nueva Vacante", expanded=True):
    with st.form("form_vacante"):
        titulo = st.text_input("Título del Puesto", placeholder="Ej. Chofer de Ruta / Desarrollador / Contador")
        desc = st.text_area("Descripción y Requisitos", placeholder="Detalla licencias, responsabilidades, herramientas o conocimientos requeridos...")
        if st.form_submit_button("💾 Guardar Vacante", use_container_width=True):
            if titulo and desc:
                crear_vacante(titulo, desc)
                st.sidebar.success("Vacante creada.")
                st.rerun()
            else:
                st.sidebar.warning("Por favor completa ambos campos.")

# --- CUERPO PRINCIPAL DE LA APLICACIÓN ---
if vacante_actual:
    st.title(f"🔍 Vacante: {vacante_actual['titulo']}")
    
    tab_eval, tab_dash = st.tabs(["🏆 Ranking & Evaluación de Candidatos", "📊 Dashboard Analítico"])
    
    # --- PESTAÑA 1: EVALUACIÓN Y RANKING ---
    with tab_eval:
        st.subheader("📤 Procesamiento de Documentos")
        
        col_up1, col_up2 = st.columns([3, 1])
        with col_up1:
            archivos = st.file_uploader(
                "Selecciona o arrastra archivos PDF (CVs o Reportes de Entrevista)", 
                type=["pdf"], 
                accept_multiple_files=True
            )
        with col_up2:
            modo_reporte = st.radio(
                "Nivel de detalle del reporte:",
                options=["detallado", "corto"],
                format_func=lambda x: "📄 Reporte Detallado" if x == "detallado" else "⚡ Resumen Corto",
                index=0
            )
        
        if archivos and st.button("🚀 Iniciar Análisis con IA Semántica", type="primary"):
            with st.spinner("Parseando PDFs, extrayendo datos y calculando vectores de compatibilidad..."):
                res = enviar_cvs(vacante_actual['id'], archivos, modo=modo_reporte)
                if res.status_code == 200:
                    st.success("¡Evaluación finalizada e integrada a la base de datos!")
                    st.rerun()
                else:
                    st.error("Error al procesar los archivos en el servidor.")
                    
        st.markdown("---")
        
        ranking = obtener_ranking(vacante_actual['id'])
        
        if ranking:
            # BARRA DE HERRAMIENTAS Y FILTROS
            col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
            with col_f1:
                min_score = st.slider("🎯 Match Mínimo (%)", 0, 100, 20)
            with col_f2:
                skill_filtro = st.text_input("🔍 Filtrar por Skill (Ej. Licencia, SQL, Excel)", "")
            with col_f3:
                st.write(" ")
                st.write(" ")
                # BOTÓN DE EXPORTACIÓN A CSV
                df_export = pd.DataFrame(ranking)
                csv_data = df_export.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Exportar Reporte (CSV)",
                    data=csv_data,
                    file_name=f"ranking_vacante_{vacante_actual['id']}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            # FILTRADO DE CANDIDATOS
            candidatos_filtrados = [
                c for c in ranking 
                if c['score_similitud'] >= min_score 
                and (not skill_filtro or skill_filtro.lower() in (c['skills'] or '').lower())
            ]
            
            st.caption(f"Mostrando **{len(candidatos_filtrados)}** de **{len(ranking)}** candidatos evaluados.")
            
            # MOSTRAR CADA CANDIDATO EN UN EXPANSOR ESTILO ACORDEÓN
            for cand in candidatos_filtrados:
                score = cand['score_similitud']
                
                with st.expander(f"⭐ Match: {score}% — {cand['nombre_archivo']}"):
                    col_left, col_right = st.columns([1, 1])
                    
                    with col_left:
                        st.markdown("#### 👤 Información de Contacto")
                        st.write(f"📧 **Correo:** {cand['email']}")
                        st.write(f"📞 **Teléfono:** {cand['telefono']}")
                        
                        st.markdown("**🛠️ Skills Identificadas:**")
                        if cand['skills']:
                            skills_list = [s.strip() for s in cand['skills'].split(",") if s.strip()]
                            skills_html = "".join([f"<span class='skill-badge'>{s}</span>" for s in skills_list])
                            st.markdown(skills_html, unsafe_allow_html=True)
                        else:
                            st.caption("Sin habilidades clave detectadas explícitamente.")
                        
                        st.write("")
                        # Botón para descargar el PDF Original
                        pdf_res = requests.get(f"{API_URL}/candidatos/{cand['candidato_id']}/pdf")
                        if pdf_res.status_code == 200:
                            st.download_button(
                                label="📄 Descargar CV PDF Original",
                                data=pdf_res.content,
                                file_name=cand['nombre_archivo'],
                                mime="application/pdf",
                                key=f"pdf_btn_{cand['candidato_id']}",
                                use_container_width=True
                            )
                    
                    with col_right:
                        st.markdown("#### 🧠 Evaluación Cualitativa de IA")
                        st.markdown(f"{cand['resumen']}")
                        st.markdown(f"{cand['justificacion']}")
                        
                        # EXTRACTO CRUDO DEL CV
                        with st.expander("📖 Ver Extracto Crudo de Texto Extraído", expanded=False):
                            st.caption(cand.get('extracto', 'Sin vista previa de texto.'))
        else:
            st.info("No hay candidatos evaluados en esta vacante. Carga archivos PDF arriba para comenzar.")

    # --- PESTAÑA 2: DASHBOARD Y ANALÍTICA DE SELECCIÓN ---
    with tab_dash:
        stats = obtener_analitica(vacante_actual['id'])
        
        if stats and stats.get("total", 0) > 0:
            st.markdown("### 📊 Indicadores Clave de Reclutamiento")
            
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Total Candidatos Evaluados", stats["total"])
            kpi2.metric("Promedio de Compatibilidad", f"{stats['promedio']}%")
            kpi3.metric("Candidatos Altamente Viables (>65%)", stats["distribucion"].get("Alto (>65%)", 0))
            
            st.markdown("---")
            
            g_col1, g_col2 = st.columns(2)
            
            with g_col1:
                st.markdown("#### 🎯 Distribución de Compatibilidad")
                df_dist = pd.DataFrame(list(stats["distribucion"].items()), columns=["Categoría", "Cantidad"])
                st.bar_chart(df_dist.set_index("Categoría"), color="#0284c7")
                
            with g_col2:
                st.markdown("#### 🛠️ Top 10 Habilidades en el Grupo de Candidatos")
                if stats["skills_frecuentes"]:
                    df_skills = pd.DataFrame(list(stats["skills_frecuentes"].items()), columns=["Habilidad", "Apariciones"])
                    st.bar_chart(df_skills.set_index("Habilidad"), color="#38bdf8")
                else:
                    st.info("No hay suficientes skills registradas para graficar.")
        else:
            st.info("Sube candidatos a esta vacante para generar analíticas en tiempo real.")
else:
    st.warning("Selecciona una vacante en el panel izquierdo o crea una nueva para comenzar.")
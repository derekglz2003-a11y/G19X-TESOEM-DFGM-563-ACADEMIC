from html import escape
import math
import streamlit as st

from servicios.api import api_post, api_get, api_put, api_delete

ESTADOS = ["En revisión", "Preseleccionado", "Descartado", "Entrevista", "Finalista", "Aceptado", "Rechazado"]


def _txt(v, n=220):
    return escape(str(v or "")[:n], quote=True)


def _err(r):
    if r is None:
        return "No hay conexión con FastAPI."
    try:
        return str(r.json().get("detail") or r.text)[:350]
    except Exception:
        return str(getattr(r, "text", "Error"))[:350]


def _flash(msg):
    st.session_state["flash_candidatos"] = msg
    st.rerun()


def _paginate(items, key, per_page=4):
    total = max(1, math.ceil(len(items) / per_page))
    page = min(max(1, st.session_state.get(key, 1)), total)
    st.session_state[key] = page
    return items[(page - 1) * per_page: page * per_page], page, total


def render(ctx):
    candidatos = ctx.get("candidatos") or []
    vacantes = ctx.get("vacantes") or []
    st.markdown('<div class="cai-intro"><div><div class="cai-kicker">GESTIÓN DE TALENTO</div><h1>Candidatos</h1><p class="cai-descripcion">Carga currículums, encuentra perfiles más rápido y administra expedientes sin estar deslizando de más.</p></div></div>', unsafe_allow_html=True)

    aviso = st.session_state.pop("flash_candidatos", None)
    detalles = st.session_state.pop("flash_candidatos_errores", [])
    if aviso:
        if aviso.startswith("¡0 candidato(s)") and detalles:
            st.warning(aviso)
        else:
            st.success(aviso)
    if detalles:
        st.error("No se pudieron procesar algunos archivos:")
        for detalle in detalles:
            st.write(f"• {detalle}")

    with st.expander("+ Cargar nuevos currículums", expanded=not bool(candidatos)):
        archivos = st.file_uploader(
            "Selecciona archivos",
            type=["pdf", "docx", "txt", "png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
        )
        if st.button("Analizar y registrar currículums", disabled=not archivos, type="primary", use_container_width=True):
            files = [("files", (f.name, f.getvalue(), f.type or "application/octet-stream")) for f in archivos]
            with st.spinner("Extrayendo datos y registrando currículums..."):
                r = api_post("/api/v1/analizar-cvs-masivo", files=files)
            if r is not None and r.ok:
                resultado = r.json()
                st.session_state["flash_candidatos"] = resultado.get(
                    "mensaje", "Currículums procesados"
                )
                st.session_state["flash_candidatos_errores"] = resultado.get(
                    "detalles_tecnicos", []
                )
                st.rerun()
            else:
                st.error(_err(r))

    if not candidatos:
        st.info("Todavía no hay candidatos registrados.")
        return

    st.markdown('<div class="cai-section">Expedientes registrados</div>', unsafe_allow_html=True)
    f1, f2 = st.columns([1.5, 1], gap="small")
    with f1:
        buscar = st.text_input("Buscar candidato", placeholder="Nombre, habilidades, experiencia o puesto...")
    with f2:
        directo = st.selectbox("Ir directo a un expediente", ["Todos"] + [f"{c.get('nombre') or 'Sin nombre'} · #{c.get('id')}" for c in candidatos])

    visibles = candidatos[:]
    if buscar.strip():
        q = buscar.casefold().strip()
        visibles = [c for c in visibles if q in " ".join(str(c.get(k) or "") for k in ("nombre", "perfil_destacado", "skills", "experiencia", "email")).casefold()]
    if directo != "Todos":
        cid = directo.split("#")[-1].strip()
        visibles = [c for c in visibles if str(c.get("id")) == cid]

    items, pagina, total = _paginate(visibles, "page_candidatos", per_page=4)
    st.caption(f"{len(visibles)} de {len(candidatos)} candidatos · página {pagina} de {total}")
    n1, n2 = st.columns(2)
    with n1:
        if st.button("← Anterior", key="cand_prev", disabled=pagina <= 1):
            st.session_state["page_candidatos"] = pagina - 1
            st.rerun()
    with n2:
        if st.button("Siguiente →", key="cand_next", disabled=pagina >= total):
            st.session_state["page_candidatos"] = pagina + 1
            st.rerun()

    for i in range(0, len(items), 2):
        cols = st.columns(2, gap="large")
        for col, c in zip(cols, items[i:i + 2]):
            cid = c.get("id")
            with col:
                st.markdown(
                    f'<div class="cai-item-card"><div class="cai-item-banner"><div><div class="cai-pretitle">Expediente #{_txt(cid,10)}</div><div class="cai-title">{_txt(c.get("nombre") or "Sin nombre", 60)}</div></div><span class="cai-icon">◎</span></div><div class="cai-item-body"><span class="cai-tag">{_txt(c.get("perfil_destacado") or "Perfil general", 50)}</span><div class="cai-item-meta">{_txt(c.get("email") or "Sin correo", 70)} · {_txt(c.get("telefono") or "Sin teléfono", 30)}</div><div class="cai-item-copy">{_txt(c.get("skills") or "Sin habilidades detectadas", 180)}</div></div></div>',
                    unsafe_allow_html=True,
                )
                with st.expander("Consultar y administrar expediente"):
                    t1, t2, t3, t4 = st.tabs(["Perfil", "Seguimiento", "Editar", "Eliminar"])
                    with t1:
                        st.write("**Experiencia:**", c.get("experiencia") or "No disponible")
                        st.write("**Fortalezas:**", c.get("puntos_fuertes") or "No disponible")
                        st.text_area("Texto extraído del CV", value=str(c.get("texto_completo") or "No disponible"), disabled=True, height=170, key=f"cv_{cid}")
                    with t2:
                        if not vacantes:
                            st.info("Primero registra una vacante para asignarle una etapa a este candidato.")
                        else:
                            opciones = {f"{v.get('titulo')} · #{v.get('id')}": v for v in vacantes}
                            seleccion = st.selectbox("Vacante", list(opciones), key=f"seg_v_{cid}")
                            vac = opciones[seleccion]
                            vid = vac.get("id")
                            seguimientos = api_get(f"/api/v1/seguimientos?vacante_id={vid}", [])
                            estado = next((s.get("estado") for s in seguimientos if str(s.get("candidato_id")) == str(cid)), "En revisión") if isinstance(seguimientos, list) else "En revisión"
                            with st.form(f"estado_form_{cid}_{vid}"):
                                nuevo = st.selectbox("Estado", ESTADOS, index=ESTADOS.index(estado) if estado in ESTADOS else 0)
                                guardar = st.form_submit_button("Guardar estado", type="primary")
                            if guardar:
                                r = api_put(f"/api/v1/seguimientos/{vid}/{cid}", {"estado": nuevo})
                                if r is not None and r.ok:
                                    _flash("Seguimiento actualizado.")
                                else:
                                    st.error(_err(r))
                    with t3:
                        with st.form(f"edit_c_{cid}"):
                            nombre = st.text_input("Nombre", value=str(c.get("nombre") or ""))
                            correo = st.text_input("Correo", value=str(c.get("email") or ""))
                            telefono = st.text_input("Teléfono", value=str(c.get("telefono") or ""))
                            perfil = st.text_input("Perfil", value=str(c.get("perfil_destacado") or ""))
                            skills = st.text_area("Habilidades", value=str(c.get("skills") or ""), height=90)
                            experiencia = st.text_area("Experiencia", value=str(c.get("experiencia") or ""), height=120)
                            guardar = st.form_submit_button("Guardar cambios", type="primary")
                        if guardar:
                            r = api_put(
                                f"/api/v1/candidatos/{cid}",
                                {
                                    "nombre": nombre,
                                    "email": correo,
                                    "telefono": telefono,
                                    "perfil_destacado": perfil,
                                    "skills": skills,
                                    "experiencia": experiencia,
                                },
                            )
                            if r is not None and r.ok:
                                _flash("Candidato actualizado.")
                            else:
                                st.error(_err(r))
                    with t4:
                        st.warning("Eliminar sólo el CV conserva al candidato. Eliminar expediente borra el registro completo.")
                        accion = st.radio("Acción", ["Sólo CV", "Expediente completo"], horizontal=True, key=f"delopt_{cid}")
                        confirma = st.checkbox("Confirmo esta acción", key=f"delconf_{cid}")
                        if st.button("Eliminar definitivamente", key=f"delete_c_{cid}", disabled=not confirma, use_container_width=True):
                            url = f"/api/v1/candidatos/{cid}/cv" if accion == "Sólo CV" else f"/api/v1/candidatos/{cid}"
                            r = api_delete(url)
                            if r is not None and r.ok:
                                _flash("Eliminación realizada.")
                            else:
                                st.error(_err(r))

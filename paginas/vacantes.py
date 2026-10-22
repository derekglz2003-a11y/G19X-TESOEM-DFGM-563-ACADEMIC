from datetime import date, time
from html import escape
import math
import streamlit as st

from servicios.api import api_get, api_post, api_post_form, api_put, api_delete
from servicios.whatsapp import enviar_invitacion_entrevista

ESTADOS = ["En revisión", "Preseleccionado", "Descartado", "Entrevista", "Finalista", "Aceptado", "Rechazado"]


def _txt(v, n=180):
    return escape(str(v or "")[:n], quote=True)


def _error(r):
    if r is None:
        return "No hay conexión con FastAPI."
    try:
        payload = r.json()
        return str(payload.get("detail") or payload.get("mensaje") or r.text)[:350]
    except Exception:
        return str(getattr(r, "text", "Error de comunicación"))[:350]


def _flash(msg):
    st.session_state["flash_vacantes"] = msg
    st.rerun()


def _paginate(items, key, per_page=4):
    total = max(1, math.ceil(len(items) / per_page))
    page = st.session_state.get(key, 1)
    page = min(max(1, page), total)
    st.session_state[key] = page
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], page, total


def encabezado():
    st.markdown('<div class="cai-intro"><div><div class="cai-kicker">CENTRO DE RECLUTAMIENTO</div><h1>Vacantes y talento</h1><p class="cai-descripcion">Administra puestos, consulta candidatos y ejecuta el flujo de reclutamiento desde una sola vista.</p></div></div>', unsafe_allow_html=True)


def crear_vacante():
    if st.session_state.pop("reset_nueva_vac", False):
        for k in ("vacante_titulo", "vacante_descripcion", "vacante_necesidades"):
            st.session_state.pop(k, None)
    descripcion_recien_generada = "desc_generada_tmp" in st.session_state
    if descripcion_recien_generada:
        st.session_state["vacante_descripcion"] = st.session_state.pop("desc_generada_tmp")
    with st.expander("+ Crear nueva vacante", expanded=descripcion_recien_generada):
        st.caption("Escribe el puesto y, si quieres, deja que la IA estructure la descripción automáticamente.")
        c1, c2 = st.columns([1.15, 1], gap="large")
        with c1:
            titulo = st.text_input("Nombre del puesto", key="vacante_titulo", placeholder="Ej. Analista de datos")
            descripcion = st.text_area(
                "Descripción estructurada del puesto",
                key="vacante_descripcion",
                height=230,
                placeholder="La IA puede ayudarte a generar este bloque completo con responsabilidades, requisitos y habilidades.",
            )
        with c2:
            necesidades = st.text_area(
                "¿Qué debe cubrir el puesto?",
                key="vacante_necesidades",
                height=140,
                placeholder="Ej. experiencia mínima, actividades principales, modalidad, herramientas, horario, perfil deseado...",
            )
            st.caption("Tip: con solo el título del puesto y estas necesidades, la IA te arma una base profesional.")
            if st.button("Estructurar con IA", key="vacante_ia", use_container_width=True):
                if not titulo.strip():
                    st.warning("Primero escribe el nombre del puesto.")
                else:
                    with st.spinner("Generando estructura del puesto..."):
                        r = api_post(
                            "/api/v1/generar-descripcion",
                            data={
                                "titulo": titulo.strip(),
                                "descripcion": descripcion.strip(),
                                "contexto": necesidades.strip(),
                            },
                        )
                    if r is not None and r.ok:
                        resultado = r.json()
                        propuesta = resultado.get("descripcion", "")
                        if propuesta:
                            st.session_state["desc_generada_tmp"] = propuesta
                            mensaje = "La descripción apareció en el formulario. Revísala y pulsa Guardar nueva vacante."
                            if resultado.get("criterios_omitidos"):
                                mensaje += " Se omitieron criterios de sexo, edad o apariencia."
                            _flash(mensaje)
                        else:
                            st.error("Gemini respondió sin una descripción de puesto.")
                    else:
                        st.error(_error(r))
            if st.button("Guardar nueva vacante", key="vacante_guardar", type="primary", use_container_width=True):
                if not titulo.strip() or not descripcion.strip():
                    st.warning("El nombre del puesto y la descripción son obligatorios.")
                else:
                    r = api_post_form("/api/v1/vacantes", {"titulo": titulo.strip(), "descripcion": descripcion.strip()})
                    if r is not None and r.ok:
                        st.session_state["vacante_activa"] = r.json().get("id")
                        st.session_state["reset_nueva_vac"] = True
                        _flash("Vacante creada correctamente.")
                    else:
                        st.error(_error(r))


def tarjeta_vacante(v):
    vid = v.get("id")
    st.markdown(
        f'<div class="cai-item-card"><div class="cai-item-banner"><div><div class="cai-pretitle">Vacante #{_txt(vid,12)}</div><div class="cai-title">{_txt(v.get("titulo") or "Vacante", 55)}</div></div><span class="cai-icon">▣</span></div><div class="cai-item-body"><span class="cai-tag">Registrada</span><div class="cai-item-meta">{_txt((v.get("descripcion") or "")[:120] or "Sin descripción",140)}</div></div></div>',
        unsafe_allow_html=True,
    )
    b1, b2 = st.columns(2, gap="small")
    with b1:
        if st.button("Gestionar", key=f"abrir_vac_{vid}", use_container_width=True):
            st.session_state["vacante_activa"] = vid
            st.rerun()
    with b2:
        if st.button("Editar", key=f"editar_directo_vac_{vid}", use_container_width=True):
            st.session_state["vacante_activa"] = vid
            st.session_state["modo_edicion_vacante"] = True
            st.rerun()


def panel_vacante(v, candidatos, entrevistas):
    vid = v.get("id")
    ranking = api_get(f"/api/v1/ranking/{vid}", [])
    ranking = ranking if isinstance(ranking, list) else []
    scores = {str(r.get("candidato_id")): r for r in ranking}
    seguimientos = api_get(f"/api/v1/seguimientos?vacante_id={vid}", [])
    seguimientos = seguimientos if isinstance(seguimientos, list) else []
    estados = {str(s.get("candidato_id")): s.get("estado") for s in seguimientos}

    st.markdown(f'<div class="cai-kicker">Vacante activa · gestión en esta misma pantalla</div><h2 style="margin-top:0">{_txt(v.get("titulo") or "Vacante", 70)}</h2>', unsafe_allow_html=True)
    st.markdown(f'<div class="cai-outline-box">{_txt(v.get("descripcion") or "Sin descripción registrada.", 1200).replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

    a1, a2, a3 = st.columns([1, 1, 1], gap="small")
    with a1:
        if st.button("Analizar compatibilidad con IA", key=f"eva_{vid}", use_container_width=True, type="primary"):
            with st.spinner("Procesando ranking..."):
                r = api_post(f"/api/v1/evaluar/{vid}")
            if r is not None and r.ok:
                info = r.json()
                omitidos = info.get("omitidos_sin_perfil", info.get("omitidos_sin_texto", 0))
                aviso = f"Evaluación completada: {info.get('evaluados', 0)} perfiles analizados."
                if omitidos:
                    aviso += f" {omitidos} perfil(es) sin información laboral suficiente; revisa sus expedientes."
                _flash(aviso)
            else:
                st.error(_error(r))
    with a2:
        editar_abierta = bool(st.session_state.pop("modo_edicion_vacante", False))
        with st.expander("Editar vacante", expanded=editar_abierta):
            with st.form(f"edit_vac_{vid}"):
                titulo = st.text_input("Nombre del puesto", value=str(v.get("titulo") or ""))
                descripcion = st.text_area("Descripción", value=str(v.get("descripcion") or ""), height=180)
                guardar = st.form_submit_button("Guardar cambios", type="primary")
            if guardar:
                r = api_put(f"/api/v1/vacantes/{vid}", {"titulo": titulo.strip(), "descripcion": descripcion.strip()})
                if r is not None and r.ok:
                    st.session_state.pop("modo_edicion_vacante", None)
                    _flash("Vacante actualizada.")
                else:
                    st.error(_error(r))
    with a3:
        with st.expander("Eliminar vacante"):
            confirma = st.checkbox("Confirmo eliminarla con su seguimiento", key=f"cf_v_{vid}")
            if st.button("Eliminar definitivamente", key=f"del_v_{vid}", disabled=not confirma, use_container_width=True):
                r = api_delete(f"/api/v1/vacantes/{vid}")
                if r is not None and r.ok:
                    st.session_state.pop("vacante_activa", None)
                    _flash("Vacante eliminada.")
                else:
                    st.error(_error(r))

    st.markdown('<div class="cai-section">Talento vinculado a la vacante</div>', unsafe_allow_html=True)
    if not candidatos:
        st.info("No hay candidatos cargados todavía.")
        return

    filtros1, filtros2, filtros3 = st.columns([1.6, 1.4, 1], gap="small")
    with filtros1:
        buscar = st.text_input("Buscar talento", key=f"buscar_tal_{vid}", placeholder="Nombre, habilidades o perfil...")
    with filtros2:
        nombres = [f"{c.get('nombre') or 'Sin nombre'} · #{c.get('id')}" for c in candidatos]
        directo = st.selectbox("Ir directo a un candidato", ["Todos"] + nombres, key=f"directo_{vid}")
    with filtros3:
        solo_con_match = st.checkbox("Solo con match IA", key=f"match_{vid}")

    lista = sorted(candidatos, key=lambda c: float(scores.get(str(c.get("id")), {}).get("score_similitud") or -1), reverse=True)
    if buscar.strip():
        q = buscar.casefold().strip()
        lista = [c for c in lista if q in " ".join(str(c.get(k) or "") for k in ("nombre", "perfil_destacado", "skills", "experiencia")).casefold()]
    if directo != "Todos":
        cid = directo.split("#")[-1].strip()
        lista = [c for c in lista if str(c.get("id")) == cid]
    if solo_con_match:
        lista = [c for c in lista if scores.get(str(c.get("id")))]

    pagina_items, pagina, total_paginas = _paginate(lista, f"page_talento_{vid}", per_page=4)
    st.caption(f"{len(lista)} candidato(s) encontrados · página {pagina} de {total_paginas}")
    nav1, nav2, _ = st.columns([1, 1, 5])
    with nav1:
        if st.button("← Anterior", key=f"prev_t_{vid}", disabled=pagina <= 1):
            st.session_state[f"page_talento_{vid}"] = pagina - 1
            st.rerun()
    with nav2:
        if st.button("Siguiente →", key=f"next_t_{vid}", disabled=pagina >= total_paginas):
            st.session_state[f"page_talento_{vid}"] = pagina + 1
            st.rerun()

    for cand in pagina_items:
        cid = cand.get("id")
        ev = scores.get(str(cid))
        estado = estados.get(str(cid), "En revisión")
        score = float(ev.get("score_similitud") or 0) if ev else None
        st.markdown(
            f'<div class="cai-item-card"><div class="cai-item-banner"><div><div class="cai-pretitle">Candidato #{_txt(cid,10)}</div><div class="cai-title">{_txt(cand.get("nombre") or "Sin nombre",65)}</div></div><span class="cai-icon">◉</span></div><div class="cai-item-body"><span class="cai-tag">{_txt(estado,28)}</span> '
            + (f'<span class="cai-tag gold">Match IA {score:.1f}%</span>' if score is not None else '')
            + f'<div class="cai-item-meta">{_txt(cand.get("perfil_destacado") or "Perfil general",70)}</div><div class="cai-item-copy">{_txt(cand.get("skills") or "Sin habilidades detectadas",220)}</div></div></div>',
            unsafe_allow_html=True,
        )
        quick1, quick2, quick3, quick4 = st.columns(4, gap="small")
        with quick1:
            if st.button("Preseleccionar", key=f"pre_{vid}_{cid}", use_container_width=True):
                r = api_put(f"/api/v1/seguimientos/{vid}/{cid}", {"estado": "Preseleccionado"})
                if r is not None and r.ok:
                    _flash("Candidato preseleccionado.")
                else:
                    st.error(_error(r))
        with quick2:
            if st.button("Descartar", key=f"desc_{vid}_{cid}", use_container_width=True):
                r = api_put(f"/api/v1/seguimientos/{vid}/{cid}", {"estado": "Descartado"})
                if r is not None and r.ok:
                    _flash("Candidato descartado para esta vacante.")
                else:
                    st.error(_error(r))
        entrevista_actual = next((e for e in entrevistas if str(e.get("candidato_id")) == str(cid)), None)
        with quick3:
            if entrevista_actual:
                if st.button("Marcar finalista", key=f"fin_{vid}_{cid}", use_container_width=True):
                    r = api_put(f"/api/v1/entrevistas/{entrevista_actual.get('id')}/decision", {"estado": "Finalista", "tipo_finalista": "En evaluación"})
                    if r is not None and r.ok:
                        api_put(f"/api/v1/seguimientos/{vid}/{cid}", {"estado": "Finalista"})
                        _flash("Candidato enviado a finalistas.")
                    else:
                        st.error(_error(r))
            else:
                st.button("Sin entrevista", key=f"no_ent_{vid}_{cid}", disabled=True, use_container_width=True)
        with quick4:
            if st.button("Ver gestión", key=f"ver_g_{vid}_{cid}", use_container_width=True):
                st.session_state[f"open_cand_{vid}_{cid}"] = not st.session_state.get(f"open_cand_{vid}_{cid}", False)
                st.rerun()

        with st.expander("Detalle, seguimiento y entrevista", expanded=st.session_state.get(f"open_cand_{vid}_{cid}", False)):
            t1, t2, t3 = st.tabs(["Resumen", "Seguimiento", "Entrevista"])
            with t1:
                if ev:
                    st.write(ev.get("resumen") or "Sin resumen generado.")
                    st.caption(ev.get("justificacion") or "Sin explicación adicional.")
                    st.progress(max(0.0, min(1.0, float(ev.get("score_similitud") or 0) / 100)), text=f"Compatibilidad: {float(ev.get('score_similitud') or 0):.1f}%")
                else:
                    st.info("Aún no hay evaluación IA para esta vacante.")
                st.write("**Experiencia:**", cand.get("experiencia") or "Sin experiencia registrada")
                st.write("**Correo:**", cand.get("email") or "Sin correo")
                st.write("**Teléfono:**", cand.get("telefono") or "Sin teléfono")
            with t2:
                with st.form(f"seg_{vid}_{cid}"):
                    nuevo = st.selectbox("Estado en esta vacante", ESTADOS, index=ESTADOS.index(estado) if estado in ESTADOS else 0)
                    guardar = st.form_submit_button("Guardar estado", type="primary")
                if guardar:
                    r = api_put(f"/api/v1/seguimientos/{vid}/{cid}", {"estado": nuevo})
                    if r is not None and r.ok:
                        _flash("Seguimiento actualizado.")
                    else:
                        st.error(_error(r))
            with t3:
                if entrevista_actual:
                    st.success(f"Entrevista registrada: {entrevista_actual.get('fecha')} · {entrevista_actual.get('hora')} · {entrevista_actual.get('lugar')}")
                    if st.button("Abrir módulo de entrevistas", key=f"ir_ent_{vid}_{cid}"):
                        navegar = st.session_state.get("cai_navegar")
                        if callable(navegar):
                            navegar("Entrevistas")
                else:
                    with st.form(f"ag_{vid}_{cid}"):
                        f1, f2, f3 = st.columns([1, 1, 1.4])
                        with f1:
                            fecha = st.date_input("Fecha", value=date.today(), key=f"fecha_{vid}_{cid}")
                        with f2:
                            hora = st.time_input("Hora", value=time(10, 0), key=f"hora_{vid}_{cid}")
                        with f3:
                            lugar = st.text_input("Lugar / enlace", value="Google Meet", key=f"lugar_{vid}_{cid}")
                        enviar_wa = st.checkbox("Enviar invitación por WhatsApp con UltraMsg", value=False,
                                                help="Requiere credenciales y autorización del candidato")
                        agenda = st.form_submit_button("Agendar entrevista", type="primary")
                    if agenda:
                        r = api_post(
                            "/api/v1/entrevistas",
                            data={
                                "candidato_id": cid,
                                "nombre": cand.get("nombre") or "Candidato",
                                "vacante_id": vid,
                                "puesto": v.get("titulo") or "Vacante",
                                "fecha": fecha.isoformat(),
                                "hora": hora.strftime("%H:%M"),
                                "lugar": lugar.strip(),
                            },
                        )
                        if r is not None and r.ok:
                            api_put(f"/api/v1/seguimientos/{vid}/{cid}", {"estado": "Entrevista"})
                            aviso = "Entrevista agendada correctamente."
                            if enviar_wa:
                                enviado, detalle, registrado = enviar_invitacion_entrevista(
                                    r.json().get("id"), cand, v.get("titulo") or "Vacante",
                                    fecha.isoformat(), hora.strftime("%H:%M"), lugar.strip()
                                )
                                aviso += (" Invitación aceptada por UltraMsg." if enviado else f" WhatsApp no enviado: {detalle}")
                                if not registrado:
                                    aviso += " No se guardó la bitácora de WhatsApp."
                            _flash(aviso)
                        else:
                            st.error(_error(r))


def render(ctx):
    ctx = ctx or {}
    st.session_state["cai_navegar"] = ctx.get("navegar")
    candidatos = ctx.get("candidatos") or []
    vacantes = ctx.get("vacantes") or []
    entrevistas = ctx.get("entrevistas") or []

    encabezado()
    aviso = st.session_state.pop("flash_vacantes", None)
    if aviso:
        st.success(aviso)

    crear_vacante()

    izquierda, derecha = st.columns([1.05, 1.5], gap="large")
    with izquierda:
        st.markdown('<div class="cai-section">Vacantes registradas</div>', unsafe_allow_html=True)
        filtro = st.text_input("Buscar vacante", placeholder="Puesto o descripción...")
        lista = vacantes[:]
        if filtro.strip():
            q = filtro.casefold().strip()
            lista = [v for v in lista if q in str(v.get("titulo") or "").casefold() or q in str(v.get("descripcion") or "").casefold()]
        items, pagina, total = _paginate(lista, "page_vacantes", per_page=4)
        st.caption(f"{len(lista)} vacante(s) · página {pagina} de {total}")
        p1, p2 = st.columns(2)
        with p1:
            if st.button("← Anterior", key="prev_vac", disabled=pagina <= 1):
                st.session_state["page_vacantes"] = pagina - 1
                st.rerun()
        with p2:
            if st.button("Siguiente →", key="next_vac", disabled=pagina >= total):
                st.session_state["page_vacantes"] = pagina + 1
                st.rerun()
        if not items:
            st.info("No hay vacantes registradas todavía.")
        for v in items:
            tarjeta_vacante(v)

    with derecha:
        vid = st.session_state.get("vacante_activa")
        actual = next((v for v in vacantes if str(v.get("id")) == str(vid)), None)
        if actual is None and vacantes:
            actual = vacantes[0]
            st.session_state["vacante_activa"] = actual.get("id")
        if actual:
            panel_vacante(actual, candidatos, entrevistas)
        else:
            st.markdown('<div class="cai-section">Selecciona una vacante</div>', unsafe_allow_html=True)
            st.info("Registra una vacante para comenzar a gestionar candidatos.")

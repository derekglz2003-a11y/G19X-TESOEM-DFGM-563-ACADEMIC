from datetime import date, time
from html import escape
import math
import streamlit as st

from servicios.api import api_get, api_get_respuesta, api_post, api_post_form, api_put, api_delete
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

def estilos_vacantes():
    """Estilos limitados a la página de vacantes. Nunca altera el menú superior."""
    st.markdown("""
    <style>
      .cai-vac-section-title{font-size:1.18rem;font-weight:800;color:#133553;margin:0.35rem 0 0.55rem}
      .cai-vac-active-label{letter-spacing:.13em;font-size:.75rem;font-weight:800;color:#1D4F7C;margin:0 0 .4rem}
      .cai-vac-active-head{border:1px solid #d5e1ee;border-radius:15px;padding:16px 19px;background:#fff;margin:0 0 12px}
      .cai-vac-active-name{font-size:1.6rem;font-weight:850;line-height:1.3;color:#153A60;margin:0}
      .cai-vac-active-tip{color:#657C8D;font-size:.88rem;margin-top:5px}
      .cai-vac-job{border:1px solid #d7e3ef;background:#fff;border-radius:14px;padding:13px 16px;margin:7px 0 3px}
      .cai-vac-job.active{background:#183B63;border-color:#183B63;color:#fff}
      .cai-vac-job .cai-vac-job-label{font-size:.72rem;font-weight:800;letter-spacing:.11em;opacity:.72}
      .cai-vac-job .cai-vac-job-title{font-size:1.06rem;font-weight:800;line-height:1.5}
      .cai-vac-job .cai-vac-job-state{font-size:.76rem;opacity:.8}
      .cai-vac-candidate{border:1px solid #d7e3ef;border-radius:14px;overflow:hidden;margin:4px 0 0;background:#fff}
      .cai-vac-candidate-head{background:#193B64;color:white;padding:12px 15px;display:flex;gap:12px;justify-content:space-between;align-items:center}
      .cai-vac-candidate-label{font-size:.69rem;font-weight:750;letter-spacing:.11em;opacity:.85}
      .cai-vac-candidate-name{font-size:1.07rem;line-height:1.4;font-weight:790;overflow-wrap:anywhere}
      .cai-vac-score{background:#e3f5ed;border:1px solid #c5e6d5;color:#0d6444;border-radius:20px;padding:6px 9px;font-size:.8rem;font-weight:850;white-space:nowrap}
      .cai-vac-score-pending{background:#eaf0f5;color:#31526e}
      .cai-vac-candidate-body{padding:12px 15px 14px}
      .cai-vac-tag{display:inline-block;border-radius:30px;background:#edf4fa;color:#244A6A;padding:5px 10px;font-weight:750;font-size:.74rem;margin-bottom:8px}
      .cai-vac-meta{font-size:.83rem;color:#647D90;margin:3px 0 8px;overflow-wrap:anywhere}
      .cai-vac-skills{font-size:.89rem;color:#1A3C5B;overflow-wrap:anywhere;min-height:28px}
      .cai-vac-note{font-size:.83rem;color:#6b8296;margin:0 0 10px}
      .cai-vac-candidate-foot{font-size:.8rem;color:#58738b;border-top:1px solid #e6edf4;margin-top:9px;padding-top:7px}
      /* Solo el selector de vacantes, no la navegación superior */
      [class*="st-key-cai_lista_vacantes"] div[data-testid="stButton"] > button{
          border:1px solid #d6e2ed;background:#fff;color:#173C63;text-align:left;
          justify-content:flex-start;min-height:45px;font-weight:750;
          border-radius:10px;margin-bottom:3px;
      }
      [class*="st-key-cai_lista_vacantes"] div[data-testid="stButton"] > button:hover{
          background:#eaf3fb;border-color:#79a8d1;color:#173C63
      }
    </style>""", unsafe_allow_html=True)


def _alternar(key):
    st.session_state[key] = not bool(st.session_state.get(key, False))
    st.rerun()


def tarjeta_vacante(v):
    """Selector inmediato; no hay que buscar ni paginar para escoger una vacante."""
    vid = v.get("id")
    activa = str(st.session_state.get("vacante_activa")) == str(vid)
    st.markdown(
        f'<div class="cai-vac-job{" active" if activa else ""}">'
        f'<div class="cai-vac-job-label">VACANTE #{_txt(vid, 12)}'
        f'{" · ACTIVA" if activa else ""}</div>'
        f'<div class="cai-vac-job-title">{_txt(v.get("titulo") or "Sin título", 95)}</div>'
        f'</div>', unsafe_allow_html=True,
    )
    if not activa:
        if st.button(f"Gestionar {str(v.get('titulo') or 'vacante')[:50]}", key=f"abrir_vac_{vid}", use_container_width=True):
            st.session_state["vacante_activa"] = vid
            st.rerun()


def acciones_vacante(v):
    """Cuatro acciones en una misma fila y descripción oculta hasta solicitarla."""
    vid = v.get("id")
    st.markdown(
        '<div class="cai-vac-active-label">VACANTE ACTIVA · GESTIÓN EN ESTA MISMA PANTALLA</div>'
        f'<div class="cai-vac-active-head"><div class="cai-vac-active-name">'
        f'{_txt(v.get("titulo") or "Vacante", 100)}</div></div>',
        unsafe_allow_html=True,
    )
    ver_key = f"cai_ver_texto_vac_{vid}"
    edit_key = f"cai_editar_vac_{vid}"
    delete_key = f"cai_eliminar_vac_{vid}"
    if st.session_state.pop("modo_edicion_vacante", False):
        st.session_state[edit_key] = True
    b1, b2, b3, b4 = st.columns([1, 1.65, 1.0, 1.05], gap="small")
    with b1:
        label = "Ocultar texto" if st.session_state.get(ver_key) else "Desplegar texto"
        if st.button(label, key=f"abrir_texto_{vid}", use_container_width=True):
            _alternar(ver_key)
    with b2:
        if st.button("Analizar compatibilidad con IA", key=f"eva_{vid}", type="primary", use_container_width=True):
            with st.spinner("Analizando perfiles laborales..."):
                respuesta = api_post(f"/api/v1/evaluar/{vid}")
            if respuesta is not None and respuesta.ok:
                info = respuesta.json()
                omitidos = info.get("omitidos_sin_perfil", info.get("omitidos_sin_texto", 0))
                aviso = f"Evaluación completada: {info.get('evaluados', 0)} perfiles analizados."
                if omitidos:
                    aviso += f" {omitidos} perfil(es) con información insuficiente."
                _flash(aviso)
            else:
                st.error(_error(respuesta))
    with b3:
        if st.button("Editar vacante", key=f"toggle_editar_vac_{vid}", use_container_width=True):
            st.session_state[delete_key] = False
            _alternar(edit_key)
    with b4:
        if st.button("Eliminar vacante", key=f"toggle_borrar_vac_{vid}", use_container_width=True):
            st.session_state[edit_key] = False
            _alternar(delete_key)

    # Publicar es una acción explícita: las vacantes antiguas no aparecen en el portal.
    publicaciones = api_get("/api/v1/publicaciones", [])
    if isinstance(publicaciones, list):
        publicada = any(str(p.get("vacante_id")) == str(vid) and p.get("publicada")
                        for p in publicaciones)
        info_pub, boton_pub = st.columns([2.8, 1.2], vertical_alignment="center")
        with info_pub:
            st.caption("Visible para candidatos" if publicada else "Borrador interno · no visible para candidatos")
        with boton_pub:
            if st.button("Retirar publicación" if publicada else "Publicar vacante",
                         key=f"pub_v_{vid}", use_container_width=True):
                r_pub = api_put(f"/api/v1/publicaciones/{vid}", {"publicada": not publicada})
                if r_pub is not None and r_pub.ok:
                    _flash("Publicación actualizada correctamente.")
                else:
                    st.error(_error(r_pub))

    if st.session_state.get(ver_key, False):
        with st.container(border=True):
            st.markdown("**Descripción completa del puesto**")
            # Markdown se renderiza sin HTML inseguro y respeta títulos/listas de Gemini.
            st.markdown(str(v.get("descripcion") or "Sin descripción registrada."))

    if st.session_state.get(edit_key, False):
        with st.container(border=True):
            st.markdown("**Editar vacante**")
            with st.form(f"edit_vac_{vid}"):
                titulo = st.text_input("Nombre del puesto", value=str(v.get("titulo") or ""))
                descripcion = st.text_area("Descripción", value=str(v.get("descripcion") or ""), height=200)
                guardar = st.form_submit_button("Guardar cambios", type="primary")
            if guardar:
                if not titulo.strip() or not descripcion.strip():
                    st.warning("Escribe el puesto y su descripción.")
                else:
                    respuesta = api_put(f"/api/v1/vacantes/{vid}", {"titulo": titulo.strip(), "descripcion": descripcion.strip()})
                    if respuesta is not None and respuesta.ok:
                        st.session_state[edit_key] = False
                        _flash("Vacante actualizada correctamente.")
                    else:
                        st.error(_error(respuesta))

    if st.session_state.get(delete_key, False):
        with st.container(border=True):
            st.warning("Esta acción elimina la vacante y sus seguimientos asociados.")
            confirma = st.checkbox("Confirmo que deseo eliminar esta vacante", key=f"cf_v_{vid}")
            if st.button("Eliminar definitivamente", key=f"del_v_{vid}", disabled=not confirma, use_container_width=True):
                respuesta = api_delete(f"/api/v1/vacantes/{vid}")
                if respuesta is not None and respuesta.ok:
                    st.session_state.pop("vacante_activa", None)
                    st.session_state.pop(delete_key, None)
                    _flash("Vacante eliminada correctamente.")
                else:
                    st.error(_error(respuesta))


def _detalle_candidato(cand, ev, estado, v, entrevista_actual, es_portal=False):
    """Conserva seguimiento, decisiones y agenda existentes en el MVP."""
    vid, cid = v.get("id"), cand.get("id")
    a1, a2, a3 = st.tabs(["Resumen", "Seguimiento", "Entrevista"])
    with a1:
        if ev:
            st.write(ev.get("resumen") or "Sin resumen generado.")
            st.caption(ev.get("justificacion") or "Sin explicación adicional.")
            score = float(ev.get("score_similitud") or 0)
            st.progress(max(0.0, min(1.0, score / 100)), text=f"Compatibilidad: {score:.1f}%")
        else:
            st.info("Sin evaluación IA para esta vacante. Usa «Analizar compatibilidad con IA».")
        st.write("**Experiencia:**", cand.get("experiencia") or "Sin experiencia registrada")
        st.write("**Correo:**", cand.get("email") or "Sin correo")
        st.write("**Teléfono:**", cand.get("telefono") or "Sin teléfono")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Preseleccionar", key=f"pre_{vid}_{cid}", use_container_width=True):
                respuesta = api_put(f"/api/v1/seguimientos/{vid}/{cid}", {"estado": "Preseleccionado"})
                if respuesta is not None and respuesta.ok:
                    _flash("Candidato preseleccionado.")
                else:
                    st.error(_error(respuesta))
        with col2:
            if st.button("Descartar", key=f"desc_{vid}_{cid}", use_container_width=True):
                respuesta = api_put(f"/api/v1/seguimientos/{vid}/{cid}", {"estado": "Descartado"})
                if respuesta is not None and respuesta.ok:
                    _flash("Candidato descartado para esta vacante.")
                else:
                    st.error(_error(respuesta))
        if es_portal:
            if st.button("Invitar a postularse en su cuenta", key=f"inv_{vid}_{cid}",
                         use_container_width=True):
                respuesta = api_post(f"/api/v1/invitaciones/{vid}/{cid}")
                if respuesta is not None and respuesta.ok:
                    _flash("Invitación enviada a la cuenta del candidato.")
                else:
                    st.error(_error(respuesta))
            st.caption("La invitación no equivale a una selección. La persona decide si postularse.")
        if entrevista_actual:
            if st.button("Marcar finalista", key=f"fin_{vid}_{cid}", use_container_width=True):
                respuesta = api_put(
                    f"/api/v1/entrevistas/{entrevista_actual.get('id')}/decision",
                    {"estado": "Finalista", "tipo_finalista": "En evaluación"},
                )
                if respuesta is not None and respuesta.ok:
                    api_put(f"/api/v1/seguimientos/{vid}/{cid}", {"estado": "Finalista"})
                    _flash("Candidato enviado a finalistas.")
                else:
                    st.error(_error(respuesta))
    with a2:
        with st.form(f"seg_{vid}_{cid}"):
            nuevo = st.selectbox("Estado para esta vacante", ESTADOS,
                                 index=ESTADOS.index(estado) if estado in ESTADOS else 0)
            guardar = st.form_submit_button("Guardar estado", type="primary")
        if guardar:
            respuesta = api_put(f"/api/v1/seguimientos/{vid}/{cid}", {"estado": nuevo})
            if respuesta is not None and respuesta.ok:
                _flash("Seguimiento actualizado.")
            else:
                st.error(_error(respuesta))
    with a3:
        if entrevista_actual:
            st.success(
                f"Entrevista registrada: {entrevista_actual.get('fecha')} · "
                f"{entrevista_actual.get('hora')} · {entrevista_actual.get('lugar')}"
            )
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
                respuesta = api_post(
                    "/api/v1/entrevistas",
                    data={
                        "candidato_id": cid, "nombre": cand.get("nombre") or "Candidato",
                        "vacante_id": vid, "puesto": v.get("titulo") or "Vacante",
                        "fecha": fecha.isoformat(), "hora": hora.strftime("%H:%M"),
                        "lugar": lugar.strip(),
                    },
                )
                if respuesta is not None and respuesta.ok:
                    api_put(f"/api/v1/seguimientos/{vid}/{cid}", {"estado": "Entrevista"})
                    aviso = "Entrevista agendada correctamente."
                    if enviar_wa:
                        enviado, detalle, registrado = enviar_invitacion_entrevista(
                            respuesta.json().get("id"), cand, v.get("titulo") or "Vacante",
                            fecha.isoformat(), hora.strftime("%H:%M"), lugar.strip(),
                        )
                        aviso += " Invitación aceptada por UltraMsg." if enviado else f" WhatsApp no enviado: {detalle}"
                        if not registrado:
                            aviso += " No se guardó la bitácora de WhatsApp."
                    _flash(aviso)
                else:
                    st.error(_error(respuesta))


def _tarjeta_candidato(cand, ev, estado, v, entrevistas, ids_portal=None):
    cid, vid = cand.get("id"), v.get("id")
    score = None
    if ev:
        try:
            score = max(0.0, min(100.0, float(ev.get("score_similitud") or 0)))
        except (TypeError, ValueError):
            score = None
    puntaje = f"{score:.1f}%" if score is not None else "Por evaluar"
    clase = "cai-vac-score" if score is not None else "cai-vac-score cai-vac-score-pending"
    mail = cand.get("email") or "Sin correo"
    telefono = cand.get("telefono") or "Sin teléfono"
    skills = cand.get("skills") or "Habilidades aún no registradas"
    st.markdown(
        f'<div class="cai-vac-candidate">'
        f'<div class="cai-vac-candidate-head"><div>'
        f'<div class="cai-vac-candidate-label">EXPEDIENTE #{_txt(cid,12)}</div>'
        f'<div class="cai-vac-candidate-name">{_txt(cand.get("nombre") or "Sin nombre",90)}</div>'
        f'</div><span class="{clase}">{_txt(puntaje,18)}</span></div>'
        f'<div class="cai-vac-candidate-body">'
        f'<span class="cai-vac-tag">{_txt(estado,30)}</span>'
        f'<div class="cai-vac-meta">{_txt(mail,85)} · {_txt(telefono,40)}</div>'
        f'<div class="cai-vac-skills">{_txt(skills,180)}</div>'
        f'</div></div>', unsafe_allow_html=True,
    )
    entrevista_actual = next((e for e in entrevistas
                              if str(e.get("candidato_id")) == str(cid)
                              and str(e.get("vacante_id")) == str(vid)), None)
    with st.expander("Consultar y administrar expediente"):
        _detalle_candidato(cand, ev, estado, v, entrevista_actual, str(cid) in (ids_portal or set()))


def panel_candidatos(v, candidatos, entrevistas):
    """Tarjetas a ancho completo, debajo de la vacante y sus acciones."""
    vid = v.get("id")
    st.markdown('<div class="cai-vac-section-title">Candidatos compatibles</div>', unsafe_allow_html=True)
    st.markdown('<div class="cai-vac-note">Perfiles ordenados por similitud para esta vacante. El porcentaje no es una probabilidad ni una decisión de contratación.</div>', unsafe_allow_html=True)

    respuesta = api_get_respuesta(f"/api/v1/ranking/{vid}")
    if respuesta is None:
        st.error("No se pudo conectar con FastAPI para consultar el ranking.")
        return
    if not respuesta.ok:
        st.error(f"No fue posible consultar el ranking (HTTP {respuesta.status_code}). No se mostrarán porcentajes inventados.")
        return
    try:
        ranking = respuesta.json()
    except ValueError:
        st.error("FastAPI devolvió una respuesta inválida para el ranking.")
        return
    if not isinstance(ranking, list):
        st.error("El ranking no tiene un formato válido.")
        return
    scores = {str(ev.get("candidato_id")): ev for ev in ranking}
    seguimientos = api_get(f"/api/v1/seguimientos?vacante_id={vid}", [])
    seguimientos = seguimientos if isinstance(seguimientos, list) else []
    estados = {str(s.get("candidato_id")): s.get("estado") for s in seguimientos}
    portal_cuentas = api_get("/api/v1/portal-candidatos", [])
    ids_portal = {str(u.get("expediente_administrativo_id")) for u in portal_cuentas
                  if u.get("expediente_administrativo_id") is not None} if isinstance(portal_cuentas, list) else set()

    if not candidatos:
        st.info("No hay candidatos registrados todavía. Carga sus CV desde el módulo Candidatos.")
        return
    if not ranking:
        st.info("Esta vacante aún no tiene un ranking. Presiona «Analizar compatibilidad con IA» para evaluarla.")

    izquierda, derecha = st.columns([1.6, 1], gap="medium")
    with izquierda:
        buscar = st.text_input("Buscar entre candidatos", key=f"buscar_tal_{vid}", placeholder="Nombre, habilidades o experiencia...")
    with derecha:
        solo_con_match = st.checkbox("Mostrar solo evaluados", key=f"match_{vid}")
    lista = sorted(
        candidatos,
        key=lambda c: float(scores.get(str(c.get("id")), {}).get("score_similitud") or -1),
        reverse=True,
    )
    if buscar.strip():
        termino = buscar.strip().casefold()
        lista = [c for c in lista if termino in " ".join(str(c.get(k) or "") for k in
                         ("nombre", "perfil_destacado", "skills", "experiencia")).casefold()]
    if solo_con_match:
        lista = [c for c in lista if str(c.get("id")) in scores]
    items, pagina, total = _paginate(lista, f"page_talento_{vid}", per_page=6)
    st.caption(f"{len(lista)} candidato(s) · página {pagina} de {total}")
    if not items:
        st.info("No hay candidatos con los filtros seleccionados.")
        return

    for i in range(0, len(items), 2):
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            candidato = items[i]
            _tarjeta_candidato(candidato, scores.get(str(candidato.get("id"))),
                               estados.get(str(candidato.get("id")), "En revisión"), v, entrevistas, ids_portal)
        if i + 1 < len(items):
            with c2:
                candidato = items[i + 1]
                _tarjeta_candidato(candidato, scores.get(str(candidato.get("id"))),
                                   estados.get(str(candidato.get("id")), "En revisión"), v, entrevistas, ids_portal)

    if total > 1:
        anterior, siguiente, _ = st.columns([1, 1, 4], gap="small")
        with anterior:
            if st.button("← Anterior", key=f"prev_t_{vid}", disabled=pagina <= 1):
                st.session_state[f"page_talento_{vid}"] = pagina - 1
                st.rerun()
        with siguiente:
            if st.button("Siguiente →", key=f"next_t_{vid}", disabled=pagina >= total):
                st.session_state[f"page_talento_{vid}"] = pagina + 1
                st.rerun()


def render(ctx):
    ctx = ctx or {}
    st.session_state["cai_navegar"] = ctx.get("navegar")
    candidatos = ctx.get("candidatos") or []
    vacantes = ctx.get("vacantes") or []
    entrevistas = ctx.get("entrevistas") or []

    estilos_vacantes()
    encabezado()
    aviso = st.session_state.pop("flash_vacantes", None)
    if aviso:
        st.success(aviso)
    crear_vacante()

    if not vacantes:
        st.info("No hay vacantes registradas. Crea una vacante para comenzar.")
        return
    vid = st.session_state.get("vacante_activa")
    actual = next((v for v in vacantes if str(v.get("id")) == str(vid)), None)
    if actual is None:
        actual = vacantes[0]
        st.session_state["vacante_activa"] = actual.get("id")

    col_lista, col_activa = st.columns([1, 1.8], gap="large")
    with col_lista:
        st.markdown('<div class="cai-vac-section-title">Vacantes registradas</div>', unsafe_allow_html=True)
        st.caption(f"{len(vacantes)} puesto(s) registrados · selecciona una tarjeta para gestionarla")
        with st.container(key="cai_lista_vacantes"):
            for vacante in vacantes:
                tarjeta_vacante(vacante)
    with col_activa:
        acciones_vacante(actual)

    st.divider()
    postulaciones = api_get(f"/api/v1/postulaciones-admin?vacante_id={actual.get('id')}", [])
    if isinstance(postulaciones, list):
        with st.expander(f"Postulaciones recibidas desde el portal ({len(postulaciones)})", expanded=False):
            if not postulaciones:
                st.info("Nadie se ha postulado a esta vacante todavía.")
            for solicitud in postulaciones:
                sid = solicitud.get("id")
                st.markdown(f"**{_txt(solicitud.get('nombre'), 90)}** · "
                            f"{_txt(solicitud.get('estado'), 45)}")
                st.caption(f"{solicitud.get('correo') or ''} · Expediente #{solicitud.get('candidato_id')}")
                if solicitud.get("estado") == "Retirada":
                    st.caption("Postulación retirada por el candidato. No se pueden cambiar sus estados.")
                    continue
                a, b = st.columns([2, 1], gap="small")
                opciones_estado = ["En revisión", "Preseleccionado", "Entrevista", "Finalista", "Aceptado", "Rechazado", "Descartado"]
                actual_estado = solicitud.get("estado") or "En revisión"
                with a:
                    nuevo = st.selectbox("Estado", opciones_estado,
                        index=opciones_estado.index(actual_estado) if actual_estado in opciones_estado else 0,
                        key=f"sol_estado_{sid}")
                with b:
                    if st.button("Guardar etapa", key=f"sol_guardar_{sid}", use_container_width=True):
                        respuesta = api_put(f"/api/v1/postulaciones-admin/{sid}/estado", {"estado": nuevo})
                        if respuesta is not None and respuesta.ok:
                            _flash("Estado de postulación actualizado.")
                        else:
                            st.error(_error(respuesta))
                st.divider()
    else:
        st.error("No se pudieron consultar las postulaciones del portal.")

    # El ranking y las tarjetas van a ancho completo, debajo de las acciones.
    panel_candidatos(actual, candidatos, entrevistas)

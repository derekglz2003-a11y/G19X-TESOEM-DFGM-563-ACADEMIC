from datetime import date, time, datetime
import re
from urllib.parse import quote
import math
import streamlit as st

from servicios.api import api_post, api_put, api_delete
from servicios.whatsapp import enviar_invitacion_entrevista
from servicios.ui_helpers import seguro, telefono_mx

ESTADOS = ["Programada", "Confirmada", "Realizada", "Cancelada", "No asistió", "Finalista", "Aceptado", "Rechazado"]


def _err(r):
    if r is None:
        return "Backend sin conexión."
    try:
        return str(r.json().get("detail") or r.text)[:320]
    except Exception:
        return str(getattr(r, "text", "Error"))[:320]


def _flash(msg):
    st.session_state["flash_entrevistas"] = msg
    st.rerun()


def _fecha(v):
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return date.today()


def _hora(v):
    try:
        txt = str(v or "10:00")[:5]
        h, m = txt.split(":")
        return time(int(h), int(m))
    except Exception:
        return time(10, 0)


def _paginate(items, key, per_page=6):
    total = max(1, math.ceil(len(items) / per_page))
    page = min(max(1, st.session_state.get(key, 1)), total)
    st.session_state[key] = page
    return items[(page - 1) * per_page: page * per_page], page, total


def render(ctx):
    candidatos = ctx.get("candidatos") or []
    entrevistas = ctx.get("entrevistas") or []
    vacantes = ctx.get("vacantes") or []
    mensajes = ctx.get("mensajes_whatsapp") or []

    st.markdown('<div class="cai-intro"><div><div class="cai-kicker">CONTROL Y SEGUIMIENTO</div><h1>Entrevistas</h1><p class="cai-descripcion">Programa, confirma o cancela citas desde una vista más compacta y práctica.</p></div></div>', unsafe_allow_html=True)
    flash = st.session_state.pop("flash_entrevistas", None)
    if flash:
        st.success(flash)

    with st.expander("+ Agendar nueva entrevista", expanded=False):
        if not candidatos:
            st.info("Primero agrega candidatos.")
        else:
            with st.form("nueva_entrevista"):
                opciones = {f"{c.get('nombre') or 'Sin nombre'} · #{c.get('id')}": c for c in candidatos}
                candidato_sel = st.selectbox("Candidato", list(opciones))
                cand = opciones[candidato_sel]
                vac_op = {f"{v.get('titulo')} · #{v.get('id')}": v for v in vacantes}
                vac_sel = st.selectbox("Vacante", ["Sin vincular"] + list(vac_op))
                vac = vac_op.get(vac_sel)
                c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1.2], gap="small")
                with c1:
                    puesto = st.text_input("Puesto", value=(vac or {}).get("titulo") or cand.get("perfil_destacado") or "")
                with c2:
                    fecha = st.date_input("Fecha", value=date.today())
                with c3:
                    hora = st.time_input("Hora", value=time(10, 0))
                with c4:
                    lugar = st.text_input("Lugar / enlace", value="Google Meet")
                enviar_al_agendar = st.checkbox("Enviar invitación por WhatsApp al agendar (requiere UltraMsg y autorización del candidato)", value=False)
                guardar = st.form_submit_button("Agendar entrevista", type="primary")
            if guardar:
                data = {
                    "candidato_id": cand.get("id"),
                    "nombre": cand.get("nombre") or "Candidato",
                    "puesto": puesto,
                    "fecha": fecha.isoformat(),
                    "hora": hora.strftime("%H:%M"),
                    "lugar": lugar,
                }
                if vac:
                    data["vacante_id"] = vac.get("id")
                r = api_post("/api/v1/entrevistas", data=data)
                if r is not None and r.ok:
                    mensaje = "Entrevista agendada correctamente."
                    if enviar_al_agendar:
                        enviada, detalle_envio, registrado = enviar_invitacion_entrevista(
                            r.json().get("id"), cand, puesto, fecha.isoformat(), hora.strftime("%H:%M"), lugar
                        )
                        mensaje += (" Invitación enviada a UltraMsg." if enviada else f" Invitación no enviada: {detalle_envio}")
                        if not registrado:
                            mensaje += " No se pudo guardar la bitácora de WhatsApp."
                    _flash(mensaje)
                else:
                    st.error(_err(r))

    st.markdown(_ESTILOS_TARJETAS, unsafe_allow_html=True)
    st.markdown('<div class="cai-section">Agenda y estados</div>', unsafe_allow_html=True)
    if not entrevistas:
        st.info("No hay entrevistas registradas.")
        return

    b1, b2 = st.columns([1.45, 1], gap="small")
    with b1:
        buscar = st.text_input("Buscar entrevista", placeholder="Candidato, puesto o estado...")
    with b2:
        directo = st.selectbox("Ir directo", ["Todas"] + [f"{e.get('nombre')} · #{e.get('id')}" for e in entrevistas])

    lista = entrevistas[:]
    if buscar.strip():
        q = buscar.casefold().strip()
        lista = [e for e in lista if q in " ".join(str(e.get(k) or "") for k in ("nombre", "puesto", "estado", "lugar")).casefold()]
    if directo != "Todas":
        eid = directo.split("#")[-1].strip()
        lista = [e for e in lista if str(e.get("id")) == eid]
    lista.sort(key=lambda e: (str(e.get("fecha") or ""), str(e.get("hora") or "")), reverse=True)

    items, pagina, total = _paginate(lista, "page_entrevistas", per_page=5)
    st.caption(f"{len(lista)} entrevista(s) · página {pagina} de {total}")
    n1, n2 = st.columns(2)
    with n1:
        if st.button("← Anterior", key="ent_prev", disabled=pagina <= 1):
            st.session_state["page_entrevistas"] = pagina - 1
            st.rerun()
    with n2:
        if st.button("Siguiente →", key="ent_next", disabled=pagina >= total):
            st.session_state["page_entrevistas"] = pagina + 1
            st.rerun()

    msg_por_entrevista = {}
    for m in mensajes:
        eid = m.get("entrevista_id")
        if eid is None:
            continue  # No atribuir mensajes viejos a entrevistas distintas.
        clave = str(eid)
        creado = str(m.get("creado_en") or "")
        if clave not in msg_por_entrevista or creado > str(msg_por_entrevista[clave].get("creado_en") or ""):
            msg_por_entrevista[clave] = m

    # Dos tarjetas por fila, igual que Radar y Candidatos.
    columnas = st.columns(2, gap="medium")
    for indice, entrevista in enumerate(items):
        with columnas[indice % 2]:
            _tarjeta_entrevista(entrevista, candidatos, msg_por_entrevista)


# La hoja de estilos afecta exclusivamente a las tarjetas de esta pagina.
_ESTILOS_TARJETAS = """
<style>
.cai-ent-cabecera {
    background: #193b64;
    color: #fff;
    border-radius: 11px 11px 0 0;
    margin: -1rem -1rem 0.95rem;
    padding: 15px 18px;
    min-height: 85px;
}
.cai-ent-etiqueta {font-size: .68rem; letter-spacing: .11em; font-weight: 800; color: #d6eaff;}
.cai-ent-nombre {font-weight: 800; font-size: 1.15rem; margin-top: 4px; line-height: 1.3;}
.cai-ent-fila {display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin-bottom:9px;}
.cai-ent-rol {background:#eaf2f9; color:#16385c; border-radius:999px; padding:5px 11px; font-size:.78rem; font-weight:700;}
.cai-ent-estado {border-radius:999px; padding:5px 11px; font-size:.78rem; font-weight:800;}
.cai-ent-dato {font-size:.87rem; color:#284866; line-height:1.6;}
.cai-ent-suave {font-size:.78rem; color:#6b8195; margin:8px 0 10px; line-height:1.5;}
.cai-ent-acciones {font-size:.70rem; color:#6b8195; font-weight:700; letter-spacing:.04em; margin:7px 0 3px;}
</style>
"""


def _tarjeta_entrevista(e: dict, candidatos: list, msg_por_entrevista: dict):
    """Tarjeta compacta; conserva todas las operaciones originales de la API."""
    eid = e.get("id")
    estado = str(e.get("estado") or "Programada")
    ultimo = msg_por_entrevista.get(str(eid))
    chip = f"WhatsApp: {ultimo.get('estado')}" if ultimo else "WhatsApp: sin envío verificado para esta cita"

    # Los colores son solamente informativos, no afectan a los estados del backend.
    colores = {
        "Programada": ("#e8f1ff", "#164ea6"),
        "Confirmada": ("#e0f4ea", "#166b44"),
        "Realizada": ("#e7f3ec", "#176b44"),
        "Finalista": ("#f1e9ff", "#6436a7"),
        "Cancelada": ("#fde8e8", "#9d3030"),
        "No asistió": ("#fff0df", "#986018"),
        "Aceptado": ("#e0f4ea", "#166b44"),
        "Rechazado": ("#fde8e8", "#9d3030"),
    }
    fondo_estado, texto_estado = colores.get(estado, ("#eaf2f9", "#16385c"))

    with st.container(border=True):
        st.markdown(
            f'<div class="cai-ent-cabecera">'
            f'<div class="cai-ent-etiqueta">ENTREVISTA #{seguro(eid, 15)}</div>'
            f'<div class="cai-ent-nombre">{seguro(e.get("nombre") or "Candidato", 90)}</div>'
            f'</div>'
            f'<div class="cai-ent-fila">'
            f'<span class="cai-ent-rol">{seguro(e.get("puesto") or "Sin puesto", 75)}</span>'
            f'<span class="cai-ent-estado" style="background:{fondo_estado};color:{texto_estado}">'
            f'{seguro(estado, 30)}</span></div>'
            f'<div class="cai-ent-dato"><strong>Fecha:</strong> {seguro(e.get("fecha") or "Por definir", 20)}'
            f' &nbsp;·&nbsp; <strong>Hora:</strong> {seguro(e.get("hora") or "Por definir", 12)}</div>'
            f'<div class="cai-ent-dato"><strong>Lugar / enlace:</strong> {seguro(e.get("lugar") or "Por definir", 90)}</div>'
            f'<div class="cai-ent-suave">{seguro(chip, 130)}</div>'
            f'<div class="cai-ent-acciones">GESTIONAR ENTREVISTA</div>',
            unsafe_allow_html=True,
        )

        # Cinco acciones en 2 filas para que se vean bien en una tarjeta de media pantalla.
        a1, a2, a3 = st.columns(3, gap="small")
        with a1:
            if st.button("Confirmar", key=f"ent_conf_{eid}", use_container_width=True):
                r = api_put(f"/api/v1/entrevistas/{eid}/decision", {"estado": "Confirmada", "tipo_finalista": ""})
                if r is not None and r.ok:
                    _flash("Entrevista confirmada.")
                else:
                    st.error(_err(r))
        with a2:
            if st.button("Realizada", key=f"ent_real_{eid}", use_container_width=True):
                r = api_put(f"/api/v1/entrevistas/{eid}/decision", {"estado": "Realizada", "tipo_finalista": ""})
                if r is not None and r.ok:
                    _flash("Entrevista actualizada a realizada.")
                else:
                    st.error(_err(r))
        with a3:
            if st.button("Finalista", key=f"ent_final_{eid}", use_container_width=True):
                r = api_put(f"/api/v1/entrevistas/{eid}/decision", {"estado": "Finalista", "tipo_finalista": "En evaluación"})
                if r is not None and r.ok:
                    _flash("Perfil enviado a finalistas.")
                else:
                    st.error(_err(r))

        b1, b2 = st.columns(2, gap="small")
        with b1:
            if st.button("Cancelar", key=f"ent_cancel_{eid}", use_container_width=True):
                r = api_put(f"/api/v1/entrevistas/{eid}/decision", {"estado": "Cancelada", "tipo_finalista": ""})
                if r is not None and r.ok:
                    _flash("Entrevista cancelada.")
                else:
                    st.error(_err(r))
        with b2:
            if st.button("Eliminar", key=f"ent_del_{eid}", use_container_width=True):
                st.session_state[f"preguntar_borrar_entrevista_{eid}"] = True

        if st.session_state.get(f"preguntar_borrar_entrevista_{eid}"):
            st.warning("Se eliminará esta entrevista, pero se conservará al candidato.")
            d1, d2 = st.columns(2, gap="small")
            with d1:
                if st.button("Sí, eliminar", key=f"ent_si_del_{eid}", type="primary", use_container_width=True):
                    r = api_delete(f"/api/v1/entrevistas/{eid}")
                    if r is not None and r.ok:
                        st.session_state.pop(f"preguntar_borrar_entrevista_{eid}", None)
                        _flash("Entrevista eliminada.")
                    else:
                        st.error(_err(r))
            with d2:
                if st.button("Conservar", key=f"ent_no_del_{eid}", use_container_width=True):
                    st.session_state.pop(f"preguntar_borrar_entrevista_{eid}", None)
                    st.rerun()

        with st.expander("Editar y notificar"):
            t1, t2 = st.tabs(["Editar cita", "WhatsApp"])
            with t1:
                with st.form(f"ent_edit_{eid}"):
                    puesto = st.text_input("Puesto", value=str(e.get("puesto") or ""), key=f"ent_puesto_{eid}")
                    fecha = st.date_input("Fecha", value=_fecha(e.get("fecha")), key=f"ent_fecha_{eid}")
                    hora = st.time_input("Hora", value=_hora(e.get("hora")), key=f"ent_hora_{eid}")
                    lugar = st.text_input("Lugar / enlace", value=str(e.get("lugar") or "Google Meet"), key=f"ent_lugar_{eid}")
                    guardar = st.form_submit_button("Guardar cambios", type="primary", use_container_width=True)
                if guardar:
                    r = api_put(
                        f"/api/v1/entrevistas/{eid}",
                        {"puesto": puesto, "fecha": fecha.isoformat(), "hora": hora.strftime("%H:%M"), "lugar": lugar},
                    )
                    if r is not None and r.ok:
                        _flash("Cita actualizada.")
                    else:
                        st.error(_err(r))

            with t2:
                c = next((c for c in candidatos if str(c.get("id")) == str(e.get("candidato_id"))), None)
                telefono = telefono_mx((c or {}).get("telefono"))
                if not telefono:
                    st.info("El candidato no tiene un teléfono mexicano válido.")
                else:
                    mensaje = (
                        f"Hola {e.get('nombre') or 'candidato'}, tu entrevista para {e.get('puesto') or 'el puesto'} "
                        f"está programada el {e.get('fecha')} a las {e.get('hora')}, en {e.get('lugar')}. "
                        "Por favor confirma tu asistencia. CurriculAi."
                    )
                    st.link_button(
                        "Abrir conversación en WhatsApp",
                        f"https://wa.me/{telefono}?text={quote(mensaje)}",
                        use_container_width=True,
                    )
                    st.caption("Abrir WhatsApp no confirma que el mensaje se haya enviado.")
                    if st.button("Enviar con UltraMsg", key=f"ent_wa_{eid}", type="primary", use_container_width=True):
                        enviado, detalle, registrado = enviar_invitacion_entrevista(
                            eid, c, e.get("puesto") or "el puesto", e.get("fecha") or "",
                            e.get("hora") or "", e.get("lugar") or "",
                        )
                        if enviado:
                            st.success("Invitación aceptada por UltraMsg. Verifica su entrega.")
                        else:
                            st.error(f"No se pudo enviar: {detalle}")
                        if not registrado:
                            st.warning("No se pudo guardar la bitácora del envío.")
                if ultimo:
                    st.caption(f"Último registro: {ultimo.get('estado')} · {ultimo.get('creado_en') or ''}")
                else:
                    st.caption("Aún no hay envío registrado para esta entrevista.")

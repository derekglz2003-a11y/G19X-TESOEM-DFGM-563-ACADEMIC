import math
import streamlit as st
from servicios.api import api_put, api_delete
from servicios.ui_helpers import seguro, es_finalista


def _err(r):
    if r is None:
        return "Backend sin conexión"
    try:
        return str(r.json().get("detail") or r.text)[:250]
    except Exception:
        return str(getattr(r, "text", "Error"))[:250]


def _flash(msg):
    st.session_state["flash_finalistas"] = msg
    st.rerun()


def _paginate(items, key, per_page=4):
    total = max(1, math.ceil(len(items) / per_page))
    page = min(max(1, st.session_state.get(key, 1)), total)
    st.session_state[key] = page
    return items[(page - 1) * per_page: page * per_page], page, total


def render(ctx):
    entrevistas = ctx.get("entrevistas") or []
    st.markdown('<div class="cai-intro"><div><div class="cai-kicker">SELECCIÓN FINAL</div><h1>Finalistas</h1><p class="cai-descripcion">Toma decisiones rápidas desde el mismo recuadro: aceptar, rechazar, retirar o eliminar.</p></div></div>', unsafe_allow_html=True)
    if st.session_state.pop("flash_finalistas", None):
        st.success("Decisión registrada correctamente.")

    lista = [e for e in entrevistas if es_finalista(e)]
    if not lista:
        st.info("Todavía no hay finalistas.")
        return

    buscar = st.text_input("Buscar finalista", placeholder="Nombre o puesto...")
    if buscar.strip():
        q = buscar.casefold().strip()
        lista = [e for e in lista if q in " ".join(str(e.get(k) or "") for k in ("nombre", "puesto", "estado")).casefold()]

    items, pagina, total = _paginate(lista, "page_finalistas", per_page=4)
    st.caption(f"{len(lista)} registro(s) en etapa final · página {pagina} de {total}")
    n1, n2 = st.columns(2)
    with n1:
        if st.button("← Anterior", key="fin_prev", disabled=pagina <= 1):
            st.session_state["page_finalistas"] = pagina - 1
            st.rerun()
    with n2:
        if st.button("Siguiente →", key="fin_next", disabled=pagina >= total):
            st.session_state["page_finalistas"] = pagina + 1
            st.rerun()

    for i in range(0, len(items), 2):
        cols = st.columns(2, gap="large")
        for col, e in zip(cols, items[i:i + 2]):
            eid = e.get("id")
            est = str(e.get("estado") or "Finalista")
            with col:
                st.markdown(
                    f'<div class="cai-item-card"><div class="cai-item-banner"><div><div class="cai-pretitle">Etapa final</div><div class="cai-title">{seguro(e.get("nombre") or "Candidato", 90)}</div></div><span class="cai-icon">★</span></div><div class="cai-item-body"><span class="cai-tag gold">{seguro(est, 30)}</span><div class="cai-item-meta">{seguro(e.get("puesto") or "Sin puesto", 100)}</div><div class="cai-item-copy">Entrevista: {seguro(e.get("fecha") or "Sin fecha", 15)} · {seguro(e.get("hora"), 12)}</div></div></div>',
                    unsafe_allow_html=True,
                )
                a1, a2, a3, a4 = st.columns(4, gap="small")
                with a1:
                    if st.button("Aceptar", key=f"acept_{eid}", use_container_width=True):
                        r = api_put(f"/api/v1/entrevistas/{eid}/decision", {"estado": "Aceptado", "tipo_finalista": "En evaluación"})
                        if r is not None and r.ok: _flash("Finalista aceptado.")
                        else: st.error(_err(r))
                with a2:
                    if st.button("Rechazar", key=f"rech_{eid}", use_container_width=True):
                        r = api_put(f"/api/v1/entrevistas/{eid}/decision", {"estado": "Rechazado", "tipo_finalista": ""})
                        if r is not None and r.ok: _flash("Finalista rechazado.")
                        else: st.error(_err(r))
                with a3:
                    if st.button("Retirar", key=f"ret_{eid}", use_container_width=True):
                        r = api_put(f"/api/v1/entrevistas/{eid}/decision", {"estado": "En evaluación", "tipo_finalista": ""})
                        if r is not None and r.ok: _flash("Perfil retirado de finalistas.")
                        else: st.error(_err(r))
                with a4:
                    if st.button("Eliminar", key=f"del_{eid}", use_container_width=True):
                        st.session_state[f"confirm_fin_{eid}"] = True
                if st.session_state.get(f"confirm_fin_{eid}"):
                    st.warning("Se eliminará la entrevista asociada; el candidato permanecerá. Esta acción no se puede deshacer.")
                    p1, p2 = st.columns(2)
                    with p1:
                        if st.button("Sí, eliminar entrevista", key=f"yes_fin_{eid}", type="primary", use_container_width=True):
                            r = api_delete(f"/api/v1/entrevistas/{eid}")
                            if r is not None and r.ok: _flash("Registro de entrevista eliminado.")
                            else: st.error(_err(r))
                    with p2:
                        if st.button("Conservar registro", key=f"no_fin_{eid}", use_container_width=True):
                            st.session_state.pop(f"confirm_fin_{eid}", None)
                            st.rerun()

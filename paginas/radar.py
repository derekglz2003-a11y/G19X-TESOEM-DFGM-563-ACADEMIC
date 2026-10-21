import math
import streamlit as st
from servicios.api import api_get, api_post
from servicios.ui_helpers import seguro


def _err(r):
    if r is None:
        return "API sin conexión."
    try:
        return str(r.json().get("detail") or r.text)[:300]
    except Exception:
        return str(getattr(r, "text", "Error"))[:300]


def _paginate(items, key, per_page=5):
    total = max(1, math.ceil(len(items) / per_page))
    page = min(max(1, st.session_state.get(key, 1)), total)
    st.session_state[key] = page
    return items[(page - 1) * per_page: page * per_page], page, total


def render(ctx):
    vacantes = ctx.get("vacantes") or []
    st.markdown('<div class="cai-intro"><div><div class="cai-kicker">MOTOR DE FILTRADO CURRICULAR</div><h1>Radar de talentos</h1><p class="cai-descripcion">Consulta el ranking semántico por vacante y revisa por qué un perfil es compatible.</p></div></div>', unsafe_allow_html=True)
    if not vacantes:
        st.info("Primero registra una vacante.")
        return

    opciones = {f"{v.get('titulo') or 'Vacante'} · #{v.get('id')}": v for v in vacantes}
    seleccion = st.selectbox("Vacante a evaluar", list(opciones))
    vac = opciones[seleccion]
    vid = vac.get("id")

    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("Evaluar todos los CV con IA", type="primary", use_container_width=True):
            with st.spinner("Ejecutando motor semántico..."):
                r = api_post(f"/api/v1/evaluar/{vid}")
            if r is not None and r.ok:
                data = r.json()
                st.success(f"Evaluación terminada: {data.get('evaluados', 0)} CV procesados.")
                if data.get("omitidos_sin_texto"):
                    st.warning(f"{data['omitidos_sin_texto']} CV no pudieron evaluarse por falta de texto utilizable.")
            else:
                st.error(_err(r))
    with c2:
        if st.button("Abrir vacante y gestionarla", use_container_width=True):
            st.session_state["vacante_activa"] = vid
            navegar = ctx.get("navegar")
            if callable(navegar):
                navegar("Vacantes")

    ranking = api_get(f"/api/v1/ranking/{vid}", [])
    ranking = ranking if isinstance(ranking, list) else []
    if not ranking:
        st.info("Aún no hay resultados. Ejecuta primero la evaluación con IA.")
        return

    st.markdown('<div class="cai-section">Resultados del ranking</div>', unsafe_allow_html=True)
    buscar = st.text_input("Buscar dentro del ranking", placeholder="Nombre, habilidades o correo...")
    if buscar.strip():
        q = buscar.casefold().strip()
        ranking = [r for r in ranking if q in " ".join(str(r.get(k) or "") for k in ("candidato_nombre", "skills", "email")).casefold()]

    items, pagina, total = _paginate(ranking, f"page_ranking_{vid}", per_page=5)
    st.caption(f"{len(ranking)} perfil(es) · página {pagina} de {total}")
    n1, n2 = st.columns(2)
    with n1:
        if st.button("← Anterior", key=f"rank_prev_{vid}", disabled=pagina <= 1):
            st.session_state[f"page_ranking_{vid}"] = pagina - 1
            st.rerun()
    with n2:
        if st.button("Siguiente →", key=f"rank_next_{vid}", disabled=pagina >= total):
            st.session_state[f"page_ranking_{vid}"] = pagina + 1
            st.rerun()

    for idx, item in enumerate(items, start=(pagina - 1) * 5 + 1):
        score = max(0.0, min(100.0, float(item.get("score_similitud") or 0)))
        st.markdown(
            f'<div class="cai-outline-box"><strong>{idx}. {seguro(item.get("candidato_nombre") or "Candidato", 100)}</strong><br>'
            f'<span class="cai-subtle">{seguro(item.get("skills") or "Sin habilidades", 220)}</span><br>'
            f'<div style="display:flex;justify-content:space-between;gap:18px;align-items:center;margin-top:10px;flex-wrap:wrap;">'
            f'<div style="flex:1 1 420px"><span class="cai-tag gold">Compatibilidad {score:.1f}%</span></div>'
            f'<div style="font-size:2.2rem;font-weight:800;color:#173a62;">{score:.1f}%</div></div></div>',
            unsafe_allow_html=True,
        )
        st.progress(score / 100)
        with st.expander("Explicación del resultado"):
            st.write(item.get("resumen") or "Sin resumen disponible.")
            st.caption(item.get("justificacion") or "Sin explicación adicional.")
            st.write("**Correo:**", item.get("email") or "N/A")
            st.write("**Teléfono:**", item.get("telefono") or "N/A")

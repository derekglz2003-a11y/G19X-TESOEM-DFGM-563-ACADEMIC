"""Radar de talentos: tarjetas compactas en el estilo de Expedientes.

Mantiene las rutas protegidas y el contrato render(ctx) de CurriculAi.
"""
from __future__ import annotations

import math
from html import escape

import streamlit as st

from servicios.api import api_get, api_post


def _seguro(valor, limite=180):
    return escape(str(valor or "")[:limite], quote=True)


def _error_respuesta(respuesta):
    if respuesta is None:
        return "No fue posible conectar con FastAPI."
    try:
        detalle = respuesta.json().get("detail")
        return str(detalle or respuesta.text)[:350]
    except (ValueError, AttributeError):
        return str(getattr(respuesta, "text", "Error desconocido"))[:350]


def _porcentaje(registro):
    """La API actual entrega score_similitud en escala porcentual 0–100."""
    valor = registro.get("score_similitud")
    if valor is None:
        return None
    try:
        numero = float(valor)
        if not math.isfinite(numero):
            return None
        return max(0.0, min(100.0, numero))
    except (TypeError, ValueError):
        return None


def _texto_candidato(registro, candidatos):
    """Complementa solo campos presentes en los datos que el backend ya autorizó."""
    cid = registro.get("candidato_id")
    candidato = next(
        (c for c in candidatos if str(c.get("id")) == str(cid)),
        {},
    )
    return {
        "id": cid,
        "nombre": registro.get("candidato_nombre") or candidato.get("nombre") or "Candidato",
        "perfil": registro.get("perfil_destacado") or candidato.get("perfil_destacado") or "Perfil laboral",
        "skills": registro.get("skills") or candidato.get("skills") or "Sin habilidades registradas",
        "email": registro.get("email") or candidato.get("email") or "Sin correo",
        "telefono": registro.get("telefono") or candidato.get("telefono") or "Sin teléfono",
    }


def _tarjeta(registro, numero, candidatos, vacante_id):
    datos = _texto_candidato(registro, candidatos)
    puntaje = _porcentaje(registro)
    texto_puntaje = "Por evaluar" if puntaje is None else f"Compatibilidad {puntaje:.1f}%"
    porcentaje_largo = "—" if puntaje is None else f"{puntaje:.1f}%"

    st.markdown(
        '<div class="cai-item-card">'
        '<div class="cai-item-banner">'
        '<div>'
        f'<div class="cai-pretitle">RESULTADO #{numero}</div>'
        f'<div class="cai-title">{_seguro(datos["nombre"], 90)}</div>'
        '</div>'
        '<span class="cai-icon">◎</span>'
        '</div>'
        '<div class="cai-item-body">'
        f'<span class="cai-tag">{_seguro(datos["perfil"], 65)}</span>'
        f'<div class="cai-item-meta">{_seguro(datos["email"], 75)} · {_seguro(datos["telefono"], 35)}</div>'
        f'<div class="cai-item-copy">{_seguro(datos["skills"], 220)}</div>'
        '<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-top:12px">'
        f'<span class="cai-tag gold">{_seguro(texto_puntaje)}</span>'
        f'<strong style="font-size:1.4rem;color:#173a62">{_seguro(porcentaje_largo)}</strong>'
        '</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    with st.expander("Explicación del resultado"):
        st.write(registro.get("resumen") or "No hay fragmento disponible.")
        st.caption(registro.get("justificacion") or "Sin explicación adicional.")
        if puntaje is not None:
            st.progress(puntaje / 100)
            st.caption("Similitud semántica orientativa: no representa una probabilidad de contratación.")
        else:
            st.caption("Este candidato todavía no tiene un porcentaje registrado.")


def render(ctx):
    """Punto de entrada requerido por app.py: PANTALLAS['Radar de talentos']."""
    vacantes = ctx.get("vacantes") or []
    candidatos = ctx.get("candidatos") or []
    st.markdown(
        '<div class="cai-intro"><div>'
        '<div class="cai-kicker">MOTOR DE FILTRADO CURRICULAR</div>'
        '<h1>Radar de talentos</h1>'
        '<p class="cai-descripcion">Consulta perfiles por vacante, ordenados por similitud semántica.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    if not vacantes:
        st.info("Primero registra una vacante para utilizar el Radar.")
        return

    opciones = {
        f"{v.get('titulo') or 'Vacante'} · #{v.get('id')}": v
        for v in vacantes
    }
    opcion = st.selectbox("Vacante para evaluar", list(opciones), key="radar_vacante_elegida")
    vacante_id = opciones[opcion].get("id")

    a, b = st.columns(2, gap="small")
    with a:
        if st.button("Evaluar todos los CV con IA", type="primary", use_container_width=True):
            with st.spinner("Evaluando perfiles..."):
                respuesta = api_post(f"/api/v1/evaluar/{vacante_id}")
            if respuesta is not None and respuesta.ok:
                try:
                    datos = respuesta.json()
                except ValueError:
                    datos = {}
                st.success(f"Evaluación terminada: {datos.get('evaluados', 0)} CV procesados.")
                omitidos = datos.get("omitidos_sin_perfil", datos.get("omitidos_sin_texto", 0))
                if omitidos:
                    st.warning(f"{omitidos} expedientes no cuentan con texto suficiente para evaluarse.")
            else:
                st.error(_error_respuesta(respuesta))
    with b:
        if st.button("Abrir vacante y gestionarla", use_container_width=True):
            st.session_state["vacante_activa"] = vacante_id
            navegar = ctx.get("navegar")
            if callable(navegar):
                navegar("Vacantes")

    registros = api_get(f"/api/v1/ranking/{vacante_id}", [])
    if not isinstance(registros, list):
        st.error("No se pudo obtener el ranking. Comprueba la conexión con FastAPI.")
        return
    if not registros:
        st.info("Aún no hay resultados para esta vacante. Ejecuta primero la evaluación con IA.")
        return

    registros = sorted(
        registros,
        key=lambda x: _porcentaje(x) if isinstance(x, dict) and _porcentaje(x) is not None else -1,
        reverse=True,
    )
    st.markdown('<div class="cai-section">Resultados del ranking</div>', unsafe_allow_html=True)
    busqueda = st.text_input(
        "Buscar dentro del ranking", placeholder="Nombre, habilidades o correo...", key="radar_busqueda"
    )
    if busqueda.strip():
        consulta = busqueda.strip().casefold()
        registros = [
            r for r in registros
            if consulta in " ".join(str(r.get(k) or "") for k in (
                "candidato_nombre", "skills", "email", "perfil_destacado"
            )).casefold()
        ]

    por_pagina = 4
    paginas = max(1, math.ceil(len(registros) / por_pagina))
    clave_pagina = f"radar_pagina_{vacante_id}"
    pagina = max(1, min(int(st.session_state.get(clave_pagina, 1)), paginas))
    st.session_state[clave_pagina] = pagina
    st.caption(f"{len(registros)} perfil(es) · página {pagina} de {paginas}")
    p1, p2 = st.columns(2)
    with p1:
        if st.button("← Anterior", key=f"radar_anterior_{vacante_id}", disabled=pagina == 1):
            st.session_state[clave_pagina] = pagina - 1
            st.rerun()
    with p2:
        if st.button("Siguiente →", key=f"radar_siguiente_{vacante_id}", disabled=pagina >= paginas):
            st.session_state[clave_pagina] = pagina + 1
            st.rerun()

    visibles = registros[(pagina - 1) * por_pagina: pagina * por_pagina]
    for fila in range(0, len(visibles), 2):
        columnas = st.columns(2, gap="large")
        for desplazamiento, registro in enumerate(visibles[fila: fila + 2]):
            numero = (pagina - 1) * por_pagina + fila + desplazamiento + 1
            with columnas[desplazamiento]:
                _tarjeta(registro, numero, candidatos, vacante_id)

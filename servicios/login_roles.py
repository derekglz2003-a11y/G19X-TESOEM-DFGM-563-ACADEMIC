"""Login visual de dos roles para CurriculAi (Streamlit).

Admin: usa la misma contraseña PBKDF2 que ya estaba configurada.
Candidato: usa cuentas independientes validadas por FastAPI /portal.
"""
from __future__ import annotations

import base64
import hmac
import html
import os
import re
from pathlib import Path

import requests
import streamlit as st
from servicios.api import API_URL
from servicios.seguridad import acceso_configurado, verificar_contrasena


RAIZ = Path(__file__).resolve().parents[1]


def _imagen_embebida(archivo: Path):
    ext = archivo.suffix.lower()
    mime = 'image/png' if ext == '.png' else 'image/webp' if ext == '.webp' else 'image/jpeg'
    return f'data:{mime};base64,{base64.b64encode(archivo.read_bytes()).decode("ascii")}'


def _logo_html(raiz: Path):
    for nombre in ('logo.png','logo.jpg','logo.jpeg','logo.webp','curriculai_logo.png','logo_curriculai.png'):
        archivo = raiz / nombre
        if archivo.is_file():
            return f'<img class="cai-role-logo" src="{_imagen_embebida(archivo)}" alt="Logo de CurriculAi">'
    return '<div class="cai-role-logo-alt">CA</div>'


def _estilos(raiz: Path):
    imagen = next((p for p in (raiz/'fondo_login_curriculai.jpeg', raiz/'fondo.jpeg') if p.is_file()), None)
    fondo = f'url("{_imagen_embebida(imagen)}")' if imagen else 'linear-gradient(135deg,#ecf6ff,#e7effa)'
    st.markdown('''<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(110deg, rgba(235,245,254,.72),rgba(243,247,254,.63)),__FONDO__ center/cover fixed !important;
    }
    [data-testid="stHeader"] {background:transparent!important;}
    [data-testid="stMainBlockContainer"] {max-width:1250px!important;padding-top:clamp(20px,4vh,55px)!important;}
    [data-testid="stSidebar"] {display:none!important;}
    /* Izquierda sin tarjeta: el fondo de CurriculAi queda visible. */
    .cai-role-welcome{
        position:relative;min-height:580px;padding:36px 12px 30px 8px;
        box-sizing:border-box;color:#173a60;background:transparent!important;
        border:0!important;border-radius:0!important;box-shadow:none!important;
        display:flex;flex-direction:column;justify-content:space-between;gap:28px;
    }
    .cai-role-welcome:before{display:none!important;content:none!important;}
    .cai-role-welcome>*{position:relative;z-index:1;}
    .cai-role-brand{display:flex;align-items:center;gap:16px;}
    .cai-role-logo{width:88px;height:88px;object-fit:contain;border-radius:18px;
        background:#fff;padding:8px;box-sizing:border-box;
        box-shadow:0 8px 25px rgba(27,65,95,.09);}
    .cai-role-logo-alt{width:88px;height:88px;display:grid;place-items:center;
        background:white;color:#193a62;border-radius:18px;font-weight:900;}
    .cai-role-brand-title{font-size:29px;font-weight:850;letter-spacing:-.9px;
        line-height:1.2;color:#163957!important;}
    .cai-role-brand-sub{font-size:11px;font-weight:800;color:#39769e!important;
        letter-spacing:1.8px;margin-top:6px;}
    .cai-role-copy{max-width:550px;}
    .cai-role-kicker{font-size:12px;color:#0874ac!important;
        letter-spacing:2px;font-weight:850;margin-bottom:14px;text-transform:uppercase;}
    .cai-role-welcome .cai-role-title{font-size:clamp(38px,3.6vw,56px);
        font-weight:850;line-height:1.12;letter-spacing:-1.7px;margin:0 0 17px;
        color:#123755!important;}
    .cai-role-title span{color:#008be3!important;}
    .cai-role-question{font-size:clamp(19px,1.6vw,24px);font-weight:750;
        line-height:1.4;color:#173b5e!important;margin:0 0 14px;max-width:540px;}
    .cai-role-text{font-size:15.5px;color:#47647c!important;
        line-height:1.7;max-width:515px;margin:0;}
    .cai-role-paths{display:grid;gap:18px;margin-top:30px;max-width:525px;}
    .cai-role-path{padding-left:16px;border-left:3px solid #008be3;}
    .cai-role-path strong{display:block;color:#173a60!important;
        font-size:14px;font-weight:800;margin-bottom:4px;}
    .cai-role-path span{display:block;color:#516b80!important;
        font-size:13px;line-height:1.6;}
    .cai-role-foot{font-size:12px;color:#55758e!important;
        font-weight:550;line-height:1.5;}
    .st-key-cai_roles_form {background:white;padding:clamp(21px,3vw,40px);border-radius:22px;
        border:1px solid #d9e6f0;box-shadow:0 18px 44px rgba(12,44,79,.10);}
    .st-key-cai_roles_form h2{color:#18395f;font-size:30px;letter-spacing:-.9px;}
    .st-key-cai_roles_form [data-testid="stForm"]{border:0!important;padding:0!important;}
    .st-key-cai_roles_form [data-testid="stTextInput"] input{
        border-radius:10px!important;min-height:46px!important;border:1px solid #d8e3ee!important;color:#163758!important;background:#fafdff!important;}
    .st-key-cai_roles_form [data-testid="stFormSubmitButton"] button{
        background:#193b64!important;color:white!important;border:0!important;min-height:46px!important;font-weight:750!important;}
    .st-key-cai_roles_form [data-testid="stFormSubmitButton"] button:hover{background:#285784!important;}
    .cai-role-note{font-size:12px;color:#7b8b9b;line-height:1.65;}
    @media(max-width:850px){
        .cai-role-welcome{min-height:0;padding:18px 5px 22px;gap:24px;}
        .cai-role-welcome .cai-role-title{font-size:36px;}
        .cai-role-logo,.cai-role-logo-alt{width:65px;height:65px;}
        .cai-role-brand-title{font-size:24px;}
        .cai-role-paths{margin-top:19px;gap:12px;}
        .cai-role-foot{display:none;}
    }
    @media(max-width:550px){
        [data-testid="stMainBlockContainer"]{padding-top:14px!important;}
        .cai-role-question{font-size:19px;}
        .cai-role-text{font-size:14px;}
        .cai-role-paths{margin-top:16px;}
    }
    </style>'''.replace('__FONDO__', fondo), unsafe_allow_html=True)


def _llamar(method, ruta, **kwargs):
    try:
        return requests.request(method, f'{API_URL}{ruta}', timeout=12, **kwargs)
    except requests.RequestException:
        return None


def _mensaje_error(r, defecto):
    """Traduce errores de validación de FastAPI sin mostrar datos sensibles."""
    if r is None:
        return 'FastAPI no responde. Verifica que el servidor esté activo.'
    try:
        detalle = r.json().get('detail', defecto)
        if isinstance(detalle, str):
            return detalle
        if isinstance(detalle, list):
            campos = {
                'usuario': 'usuario', 'nombre': 'nombre completo',
                'correo': 'correo electrónico', 'contrasena': 'contraseña',
            }
            errores = []
            for e in detalle:
                if not isinstance(e, dict):
                    continue
                loc = e.get('loc', [])
                campo = campos.get(str(loc[-1]) if loc else '', 'un campo')
                tipo = str(e.get('type', ''))
                if tipo == 'missing':
                    errores.append(f'Falta el campo {campo}.')
                elif tipo == 'string_too_short':
                    minimo = e.get('ctx', {}).get('min_length')
                    errores.append(f'El campo {campo} debe contener al menos {minimo} caracteres.' if minimo else f'El campo {campo} es demasiado corto.')
                elif tipo == 'string_too_long':
                    errores.append(f'El campo {campo} es demasiado largo.')
                else:
                    errores.append(f'Revisa el campo {campo}.')
            if errores:
                return ' '.join(errores)
    except (ValueError, AttributeError, TypeError):
        pass
    return defecto


def _errores_registro(usuario, nombre, correo, contrasena):
    """Mismas reglas de longitud y formato del endpoint /portal/registro."""
    errores = []
    usuario = usuario.strip().lower()
    nombre = nombre.strip()
    correo = correo.strip().lower()
    if not re.fullmatch(r'[a-z0-9._-]{3,40}', usuario):
        errores.append('Usuario: escribe entre 3 y 40 caracteres, sin espacios. Puedes usar letras, números, punto, guion y guion bajo.')
    if not 2 <= len(nombre) <= 100:
        errores.append('Nombre completo: escribe entre 2 y 100 caracteres.')
    if not 5 <= len(correo) <= 254 or correo.count('@') != 1 or '.' not in correo.partition('@')[2] or ' ' in correo:
        errores.append('Correo electrónico: escribe una dirección válida, por ejemplo, maria@example.com.')
    if not 12 <= len(contrasena) <= 128:
        errores.append('Contraseña: debe tener entre 12 y 128 caracteres.')
    return errores


def mostrar_login_roles(raiz_proyecto=None):
    raiz = Path(raiz_proyecto) if raiz_proyecto else RAIZ
    _estilos(raiz)
    left, right = st.columns([1.07,.93], gap='large', vertical_alignment='center')
    with left:
        marca = _logo_html(raiz)
        st.markdown(f'''<section class="cai-role-welcome">
        <div class="cai-role-brand">{marca}<div><div class="cai-role-brand-title">CurriculAi</div><div class="cai-role-brand-sub">TALENT INTELLIGENCE</div></div></div>
        <div class="cai-role-copy"><div class="cai-role-kicker">Conectamos talento y oportunidades</div>
        <h1 class="cai-role-title">Bienvenido a <span>CurriculAi</span></h1>
        <p class="cai-role-question">¿Buscas trabajo o los candidatos ideales para tu empresa?</p>
        <p class="cai-role-text">Nosotros te ayudamos a dar el siguiente paso. Unimos personas y empresas con tecnología que hace el reclutamiento más ágil, organizado y humano.</p>
        <div class="cai-role-paths">
            <div class="cai-role-path"><strong>Para empresas</strong><span>Gestiona vacantes, analiza currículums con inteligencia artificial y organiza tus procesos de selección.</span></div>
            <div class="cai-role-path"><strong>Para candidatos</strong><span>Crea tu cuenta y comienza a construir tu espacio personal para próximas oportunidades laborales.</span></div>
        </div></div>
        <div class="cai-role-foot">CurriculAi · Tecnología al servicio de las personas y las empresas.</div></section>''',unsafe_allow_html=True)
    with right:
        with st.container(key='cai_roles_form'):
            st.markdown('<h2>Iniciar sesión</h2><p style="color:#72839a">Selecciona tu tipo de acceso e ingresa tus datos.</p>', unsafe_allow_html=True)
            rol = st.radio('Tipo de acceso', ['Administrador','Candidato'], horizontal=True, key='cai_login_rol')
            with st.form(f'cai_roles_login_{rol}'):
                usuario = st.text_input('Usuario', placeholder='Tu nombre de usuario')
                contrasena = st.text_input('Contraseña', type='password', placeholder='Introduce tu contraseña')
                entrar = st.form_submit_button('Entrar a CurriculAi', use_container_width=True, type='primary')
            if entrar:
                if rol == 'Administrador':
                    configurado = acceso_configurado()
                    esperado = os.getenv('ADMIN_USERNAME', 'administrador').strip().lower()
                    usuario_valido = hmac.compare_digest(usuario.strip().lower().encode("utf-8"), esperado.encode("utf-8"))
                    # La verificación de la contraseña es la original, no se debilita.
                    if configurado and usuario_valido and verificar_contrasena(contrasena):
                        st.session_state['cai_autenticado'] = True
                        st.session_state['cai_usuario_rol'] = 'administrador'
                        st.rerun()
                    elif not configurado:
                        st.error('Acceso administrativo sin configurar. Revisa tus credenciales en .env.')
                    else:
                        st.error('Usuario o contraseña incorrectos.')
                else:
                    respuesta = _llamar('POST','/portal/ingresar', json={'usuario':usuario, 'contrasena':contrasena})
                    if respuesta is not None and respuesta.status_code == 200:
                        st.session_state['cai_portal_token'] = respuesta.json()['token']
                        st.session_state['cai_autenticado'] = True
                        st.session_state['cai_usuario_rol'] = 'candidato'
                        st.rerun()
                    else:
                        st.error(_mensaje_error(respuesta, 'No se pudo iniciar sesión.'))
            if rol == 'Candidato':
                with st.expander('¿Todavía no tienes cuenta? Regístrate'):
                    with st.form('cai_candidato_registro'):
                        nuevo_usuario = st.text_input('Elige tu usuario', placeholder='Ej. maria.garcia')
                        nombre = st.text_input('Nombre completo')
                        correo = st.text_input('Correo electrónico', placeholder='nombre@gmail.com')
                        nueva_pass = st.text_input('Crea una contraseña (mínimo 12 caracteres)', type='password')
                        repetida = st.text_input('Repite tu contraseña', type='password')
                        registrar = st.form_submit_button('Crear mi cuenta', use_container_width=True)
                    if registrar:
                        errores = _errores_registro(nuevo_usuario, nombre, correo, nueva_pass)
                        if nueva_pass != repetida:
                            errores.append('Las contraseñas no coinciden.')
                        if errores:
                            for mensaje in errores:
                                st.error(mensaje)
                        else:
                            respuesta = _llamar('POST', '/portal/registro', json={
                                'usuario': nuevo_usuario.strip().lower(),
                                'nombre': nombre.strip(),
                                'correo': correo.strip().lower(),
                                'contrasena': nueva_pass,
                            })
                            if respuesta is not None and respuesta.status_code == 201:
                                st.success('Cuenta creada correctamente. Ahora inicia sesión.')
                            elif respuesta is not None and respuesta.status_code == 409:
                                st.error('Ese nombre de usuario o correo ya está registrado. Prueba con otro o inicia sesión.')
                            else:
                                st.error(_mensaje_error(respuesta, 'No se pudo crear la cuenta.'))
            st.divider()
            g, f = st.columns(2)
            g.button('Google · Próximamente', disabled=True, use_container_width=True)
            f.button('Facebook · Próximamente', disabled=True, use_container_width=True)
            st.markdown('<p class="cai-role-note">Acceso seguro con usuario y contraseña. Google y Facebook requerirán integración OAuth real antes de habilitarse.</p>',unsafe_allow_html=True)


def _cerrar_sesion_candidato():
    token = st.session_state.get('cai_portal_token')
    if token:
        _llamar('POST','/portal/salir',headers={'Authorization':f'Bearer {token}'})
    for llave in ('cai_portal_token','cai_autenticado','cai_usuario_rol'):
        st.session_state.pop(llave, None)
    st.rerun()


def mostrar_portal_candidato():
    """Expediente personal. Conserva intactos el login y el rol administrativo."""
    from servicios.portal_expediente_ui import mostrar_expediente_candidato
    mostrar_expediente_candidato()

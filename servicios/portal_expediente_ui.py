"""Vista Streamlit del expediente laboral de cada candidato autenticado."""
from __future__ import annotations

from io import BytesIO
import html

import requests
import streamlit as st

from servicios.portal_campos import CAMPOS, JORNADAS, MODALIDADES, NIVELES, SEXOS


def _error(respuesta):
    if respuesta is None:
        return 'No se pudo conectar con FastAPI.'
    try:
        detalle = respuesta.json().get('detail', '')
        if isinstance(detalle, str) and detalle:
            return detalle
        if isinstance(detalle, list):
            return '; '.join(str(e.get('msg', 'Dato inválido')) for e in detalle[:3])
    except (ValueError, AttributeError, TypeError):
        pass
    return f'No se completó la operación (HTTP {respuesta.status_code}).'


def _opciones(etiqueta, opciones, actual, **kwargs):
    lista = list(opciones)
    posicion = lista.index(actual) if actual in lista else 0
    return st.selectbox(etiqueta, lista, index=posicion, **kwargs)


def _documento_cv(datos):
    """Crea un DOCX a partir del perfil; no reproduce ni modifica archivos subidos."""
    from docx import Document
    from docx.shared import Pt, RGBColor

    doc = Document()
    base = doc.styles['Normal']
    base.font.name = 'Aptos'
    base.font.size = Pt(10)
    base.font.color.rgb = RGBColor(37, 56, 78)
    doc.add_heading(datos.get('nombre') or 'Currículum profesional', 0)
    contacto = ' | '.join(t for t in (
        datos.get('correo'), datos.get('telefono'),
        ', '.join(t for t in (datos.get('municipio'), datos.get('estado')) if t)
    ) if t)
    if contacto:
        doc.add_paragraph(contacto)
    secciones = [
        ('Perfil profesional', [datos.get('resumen_profesional')]),
        ('Objetivo laboral', [datos.get('puesto_deseado'), datos.get('area_interes')]),
        ('Formación académica', [datos.get('nivel_estudios'), datos.get('carrera'),
                                 datos.get('institucion'), datos.get('estudios_detalle')]),
        ('Experiencia', [
            'Busco mi primer empleo' if datos.get('primer_empleo') else
            f"{datos.get('anos_experiencia', 0)} año(s) de experiencia",
            datos.get('experiencia'),
        ]),
        ('Habilidades', [datos.get('habilidades')]),
        ('Fortalezas', [datos.get('fortalezas')]),
        ('Idiomas', [datos.get('idiomas')]),
        ('Cursos y certificaciones', [datos.get('certificaciones')]),
        ('Preferencias laborales', [datos.get('zonas_preferidas'),
                                   datos.get('modalidad'), datos.get('jornada'), datos.get('disponibilidad')]),
    ]
    for titulo, campos in secciones:
        contenido = [str(v).strip() for v in campos if v is not None and str(v).strip()]
        if contenido:
            doc.add_heading(titulo, level=2)
            for parte in contenido:
                doc.add_paragraph(parte)
    # Ni sexo ni domicilio detallado entran al DOCX generado.
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def mostrar_expediente_candidato():
    """Nunca consulta servicios.api (clave admin). Opera con Bearer propio."""
    from servicios.login_roles import _llamar, _cerrar_sesion_candidato
    from servicios.api import API_URL

    token = st.session_state.get('cai_portal_token', '')
    if not token:
        st.session_state['cai_autenticado'] = False
        st.rerun()
        return
    headers = {'Authorization': f'Bearer {token}'}
    cuenta = _llamar('GET', '/portal/yo', headers=headers)
    if cuenta is None:
        st.error('FastAPI no responde. Comprueba que está iniciado.')
        if st.button('Cerrar sesión'):
            _cerrar_sesion_candidato()
        return
    if cuenta.status_code != 200:
        st.warning('La sesión caducó o dejó de ser válida. Vuelve a entrar.')
        if st.button('Volver al inicio'):
            _cerrar_sesion_candidato()
        return

    res = _llamar('GET', '/portal/expediente', headers=headers)
    if res is None or not res.ok:
        st.error(_error(res))
        st.info('Si acabas de instalar el parche, reinicia FastAPI en SQLite de pruebas.')
        return
    p = res.json()
    compartido_resp = _llamar('GET', '/portal/expediente/compartido', headers=headers)
    compartido = compartido_resp.json() if compartido_resp is not None and compartido_resp.ok else {}
    avisos_resp = _llamar('GET', '/portal/notificaciones', headers=headers)
    avisos = avisos_resp.json() if avisos_resp is not None and avisos_resp.ok else []
    if not isinstance(avisos, list):
        avisos = []
    sin_leer = sum(not item.get('leida', False) for item in avisos)

    st.markdown('''<style>
    .cai-portal-hero{padding:22px 28px;border-radius:17px;background:linear-gradient(105deg,#eaf5fc,#f6faff);
      border:1px solid #d4e7f5;margin-bottom:17px}
    .cai-portal-hero .cai-kicker{letter-spacing:2px;color:#2673a8;font-size:12px;font-weight:800}
    .cai-portal-hero h1{margin:9px 0 6px;color:#193b64;font-size:35px;line-height:1.2}
    .cai-portal-hero p{color:#566f86;font-size:14px;margin:0}
    [data-testid="stTabs"] button p{font-weight:650}
    .cai-portal-label{color:#193B64;font-weight:800;font-size:.95rem;margin:.25rem 0}
    .cai-portal-panel{border:1px solid #d4e3ef;border-radius:16px;padding:17px 20px;
      background:#fff;margin:8px 0 13px;box-shadow:0 4px 18px rgba(13,50,85,.035)}
    .cai-portal-panel h4{font-size:1.1rem;color:#193B64;margin:0 0 7px}
    .cai-portal-panel p{font-size:.91rem;color:#536d84;line-height:1.55;margin:5px 0}
    .cai-portal-mini{font-size:.75rem;color:#39769e;font-weight:850;letter-spacing:1.1px}
    </style>''', unsafe_allow_html=True)

    from servicios.barra_candidato import mostrar_barra_candidato

    nombre_candidato = html.escape(str(p.get('nombre') or cuenta.json().get('nombre') or 'Candidato')[:100])
    seccion = mostrar_barra_candidato(
        nombre=nombre_candidato,
        sin_leer=sin_leer,
        cerrar_sesion=_cerrar_sesion_candidato,
    )
    st.markdown(
        '<div class="cai-portal-hero"><div class="cai-kicker">TU ESPACIO PROFESIONAL</div>'
        f'<h1>Bienvenido, {nombre_candidato}, a CurriculAi</h1>'
        '<p>Encuentra oportunidades, mantén actualizado tu CV y sigue tus procesos de selección.</p>'
        '</div>', unsafe_allow_html=True,
    )

    if st.session_state.get('cai_expediente_mensaje'):
        st.success(st.session_state.pop('cai_expediente_mensaje'))

    if seccion == 'Inicio':
        avance = p.get('completitud', {})
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            st.metric('Perfil completo', f"{avance.get('porcentaje', 0)} %")
        with c2:
            st.metric('Datos completados', f"{avance.get('completados', 0)} / {avance.get('total', 13)}")
        with c3:
            st.write('**Avance de tu expediente**')
            st.progress(float(avance.get('porcentaje', 0)) / 100)
            st.caption('El sexo y el domicilio detallado son opcionales y no afectan este porcentaje.')
        fila_estado = st.columns([1.4, 1.2, 1.4], gap="small")
        with fila_estado[0]:
            st.caption(f"CV en reclutamiento: {'Compartido' if compartido.get('compartido') else 'Privado'}")
        with fila_estado[1]:
            st.caption(f"Notificaciones sin leer: {sin_leer}")
        with fila_estado[2]:
            if compartido.get('compartido'):
                st.caption(f"Expediente administrativo #{compartido.get('candidato_id')}")
            else:
                st.caption('Comparte tu CV para entrar al Radar de talentos')
        faltantes = avance.get('pendientes', [])
        if faltantes:
            with st.expander('¿Qué me falta para llegar al 100 %?', expanded=not p.get('cv_cargado')):
                for item in faltantes:
                    st.write(f'• {item}')
        else:
            st.success('¡Tu perfil laboral está completo! Puedes actualizarlo cuando quieras.')

        if not p.get('cv_cargado'):
            st.info('**Primer paso recomendado:** abre «Mi currículum» y elige entre crearlo a mano o subir un archivo.')

    def guardar(cambios, mensaje):
        payload = {'nombre': p['nombre']}
        payload.update({campo: p.get(campo) for campo in CAMPOS})
        payload.update(cambios)
        resultado = _llamar('PUT', '/portal/expediente', headers=headers, json=payload)
        if resultado is not None and resultado.ok:
            st.session_state['cai_expediente_mensaje'] = mensaje
            st.rerun()
        else:
            st.error(_error(resultado))

    # Navegación superior fija (la barra del administrador no se modifica).
    # Se dibuja un solo apartado por ejecución, sin recrear todos los formularios.

    if seccion == 'Inicio':
        st.subheader('Tu perfil de un vistazo')
        st.markdown('<div class="cai-portal-panel"><span class="cai-portal-mini">TU SIGUIENTE OPORTUNIDAD</span>'
                    '<h4>Tu perfil, tus vacantes y tus entrevistas en un solo lugar</h4>'
                    '<p>Completa tu currículum, compártelo cuando quieras participar en evaluaciones '
                    'y postúlate a las vacantes que te interesen. Puedes consultar los resultados aquí.</p>'
                    '</div>', unsafe_allow_html=True)
        st.write(f"**Nombre:** {p.get('nombre') or 'Sin registrar'}")
        st.write(f"**Correo:** {p.get('correo')}")
        st.write(f"**Puesto deseado:** {p.get('puesto_deseado') or 'Sin definir'}")
        st.write(f"**Escolaridad:** {p.get('nivel_estudios') or 'Sin registrar'}")
        st.write(f"**Zona de interés:** {p.get('zonas_preferidas') or 'Sin registrar'}")
        st.write(f"**Archivo CV:** {p.get('cv_nombre') or 'Todavía no has creado ni subido un currículum'}")
        st.markdown('**Accesos rápidos**')
        acceso_cols = st.columns(3, gap='small')
        for col, (etiqueta, destino) in zip(acceso_cols, [
            ('Preparar mi CV', 'Mi CV'),
            ('Explorar vacantes', 'Vacantes'),
            ('Ver mis avisos', 'Notificaciones'),
        ]):
            with col:
                if st.button(etiqueta, key=f'cai_atajo_{destino}', use_container_width=True):
                    st.session_state['cai_candidato_seccion'] = destino
                    st.rerun()
        st.divider()
        st.subheader('Generar mi currículum desde mi perfil')
        st.caption('Puedes editar tus datos en Mi perfil y descargar un DOCX actualizado. No incluye sexo ni domicilio específico.')
        if p.get('nombre') and (p.get('habilidades') or p.get('experiencia') or p.get('estudios_detalle')):
            try:
                st.download_button('Descargar mi CV en Word (.docx)',
                    data=_documento_cv(p), file_name='CurriculAi_mi_curriculum.docx',
                    mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    type='primary')
            except ImportError:
                st.warning('Para generar Word instala python-docx en el entorno.')
        else:
            st.info('Agrega experiencia, estudios o habilidades para generar el documento.')

    if seccion == 'Mi perfil':
        perfil_tabs = st.tabs(['Datos personales', 'Estudios y fortalezas', 'Experiencia y empleo'])
        with perfil_tabs[0]:
            st.subheader('Datos personales y contacto')
            st.caption('El domicilio puede ser general: colonia, municipio y estado. Evita poner calle o número de casa.')
            with st.form('cai_expediente_datos'):
                nombre = st.text_input('Nombre completo *', value=p.get('nombre', ''), max_chars=100)
                st.text_input('Correo de tu cuenta', value=p.get('correo', ''), disabled=True)
                c_telefono, c_sexo = st.columns(2)
                with c_telefono:
                    telefono = st.text_input('Teléfono de contacto', value=p.get('telefono', ''), max_chars=30)
                with c_sexo:
                    sexo = _opciones('Sexo (opcional)', SEXOS, p.get('sexo', ''))
                c_estado, c_municipio = st.columns(2)
                with c_estado:
                    estado = st.text_input('Estado', value=p.get('estado', ''), max_chars=90)
                with c_municipio:
                    municipio = st.text_input('Municipio o alcaldía', value=p.get('municipio', ''), max_chars=110)
                domicilio = st.text_input('Domicilio general (opcional)', value=p.get('domicilio_general', ''),
                                           placeholder='Ej. Centro, Ixtapaluca; sin calle ni número', max_chars=180)
                enviar = st.form_submit_button('Guardar datos personales', type='primary')
            if enviar:
                guardar({'nombre': nombre, 'telefono': telefono, 'sexo': sexo, 'estado': estado,
                         'municipio': municipio, 'domicilio_general': domicilio}, 'Tus datos personales se actualizaron.')
            st.caption('El sexo es opcional y no se utiliza para calcular compatibilidad laboral.')

        with perfil_tabs[1]:
            st.subheader('Estudios, habilidades y fortalezas')
            with st.form('cai_expediente_formacion'):
                nivel = _opciones('Máximo nivel de estudios', NIVELES, p.get('nivel_estudios', ''))
                c_carrera, c_inst = st.columns(2)
                with c_carrera:
                    carrera = st.text_input('Carrera, especialidad o formación', value=p.get('carrera', ''), max_chars=180)
                with c_inst:
                    institucion = st.text_input('Escuela o institución', value=p.get('institucion', ''), max_chars=180)
                estudios = st.text_area('Formación: periodos, logros o estudios en curso', value=p.get('estudios_detalle', ''),
                                         placeholder='Ej. Ingeniería en Sistemas Computacionales, 2022–2026', max_chars=2000)
                habilidades = st.text_area('Habilidades y conocimientos técnicos', value=p.get('habilidades', ''),
                                             placeholder='Ej. Excel, atención a clientes, Python, SAP, ventas...', max_chars=2000)
                fortalezas = st.text_area('Fortalezas personales', value=p.get('fortalezas', ''),
                                            placeholder='Ej. Organización, liderazgo, trabajo en equipo, comunicación...', max_chars=1500)
                idiomas = st.text_area('Idiomas y nivel', value=p.get('idiomas', ''),
                                         placeholder='Ej. Español nativo, inglés B1', max_chars=1000)
                certificados = st.text_area('Cursos, certificados y reconocimientos', value=p.get('certificaciones', ''), max_chars=1500)
                guardar_formacion = st.form_submit_button('Guardar estudios y habilidades', type='primary')
            if guardar_formacion:
                guardar({'nivel_estudios': nivel, 'carrera': carrera, 'institucion': institucion,
                         'estudios_detalle': estudios, 'habilidades': habilidades,
                         'fortalezas': fortalezas, 'idiomas': idiomas, 'certificaciones': certificados},
                        'Tus estudios y fortalezas se actualizaron.')

        with perfil_tabs[2]:
            st.subheader('Experiencia y preferencias laborales')
            with st.form('cai_expediente_empleo'):
                resumen = st.text_area('Sobre mí / resumen profesional', value=p.get('resumen_profesional', ''),
                                        placeholder='Preséntate en tres o cuatro líneas. ¿Qué sabes hacer y qué aportas?', max_chars=1800)
                primer = st.checkbox('Estoy buscando mi primer empleo', value=bool(p.get('primer_empleo')))
                anos = st.number_input('Años de experiencia', min_value=0, max_value=60,
                                       value=int(p.get('anos_experiencia', 0)), step=1, disabled=primer)
                experiencia = st.text_area('Experiencia laboral (puestos, funciones y logros)', value=p.get('experiencia', ''),
                                            placeholder='Empresa (opcional), puesto, periodo, tareas y resultados...', max_chars=4000)
                c_puesto, c_area = st.columns(2)
                with c_puesto:
                    puesto = st.text_input('¿De qué quieres trabajar?', value=p.get('puesto_deseado', ''), max_chars=150)
                with c_area:
                    area = st.text_input('Área o sector de interés', value=p.get('area_interes', ''), max_chars=150)
                zonas = st.text_input('Zonas donde puedes trabajar', value=p.get('zonas_preferidas', ''),
                                       placeholder='Ej. Ixtapaluca, Chalco, CDMX oriente, remoto', max_chars=250)
                c_modalidad, c_jornada = st.columns(2)
                with c_modalidad:
                    modalidad = _opciones('Modalidad', MODALIDADES, p.get('modalidad', ''))
                with c_jornada:
                    jornada = _opciones('Tipo de jornada', JORNADAS, p.get('jornada', ''))
                disponibilidad = st.text_input('Disponibilidad para comenzar', value=p.get('disponibilidad', ''),
                                                 placeholder='Ej. Inmediata / en 15 días', max_chars=100)
                guardar_empleo = st.form_submit_button('Guardar experiencia y preferencias', type='primary')
            if guardar_empleo:
                guardar({'resumen_profesional': resumen, 'primer_empleo': primer,
                         'anos_experiencia': 0 if primer else int(anos), 'experiencia': experiencia,
                         'puesto_deseado': puesto, 'area_interes': area, 'zonas_preferidas': zonas,
                         'modalidad': modalidad, 'jornada': jornada, 'disponibilidad': disponibilidad},
                        'Tu experiencia y preferencias se actualizaron.')

    if seccion == 'Mi CV':
        st.subheader('Mi currículum')
        st.caption('Puedes crear un CV con tus datos, sin tener un archivo previo, o subir uno existente.')
        if p.get('cv_cargado'):
            st.success(f"CV guardado: {p.get('cv_nombre', 'Currículum')}")
            st.caption('Puedes actualizarlo, sustituirlo o retirarlo cuando quieras.')
        else:
            st.info('Elige una de las dos opciones para preparar tu currículum.')

        opcion_crear, opcion_subir = st.tabs(['Crear mi CV desde cero', 'Subir mi CV'])
        with opcion_crear:
            st.markdown('**Crea tu currículum manualmente**')
            st.caption('Los campos se guardan también en Mi perfil. Puedes corregirlos después y descargar el CV en Word.')
            with st.form('cai_crear_cv_manual'):
                nombre_cv = st.text_input('Nombre completo *', value=str(p.get('nombre') or ''), max_chars=100)
                telefono_cv = st.text_input('Teléfono de contacto', value=str(p.get('telefono') or ''), max_chars=30)
                c_zona1, c_zona2 = st.columns(2)
                with c_zona1:
                    estado_cv = st.text_input('Estado', value=str(p.get('estado') or ''), max_chars=90)
                with c_zona2:
                    municipio_cv = st.text_input('Municipio o alcaldía', value=str(p.get('municipio') or ''), max_chars=110)
                resumen_cv = st.text_area('Perfil profesional / Sobre mí', value=str(p.get('resumen_profesional') or ''),
                    max_chars=1800, placeholder='Describe tus conocimientos y lo que puedes aportar')
                c_puesto_cv, c_nivel_cv = st.columns(2)
                with c_puesto_cv:
                    puesto_cv = st.text_input('¿De qué quieres trabajar?', value=str(p.get('puesto_deseado') or ''), max_chars=150)
                with c_nivel_cv:
                    nivel_cv = _opciones('Último nivel de estudios', NIVELES, p.get('nivel_estudios', ''), key='manual_nivel_cv')
                carrera_cv = st.text_input('Carrera / Especialidad', value=str(p.get('carrera') or ''), max_chars=180)
                escuela_cv = st.text_input('Institución educativa', value=str(p.get('institucion') or ''), max_chars=180)
                estudios_cv = st.text_area('Estudios, logros y formación', value=str(p.get('estudios_detalle') or ''), max_chars=2000)
                primer_cv = st.checkbox('Estoy buscando mi primer empleo', value=bool(p.get('primer_empleo')))
                experiencia_cv = st.text_area('Experiencia laboral, actividades y logros', value=str(p.get('experiencia') or ''),
                    max_chars=4000, placeholder='Si no tienes experiencia, puedes indicar prácticas y proyectos')
                habilidades_cv = st.text_area('Habilidades técnicas', value=str(p.get('habilidades') or ''), max_chars=2000,
                    placeholder='Ej. Excel, SAP, atención al cliente, Python...')
                fortalezas_cv = st.text_area('Fortalezas', value=str(p.get('fortalezas') or ''), max_chars=1500)
                idiomas_cv = st.text_input('Idiomas y nivel', value=str(p.get('idiomas') or ''), max_chars=1000)
                cursos_cv = st.text_area('Cursos y certificaciones', value=str(p.get('certificaciones') or ''), max_chars=1500)
                zona_cv = st.text_input('Zonas donde buscas trabajar', value=str(p.get('zonas_preferidas') or ''), max_chars=250)
                st.caption('El sexo y el domicilio detallado no se incluyen en el CV creado ni en el ranking.')
                sustituir_cv = st.checkbox('Acepto reemplazar mi CV actual por esta versión creada manualmente',
                    value=False, disabled=not bool(p.get('cv_cargado'))) if p.get('cv_cargado') else False
                guardar_cv = st.form_submit_button('Guardar mi CV creado a mano', type='primary', use_container_width=True)
            if guardar_cv:
                if p.get('cv_cargado') and not sustituir_cv:
                    st.warning('Confirma que deseas sustituir tu CV actual para guardar la versión manual.')
                else:
                    perfil_cv = {'nombre': nombre_cv, **{k: p.get(k) for k in CAMPOS}}
                    perfil_cv.update({'telefono': telefono_cv, 'estado': estado_cv, 'municipio': municipio_cv,
                        'resumen_profesional': resumen_cv, 'puesto_deseado': puesto_cv,
                        'nivel_estudios': nivel_cv, 'carrera': carrera_cv, 'institucion': escuela_cv,
                        'estudios_detalle': estudios_cv, 'primer_empleo': primer_cv,
                        'anos_experiencia': 0 if primer_cv else p.get('anos_experiencia', 0),
                        'experiencia': experiencia_cv, 'habilidades': habilidades_cv,
                        'fortalezas': fortalezas_cv, 'idiomas': idiomas_cv,
                        'certificaciones': cursos_cv, 'zonas_preferidas': zona_cv})
                    respuesta_cv = _llamar('POST', '/portal/expediente/cv/manual', headers=headers,
                        json={'perfil': perfil_cv, 'reemplazar_cv': bool(sustituir_cv)})
                    if respuesta_cv is not None and respuesta_cv.ok:
                        st.session_state['cai_expediente_mensaje'] = (
                            'CV creado y guardado. Para que los reclutadores evalúen esta versión, '
                            've a Compartir mi CV y autoriza el envío.')
                        st.rerun()
                    else:
                        st.error(_error(respuesta_cv))
            if p.get('nombre') and (p.get('habilidades') or p.get('experiencia') or p.get('estudios_detalle')):
                try:
                    st.download_button('Descargar mi CV en Word (.docx)', data=_documento_cv(p),
                        file_name='CurriculAi_mi_curriculum.docx',
                        mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                except ImportError:
                    st.warning('Para descargar Word debes instalar python-docx.')
                st.caption('La descarga se genera con los datos guardados; guarda el formulario primero si hiciste cambios.')
        with opcion_subir:
            st.caption('Archivos aceptados: PDF, DOCX, TXT, PNG, JPG o WEBP; máximo 8 MB.')
            archivo = st.file_uploader('Selecciona tu currículum',
                                       type=['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'webp'], key='cai_exp_cv')
            if st.button('Cargar o reemplazar mi currículum', type='primary', disabled=archivo is None):
                if archivo.size > 8 * 1024 * 1024:
                    st.error('El archivo supera los 8 MB permitidos.')
                else:
                    with st.spinner('Procesando tu CV...'):
                        try:
                            r = requests.post(f'{API_URL}/portal/expediente/cv', headers=headers,
                                files={'archivo': (archivo.name, archivo.getvalue(), archivo.type or 'application/octet-stream')},
                                timeout=120)
                        except requests.RequestException:
                            r = None
                    if r is not None and r.ok:
                        st.session_state['cai_expediente_mensaje'] = 'Tu CV se cargó o reemplazó correctamente.'
                        st.rerun()
                    else:
                        st.error(_error(r))
        if p.get('cv_cargado'):
            with st.expander('Ver o corregir texto extraído del CV'):
                rc = _llamar('GET', '/portal/expediente/cv', headers=headers)
                if rc is None or not rc.ok:
                    st.error(_error(rc))
                else:
                    with st.form('cai_corregir_texto_cv'):
                        texto = st.text_area('Texto extraído (editable)', value=rc.json().get('texto', ''), height=300,
                                             max_chars=15000)
                        corregir = st.form_submit_button('Guardar correcciones de texto')
                    if corregir:
                        rr = _llamar('PUT', '/portal/expediente/cv', headers=headers, json={'texto': texto})
                        if rr is not None and rr.ok:
                            st.session_state['cai_expediente_mensaje'] = 'Texto de tu CV corregido.'
                            st.rerun()
                        else:
                            st.error(_error(rr))
            with st.expander('Retirar mi CV del expediente'):
                confirmar = st.checkbox('Confirmo retirar mi CV del perfil y la copia compartida para evaluación', key='cai_exp_cv_confirmar')
                if st.button('Retirar CV', disabled=not confirmar):
                    rr = _llamar('DELETE', '/portal/expediente/cv', headers=headers)
                    if rr is not None and rr.ok:
                        st.session_state['cai_expediente_mensaje'] = 'CV retirado del perfil y del ranking. Los registros de postulaciones se conservan.'
                        st.rerun()
                    else:
                        st.error(_error(rr))
        st.caption('Se almacena únicamente el texto del CV y su nombre, no el PDF o imagen original. '
                   'Editar aquí el texto extraído no modifica el documento original.')
        st.info('Tu perfil es privado y no expone rankings de otros candidatos ni información empresarial.')
        if p.get('cv_cargado'):
            with st.expander('Compartir mi CV con reclutadores', expanded=not bool(compartido.get('compartido'))):
                if compartido.get('compartido'):
                    st.success('Tu CV ya forma parte del pool de evaluación del administrador.')
                    st.caption('Si actualizaste tu perfil o CV, pulsa Compartir de nuevo para sincronizarlo. '
                               'Se eliminarán los puntajes calculados con la versión anterior.')
                else:
                    st.info('Puedes compartir tu CV para que aparezca entre los candidatos evaluables, '
                            'incluso antes de postularte a una vacante.')
                st.caption('Se compartirán nombre, contacto, perfil laboral, habilidades y texto de CV. '
                           'Sexo y domicilio detallado no se copian como campos del perfil evaluable. '
                           'El reclutador puede consultar el texto del CV que proporcionaste.')
                acepto_compartir = st.checkbox(
                    'Autorizo compartir estos datos con el equipo de reclutamiento', key='cai_sync_permiso')
                if st.button('Compartir o actualizar mi CV', disabled=not acepto_compartir,
                             key='cai_cv_compartir', type='primary'):
                    r = _llamar('POST', '/portal/expediente/compartir', headers=headers)
                    if r is not None and r.ok:
                        st.session_state['cai_expediente_mensaje'] = r.json().get('mensaje', 'CV compartido.')
                        st.rerun()
                    else:
                        st.error(_error(r))

    # Nuevas secciones. No modifican los formularios existentes de perfil o CV.
    if seccion == 'Vacantes':
        st.subheader('Vacantes disponibles')
        st.caption('Aquí aparecen solo las vacantes publicadas por el administrador. Postularte comparte una copia de tu CV laboral con reclutamiento.')
        respuesta = _llamar('GET', '/portal/vacantes', headers=headers)
        if respuesta is None or not respuesta.ok:
            st.error(_error(respuesta))
        else:
            vacantes = respuesta.json()
            if not isinstance(vacantes, list):
                vacantes = []
            q = st.text_input('Buscar trabajo', placeholder='Puesto, experiencia o habilidades...', key='cai_buscar_vacante_portal')
            if q.strip():
                vacantes = [v for v in vacantes if q.casefold().strip() in
                            (str(v.get('titulo') or '') + ' ' + str(v.get('descripcion') or '')).casefold()]
            st.caption(f'{len(vacantes)} oportunidad(es) publicada(s)')
            if not vacantes:
                st.info('No encontramos vacantes con esos filtros. Revisa nuevamente más adelante.')
            for i in range(0, len(vacantes), 2):
                cols = st.columns(2, gap='large')
                for col, v in zip(cols, vacantes[i:i + 2]):
                    vid = v.get('id')
                    titulo_v = str(v.get('titulo') or 'Vacante')
                    with col:
                        st.markdown(
                            '<div style="border:1px solid #d7e3ef;border-radius:14px;overflow:hidden;'
                            'background:#fff;margin:3px 0 12px">'
                            '<div style="background:#193B64;color:#fff;padding:14px 18px">'
                            '<div style="font-size:.7rem;letter-spacing:.13em;opacity:.8;font-weight:800">'
                            'VACANTE PUBLICADA</div><div style="font-size:1.17rem;font-weight:800">'
                            f'{html.escape(titulo_v[:95])}</div></div></div>',
                            unsafe_allow_html=True,
                        )
                        with st.expander('Ver descripción y requisitos'):
                            st.write(v.get('descripcion') or 'Sin información.')
                        with st.expander('Postularme a esta vacante'):
                            st.caption('Al enviar tu postulación autorizas compartir tu CV y perfil laboral con el administrador. No se comparte tu sexo ni domicilio detallado.')
                            acepto = st.checkbox('Confirmo que deseo enviar mi CV', key=f'cai_autoriza_{vid}')
                            if st.button('Enviar postulación', key=f'cai_aplicar_{vid}',
                                         disabled=not acepto, type='primary', use_container_width=True):
                                r = _llamar('POST', f'/portal/vacantes/{vid}/postularse', headers=headers)
                                if r is not None and r.ok:
                                    st.session_state['cai_expediente_mensaje'] = '¡Postulación registrada! Puedes consultarla en Mis postulaciones.'
                                    st.rerun()
                                else:
                                    st.error(_error(r))

    if seccion == 'Mis postulaciones':
        st.subheader('Mis postulaciones')
        st.caption('Consulta solo tus solicitudes y los estados que se pueden comunicar al candidato. No mostramos puntuaciones ni evaluaciones internas.')
        respuesta = _llamar('GET', '/portal/postulaciones', headers=headers)
        if respuesta is None or not respuesta.ok:
            st.error(_error(respuesta))
        else:
            solicitudes = respuesta.json()
            if not isinstance(solicitudes, list):
                solicitudes = []
            if not solicitudes:
                st.info('Todavía no has enviado postulaciones. Explora la sección Vacantes.')
            for item in solicitudes:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1], vertical_alignment='center')
                    with c1:
                        st.markdown(f"**{html.escape(str(item.get('vacante') or 'Vacante'))}**")
                        st.caption(f"Solicitud #{item.get('id')} · {str(item.get('creada_en') or '')[:10]}")
                    with c2:
                        st.markdown(f"**{html.escape(str(item.get('estado') or 'En revisión'))}**")
                    if item.get('estado') not in ('Retirada', 'Seleccionado', 'No seleccionado'):
                        with st.expander('Retirar postulación'):
                            st.warning('Retirar la solicitud no elimina tu cuenta ni tu expediente. El reclutador conservará el registro de la solicitud.')
                            confirmacion = st.checkbox('Confirmo que quiero retirar esta postulación', key=f'cai_retirar_confirm_{item.get("id")}')
                            if st.button('Retirar mi solicitud', disabled=not confirmacion,
                                         key=f'cai_retirar_{item.get("id")}'):
                                r = _llamar('POST', f'/portal/postulaciones/{item.get("id")}/retirar', headers=headers)
                                if r is not None and r.ok:
                                    st.session_state['cai_expediente_mensaje'] = 'Postulación retirada.'
                                    st.rerun()
                                else:
                                    st.error(_error(r))


    if seccion == 'Mis entrevistas':
        st.subheader('Mis entrevistas')
        st.caption('Las citas se muestran solo cuando están vinculadas a una postulación de esta cuenta.')
        r_entrevistas = _llamar('GET', '/portal/entrevistas', headers=headers)
        if r_entrevistas is None or not r_entrevistas.ok:
            st.error(_error(r_entrevistas))
        else:
            citas = r_entrevistas.json()
            if not citas:
                st.info('Todavía no tienes entrevistas programadas. Revisa tus postulaciones.')
            for i in range(0, len(citas), 2):
                columnas = st.columns(2, gap='large')
                for col, cita in zip(columnas, citas[i:i+2]):
                    with col:
                        vacante = html.escape(str(cita.get('vacante') or 'Vacante'))
                        fecha = html.escape(str(cita.get('fecha') or 'Por definir'))
                        hora = html.escape(str(cita.get('hora') or 'Por definir'))
                        lugar = html.escape(str(cita.get('lugar') or 'Por definir'))
                        estado_cita = html.escape(str(cita.get('estado') or 'Programada'))
                        st.markdown(
                            '<div class="cai-portal-panel"><span class="cai-portal-mini">ENTREVISTA</span>'
                            f'<h4>{vacante}</h4><p>📅 {fecha} · {hora}</p>'
                            f'<p>📍 {lugar}</p><p><b>Estado:</b> {estado_cita}</p></div>',
                            unsafe_allow_html=True,
                        )

    if seccion == 'Notificaciones':
        st.subheader('Mis notificaciones')
        st.caption('Avisos guardados en tu cuenta. Solo tú puedes consultarlos y marcarlos como leídos.')
        if not avisos:
            st.info('No tienes notificaciones todavía. Las actualizaciones de tus procesos aparecerán aquí.')
        for i in range(0, len(avisos), 2):
            columnas = st.columns(2, gap='large')
            for col, aviso in zip(columnas, avisos[i:i+2]):
                with col:
                    titulo_aviso = html.escape(str(aviso.get('titulo') or 'Aviso'))
                    mensaje_aviso = html.escape(str(aviso.get('mensaje') or ''))
                    fecha_aviso = html.escape(str(aviso.get('creada_en') or '')[:16].replace('T', ' '))
                    leida = bool(aviso.get('leida'))
                    indicador = 'LEÍDA' if leida else 'NUEVA'
                    st.markdown(
                        '<div class="cai-portal-panel">'
                        f'<span class="cai-portal-mini">{indicador} · {fecha_aviso}</span>'
                        f'<h4>{titulo_aviso}</h4><p>{mensaje_aviso}</p></div>',
                        unsafe_allow_html=True,
                    )
                    if not leida and st.button('Marcar como leída', key=f'leer_aviso_{aviso.get("id")}',
                                                use_container_width=True):
                        rr = _llamar('PUT', f'/portal/notificaciones/{aviso.get("id")}/leida', headers=headers)
                        if rr is not None and rr.ok:
                            st.rerun()
                        else:
                            st.error(_error(rr))

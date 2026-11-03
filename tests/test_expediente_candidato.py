"""Pruebas aisladas del expediente del portal (nunca usan Supabase)."""
from pathlib import Path
import os
import subprocess
import sys


def test_expediente_por_usuario_y_cv_privado(tmp_path):
    raiz = Path(__file__).resolve().parents[1]
    script = r'''
from fastapi import FastAPI
from fastapi.testclient import TestClient
from servicios.portal_auth import montar_portal

api = FastAPI()
montar_portal(api)

with TestClient(api) as c:
    def entrar(nombre):
        r = c.post('/portal/registro', json={
            'usuario': nombre, 'nombre': 'Persona Ficticia',
            'correo': f'{nombre}@example.com', 'contrasena': 'Prueba-Ficticia_123456!'
        })
        assert r.status_code == 201, r.text
        r = c.post('/portal/ingresar', json={'usuario': nombre,
                  'contrasena': 'Prueba-Ficticia_123456!'})
        assert r.status_code == 200, r.text
        return {'Authorization': 'Bearer ' + r.json()['token']}

    a = entrar('ana.cv')
    b = entrar('luis.cv')
    assert c.get('/portal/expediente').status_code == 401
    assert c.get('/portal/expediente/cv').status_code == 401
    assert c.put('/portal/expediente', json={'nombre': 'Intruso'}).status_code == 401
    assert c.post('/portal/expediente/cv', files={'archivo': ('x.txt', b'Prueba de cv simulada', 'text/plain')}).status_code == 401
    assert c.get('/portal/expediente', headers=a).json()['completitud']['porcentaje'] < 100
    assert c.get('/portal/expediente', headers=b).json()['cv_cargado'] is False

    datos = {
        'nombre':'Ana Ficticia', 'telefono':'5550002233','sexo':'Mujer',
        'estado':'México','municipio':'Chalco','domicilio_general':'Centro, Chalco',
        'nivel_estudios':'Bachillerato / Preparatoria','carrera':'Administración',
        'institucion':'Escuela Demo','estudios_detalle':'Bachillerato concluido',
        'certificaciones':'Excel', 'primer_empleo':False,'anos_experiencia':2,
        'experiencia':'Dos años en oficina con archivos digitales y reportes',
        'habilidades':'Excel, Word, archivo', 'fortalezas':'Organización, responsabilidad',
        'idiomas':'Español','resumen_profesional':'Auxiliar administrativa con experiencia',
        'puesto_deseado':'Auxiliar administrativo','area_interes':'Oficinas',
        'zonas_preferidas':'Chalco, Ixtapaluca','modalidad':'Presencial',
        'jornada':'Tiempo completo','disponibilidad':'Inmediata'
    }
    r = c.put('/portal/expediente',json=datos,headers=a)
    assert r.status_code == 200,r.text
    assert r.json()['completitud']['porcentaje'] < 100  # falta CV
    p_a = c.get('/portal/expediente',headers=a).json()
    p_b = c.get('/portal/expediente',headers=b).json()
    assert p_a['sexo'] == 'Mujer' and p_a['municipio'] == 'Chalco'
    assert p_b['sexo'] == '' and p_b['telefono'] == ''
    assert 'sexo' not in str(p_a['completitud']['pendientes']).lower()
    assert 'domicilio' not in str(p_a['completitud']['pendientes']).lower()

    mal = {**datos,'sexo':'Valor no válido'}
    assert c.put('/portal/expediente',json=mal,headers=a).status_code == 422
    mal = {**datos,'usuario_id': 2}
    assert c.put('/portal/expediente',json=mal,headers=a).status_code == 422

    cv = b'Experiencia en archivo, gestion documental, Excel, trabajo administrativo y reportes mensuales.'
    r = c.post('/portal/expediente/cv',headers=a,files={'archivo':('curriculum.txt',cv,'text/plain')})
    assert r.status_code == 200,r.text
    assert c.get('/portal/expediente',headers=a).json()['completitud']['porcentaje'] == 100
    assert c.get('/portal/expediente',headers=b).json()['cv_cargado'] is False
    assert c.get('/portal/expediente/cv',headers=b).json()['texto'] == ''

    cv2 = b'Otro curriculo actualizado con nuevos datos de atencion a clientes y uso avanzado de Excel.'
    r = c.post('/portal/expediente/cv',headers=a,files={'archivo':('version2.txt',cv2,'text/plain')})
    assert r.status_code == 200, r.text
    assert c.get('/portal/expediente/cv',headers=a).json()['nombre'] == 'version2.txt'
    r = c.put('/portal/expediente/cv',headers=a,
              json={'texto':'Texto corregido por el propietario con mas detalle de experiencia y formacion.'})
    assert r.status_code == 200,r.text
    assert 'Texto corregido' in c.get('/portal/expediente/cv',headers=a).json()['texto']
    assert c.delete('/portal/expediente/cv',headers=b).status_code == 200
    assert c.get('/portal/expediente',headers=a).json()['cv_cargado'] is True
    assert c.delete('/portal/expediente/cv',headers=a).status_code == 200
    assert c.get('/portal/expediente',headers=a).json()['cv_cargado'] is False
    assert c.get('/portal/expediente',headers=a).json()['completitud']['porcentaje'] < 100

    assert c.post('/portal/expediente/cv',headers=a,
           files={'archivo':('mal.exe',b'not a valid cv','application/octet-stream')}).status_code == 422
    assert c.post('/portal/expediente/cv',headers=a,
           files={'archivo':('mucho.txt',b'x' * (8*1024*1024+1),'text/plain')}).status_code == 413
'''
    env = os.environ.copy()
    env['DATABASE_URL'] = f'sqlite:///{tmp_path / "portal_aislado.db"}'
    # Evita intentar usar credenciales externas o una BD real.
    env['GEMINI_API_KEY'] = ''
    env['ULTRAMSG_INSTANCE_ID'] = ''
    env['ULTRAMSG_TOKEN'] = ''
    proceso = subprocess.run([sys.executable, '-c', script], cwd=raiz, env=env,
                             capture_output=True, text=True, timeout=90)
    assert proceso.returncode == 0, f'{proceso.stdout}\n{proceso.stderr}'


def test_instalador_no_duplica_enganche(tmp_path):
    raiz = Path(__file__).resolve().parents[1]
    # El instalador no debe requerir secretos ni modificar app.py, main.py, database.py.
    texto = (raiz / 'instalar_expediente_candidato.py').read_text(encoding='utf-8')
    assert "raiz / 'servicios' / 'portal_auth.py'" in texto
    assert 'agregar_expediente(portal, motor, db_sesion, sesion_autorizada)' in texto
    assert 'shutil.copy2' in texto
    assert 'ast.parse' in texto


def test_cv_word_omite_sexo_y_domicilio_privado(monkeypatch):
    """El documento descargable no debe exponer campos opcionales sensibles."""
    import sys
    import types
    import zipfile
    from io import BytesIO

    # La función DOCX no necesita el servidor Streamlit activo.
    monkeypatch.setitem(sys.modules, 'streamlit', types.ModuleType('streamlit'))
    from servicios.portal_expediente_ui import _documento_cv
    datos = {
        'nombre': 'Persona Ficticia', 'correo': 'persona@example.com',
        'telefono': '5550009999', 'municipio': 'Chalco', 'estado': 'México',
        'sexo': 'Mujer', 'domicilio_general': 'Calle Privada 999',
        'habilidades': 'Excel', 'experiencia': 'Trabajo en administración'
    }
    contenido = _documento_cv(datos)
    with zipfile.ZipFile(BytesIO(contenido)) as z:
        xml = z.read('word/document.xml').decode('utf-8')
    assert 'Persona Ficticia' in xml and 'Excel' in xml
    assert 'Calle Privada' not in xml
    assert 'Mujer' not in xml

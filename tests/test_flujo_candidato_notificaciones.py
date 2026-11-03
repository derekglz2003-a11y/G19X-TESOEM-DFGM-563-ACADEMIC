"""E2E aislado: integra las rutas de main.py con las notificaciones del portal.

No accede a bases reales, Gemini, UltraMsg ni modelos remotos.
"""
import os
import subprocess
import sys
import textwrap
from pathlib import Path


def test_flujo_compartir_ranking_postulacion_entrevista_notificacion(tmp_path):
    raiz = Path(__file__).resolve().parents[1]
    codigo = textwrap.dedent('''
        import sys, types
        from fastapi.testclient import TestClient
        from sqlalchemy.orm import Session
        fake = types.ModuleType('embeddings')
        fake.calcular_similitud_semantica_lote = lambda texto, cvs: [round(.79 - n*.03, 2) for n in range(len(cvs))]
        sys.modules['embeddings'] = fake
        from database import Candidato, Evaluacion, SessionLocal
        from main import app
        admin = {'X-API-Key': __import__('os').environ['ADMIN_API_KEY']}
        cliente = TestClient(app)
        def cuenta(usuario, correo):
            assert cliente.post('/portal/registro', json={
                'usuario':usuario, 'nombre':usuario.title(), 'correo':correo,
                'contrasena':'clave-de-prueba-segura-12345'
            }).status_code == 201
            r=cliente.post('/portal/ingresar', json={'usuario':usuario,'contrasena':'clave-de-prueba-segura-12345'})
            assert r.status_code == 200, r.text
            return {'Authorization': 'Bearer ' + r.json()['token']}
        a=cuenta('alicia', 'alicia@ejemplo.test')
        b=cuenta('bruno', 'bruno@ejemplo.test')
        assert cliente.get('/portal/notificaciones',headers=b).json()==[]
        assert cliente.post('/portal/expediente/compartir',headers=a).status_code==422
        cv=b'Experiencia profesional en Excel, contabilidad, facturacion y conciliacion de cuentas de oficina. '
        r=cliente.post('/portal/expediente/cv',headers=a, files={'archivo':('cv.txt',cv,'text/plain')})
        assert r.status_code==200, r.text
        r=cliente.post('/portal/expediente/compartir',headers=a)
        assert r.status_code==200,r.text
        cid=r.json()['candidato_id']
        assert cliente.post('/portal/expediente/compartir',headers=a).json()['candidato_id']==cid
        with SessionLocal() as db:
            assert db.query(Candidato).count()==1
        assert cliente.get('/api/v1/candidatos',headers=admin).json()[0]['id']==cid
        assert next(x for x in cliente.get('/api/v1/portal-candidatos',headers=admin).json() if x['usuario']=='alicia')['expediente_administrativo_id']==cid
        v=cliente.post('/api/v1/vacantes',data={'titulo':'Auxiliar contable',
            'descripcion':'Registro de polizas y conciliacion bancaria con Excel y contabilidad'},headers=admin)
        assert v.status_code==200,v.text
        vid=v.json()['id']
        # Evalúa aun ANTES de postularse, por compartir CV expresamente.
        ranking=cliente.post(f'/api/v1/evaluar/{vid}',headers=admin)
        assert ranking.status_code==200,ranking.text
        assert ranking.json()['evaluados']==1
        assert cliente.get(f'/api/v1/ranking/{vid}',headers=admin).json()[0]['candidato_id']==cid
        assert cliente.put(f'/api/v1/publicaciones/{vid}',headers=admin,json={'publicada':True}).status_code==200
        assert cliente.post(f'/portal/vacantes/{vid}/postularse',headers=a).status_code==201
        assert cliente.post(f'/portal/vacantes/{vid}/postularse',headers=a).status_code==409
        notifs=cliente.get('/portal/notificaciones',headers=a).json()
        assert len(notifs)==1 and notifs[0]['tipo']=='postulacion'
        assert cliente.get('/portal/notificaciones',headers=b).json()==[]
        ent=cliente.post('/api/v1/entrevistas',headers=admin,json={
            'vacante_id':vid,'candidato_id':cid,'nombre':'Alicia','puesto':'Auxiliar contable',
            'fecha':'2026-12-05','hora':'09:30','lugar':'Google Meet'
        })
        assert ent.status_code==200,ent.text
        eid=ent.json()['id']
        citas=cliente.get('/portal/entrevistas',headers=a).json()
        assert len(citas)==1 and citas[0]['hora']=='09:30'
        assert cliente.get('/portal/entrevistas',headers=b).json()==[]
        assert 'Entrevista programada' in [n['titulo'] for n in cliente.get('/portal/notificaciones',headers=a).json()]
        assert cliente.put(f'/api/v1/entrevistas/{eid}',headers=admin,json={
            'puesto':'Auxiliar contable','fecha':'2026-12-06','hora':'10:15','lugar':'Sala virtual'}).status_code==200
        assert 'Tu entrevista fue actualizada' in [n['titulo'] for n in cliente.get('/portal/notificaciones',headers=a).json()]
        assert cliente.put(f'/api/v1/entrevistas/{eid}/decision',headers=admin,json={
            'estado':'Finalista', 'tipo_finalista':'En evaluacion'}).status_code==200
        assert cliente.get('/portal/postulaciones',headers=a).json()[0]['estado']=='Etapa final'
        assert cliente.put(f'/api/v1/entrevistas/{eid}/decision',headers=admin,json={
            'estado':'Aceptado','tipo_finalista':''}).status_code==200
        assert cliente.get('/portal/postulaciones',headers=a).json()[0]['estado']=='Seleccionado'
        avisos=cliente.get('/portal/notificaciones',headers=a).json()
        assert avisos[0]['titulo']=='¡Has sido seleccionado!'
        assert cliente.put(f'/portal/notificaciones/{avisos[0]["id"]}/leida',headers=b).status_code==404
        assert cliente.put(f'/portal/notificaciones/{avisos[0]["id"]}/leida',headers=a).status_code==200
        assert cliente.get('/portal/notificaciones',headers=a).json()[0]['leida'] is True
        # No se envía notificación a la cuenta no relacionada.
        assert cliente.get('/portal/postulaciones',headers=b).json()==[]
        assert cliente.get('/portal/notificaciones',headers=b).json()==[]
        print('FLUJO COMPLETO APROBADO')
    ''')
    env = os.environ.copy()
    env['DATABASE_URL'] = f'sqlite:///{tmp_path / "flujo_aislado.db"}'
    env['GEMINI_API_KEY'] = ''
    env['ULTRAMSG_TOKEN'] = ''
    env['ULTRAMSG_INSTANCE_ID'] = ''
    env['ADMIN_API_KEY'] = 'solo-prueba-segura-12345678901234567890'
    proceso = subprocess.run([sys.executable, '-c', codigo], cwd=raiz, env=env,
                             capture_output=True, text=True, timeout=120)
    assert proceso.returncode == 0, f'{proceso.stdout}\n{proceso.stderr}'
    assert 'FLUJO COMPLETO APROBADO' in proceso.stdout

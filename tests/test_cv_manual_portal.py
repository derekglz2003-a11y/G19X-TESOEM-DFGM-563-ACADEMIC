"""CV manual: guardado, privacidad, autorizacion de compartir y ranking sin archivos.

Ejecuta la app en un subprocess con SQLite temporal. Nunca toca la base real.
"""
import os
import subprocess
import sys
import textwrap
from pathlib import Path


def test_cv_manual_candidatos_sin_archivo_y_ranking_sin_datos_obsoletos(tmp_path):
    proyecto = Path(__file__).resolve().parents[1]
    script = textwrap.dedent('''
        import sys, types
        fake = types.ModuleType('embeddings')
        fake.calcular_similitud_semantica_lote = lambda a,b: [75.0 for _ in b]
        sys.modules['embeddings'] = fake
        from fastapi.testclient import TestClient
        from database import Candidato, Evaluacion, SessionLocal
        from main import app
        client = TestClient(app)
        admin = {'X-API-Key': __import__('os').environ['ADMIN_API_KEY']}
        def registrar(name):
            r = client.post('/portal/registro',json={
                'usuario':name, 'nombre':'Persona ' + name,
                'correo':name+'@example.test',
                'contrasena':'contrasena-de-pruebas-muy-segura'
            })
            assert r.status_code == 201, r.text
            r = client.post('/portal/ingresar',json={'usuario':name, 'contrasena':'contrasena-de-pruebas-muy-segura'})
            assert r.status_code == 200, r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        ana, bea = registrar('ana'), registrar('bea')
        data = {
            'nombre':'Ana de Prueba','telefono':'5550000000',
            'sexo':'Mujer', 'domicilio_general':'Calle Secreta 33',
            'nivel_estudios':'Licenciatura / Ingeniería','carrera':'Contabilidad',
            'experiencia':'Dos años conciliando cuentas y haciendo reportes',
            'habilidades':'Excel, facturación y contabilidad',
            'fortalezas':'Organización y atención al detalle',
            'puesto_deseado':'Auxiliar contable','zonas_preferidas':'CDMX',
            'modalidad':'Presencial','jornada':'Tiempo completo',
        }
        r = client.post('/portal/expediente/cv/manual',headers=ana,json={'perfil':data})
        assert r.status_code == 200, r.text
        assert r.json()['requiere_compartir'] is True
        texto = client.get('/portal/expediente/cv',headers=ana).json()['texto']
        assert 'Excel' in texto and 'Contabilidad' in texto
        assert 'Mujer' not in texto and 'Calle Secreta' not in texto
        assert client.get('/portal/expediente',headers=ana).json()['cv_cargado'] is True
        assert client.get('/portal/expediente',headers=bea).json()['cv_cargado'] is False
        assert client.get('/portal/expediente/cv',headers=bea).json()['texto']==''
        assert client.post('/portal/expediente/cv/manual',json={'perfil':data}).status_code==401
        assert client.post('/portal/expediente/cv/manual',headers=ana,json={'perfil':data}).status_code==409
        assert client.get('/api/v1/candidatos',headers=admin).json()==[]  # no comparte por defecto
        r=client.post('/portal/expediente/compartir',headers=ana)
        assert r.status_code==200,r.text
        cid=r.json()['candidato_id']
        v=client.post('/api/v1/vacantes',headers=admin,data={'titulo':'Auxiliar contable',
            'descripcion':'Contabilidad, Excel, conciliación y facturación'})
        assert v.status_code==200,v.text
        vid=v.json()['id']
        r=client.post(f'/api/v1/evaluar/{vid}',headers=admin)
        assert r.status_code==200,r.text
        assert r.json()['evaluados']==1
        # Editar CV manual no reutiliza evaluaciones obsoletas ni comparte los cambios sin permiso.
        data['habilidades']='Control de inventarios y atención a proveedores'
        r=client.post('/portal/expediente/cv/manual',headers=ana,
            json={'perfil':data,'reemplazar_cv':True})
        assert r.status_code==200,r.text
        with SessionLocal() as db:
            candidato=db.get(Candidato,cid)
            assert candidato is not None
            assert candidato.texto_completo=='' and candidato.skills==''
            assert db.query(Evaluacion).count()==0
        r=client.post(f'/api/v1/evaluar/{vid}',headers=admin)
        assert r.status_code==200,r.text
        assert r.json()['evaluados']==0
        r=client.post('/portal/expediente/compartir',headers=ana)
        assert r.status_code==200,r.text
        assert r.json()['candidato_id']==cid
        with SessionLocal() as db:
            assert db.query(Candidato).count()==1
            assert db.get(Candidato,cid).skills=='Control de inventarios y atención a proveedores'
        # Perfil laboral vacio no debe poder convertirse en CV artificialmente.
        malo={'nombre':'Persona Incompleta'}
        r=client.post('/portal/expediente/cv/manual',headers=bea,json={'perfil':malo})
        assert r.status_code==422,r.text
        # Un segundo usuario no puede editar el CV de Ana; solo el propio.
        assert client.get('/portal/expediente/cv',headers=bea).json()['texto']==''
        print('CV MANUAL APROBADO')
    ''')
    env=os.environ.copy()
    env.update({
        'DATABASE_URL':'sqlite:///'+str(tmp_path/'cv_manual.db'),
        'ADMIN_API_KEY':'clave-de-pruebas-segura-de-32-o-mas-caracteres',
        'GEMINI_API_KEY':'', 'ULTRAMSG_INSTANCE_ID':'', 'ULTRAMSG_TOKEN':''
    })
    r=subprocess.run([sys.executable,'-c',script],cwd=proyecto,env=env,
                     capture_output=True,text=True,timeout=120)
    assert r.returncode==0, f'{r.stdout}\n{r.stderr}'
    assert 'CV MANUAL APROBADO' in r.stdout

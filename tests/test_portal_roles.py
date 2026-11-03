"""Pruebas aisladas de acceso candidato; NO conectan con Supabase.

El subprocess fuerza SQLite temporal antes de importar database.py, para
no tocar el motor DB que el usuario haya configurado en su .env real.
"""
import os
from pathlib import Path
import subprocess
import sys


def test_portal_registro_sesion_y_aislamiento(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    prueba = r'''
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.testclient import TestClient
from servicios.portal_auth import montar_portal

def exige_clave(x_api_key: str | None = Header(None)):
    if x_api_key != 'clave-administrativa-inventada':
        raise HTTPException(status_code=401)

app = FastAPI(dependencies=[Depends(exige_clave)])
@app.get('/api/v1/candidatos')
def candidatos():
    return [{'privado':True}]

montar_portal(app)
with TestClient(app) as c:
    assert c.get('/api/v1/candidatos').status_code == 401
    datos = {'usuario':'elena.prueba','nombre':'Elena Ficticia','correo':'elena@example.com','contrasena':'ContraseñaPrueba123!'}
    r = c.post('/portal/registro',json=datos)
    assert r.status_code == 201, r.text
    assert c.post('/portal/registro',json=datos).status_code == 409
    assert c.get('/portal/yo').status_code == 401
    assert c.post('/portal/ingresar',json={'usuario':'elena.prueba','contrasena':'incorrecta'}).status_code == 401
    r = c.post('/portal/ingresar',json={'usuario':'elena.prueba','contrasena':'ContraseñaPrueba123!'})
    assert r.status_code == 200, r.text
    token = r.json()['token']
    cab = {'Authorization':'Bearer '+token}
    perfil = c.get('/portal/yo',headers=cab)
    assert perfil.status_code == 200
    assert perfil.json()['rol'] == 'candidato'
    assert 'contrasena_hash' not in perfil.text
    # Un token de candidato no da acceso a rutas administrativas.
    assert c.get('/api/v1/candidatos',headers=cab).status_code == 401
    assert c.post('/portal/salir',headers=cab).status_code == 200
    assert c.get('/portal/yo',headers=cab).status_code == 401
'''
    env = os.environ.copy()
    env['DATABASE_URL'] = f"sqlite:///{tmp_path / 'portal_prueba.db'}"
    env['ADMIN_API_KEY'] = 'x' * 40
    resultado = subprocess.run([sys.executable, '-c', prueba], cwd=project_root, env=env,
                               capture_output=True, text=True, timeout=40)
    assert resultado.returncode == 0, f"{resultado.stdout}\n{resultado.stderr}"

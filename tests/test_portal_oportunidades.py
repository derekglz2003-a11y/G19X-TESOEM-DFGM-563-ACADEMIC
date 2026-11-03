"""Pruebas de integración del portal: usar exclusivamente SQLite temporal."""
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


# IMPORTANTE: no importar database ni el portal durante la colección de pytest.
# tests/test_api.py establece DATABASE_URL temporal al iniciar su fixture.

@pytest.fixture
def sistema():
    from database import Base, Vacante
    from servicios.portal_auth import montar_portal
    from servicios.portal_oportunidades import registrar_admin_oportunidades

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    app = FastAPI()

    def exigir_admin(x_api_key: str = Header(default="")):
        if x_api_key != "test-admin-secret":
            raise HTTPException(401, "No autorizado")

    registrar_admin_oportunidades(app, exigir_admin, motor=engine)
    montar_portal(app, engine)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Vacante(titulo="Auxiliar contable", descripcion="Revisar documentos, manejar Excel y apoyar la contabilidad de la empresa."))
        db.commit()
    with TestClient(app) as cliente:
        yield cliente, engine
    engine.dispose()


def _registro_y_token(cliente, nombre="Ana López", usuario="anal", correo="ana.test@example.com"):
    r = cliente.post('/portal/registro', json={
        "usuario": usuario, "nombre": nombre, "correo": correo,
        "contrasena": "contraseña-segura-12345",
    })
    assert r.status_code == 201, r.text
    r = cliente.post('/portal/ingresar', json={"usuario": usuario, "contrasena": "contraseña-segura-12345"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_al_registrarse_es_visible_al_admin_sin_crear_cv(sistema):
    cliente, engine = sistema
    _registro_y_token(cliente)
    assert cliente.get('/api/v1/portal-candidatos').status_code == 401
    r = cliente.get('/api/v1/portal-candidatos', headers={"X-API-Key": "test-admin-secret"})
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1
    assert r.json()[0]['expediente_administrativo_id'] is None
    from database import Candidato
    with Session(engine) as db:
        assert db.query(Candidato).count() == 0  # Sin consentimiento no entra al pool.


def test_publicar_y_postularse_una_vez_con_cv(sistema):
    cliente, engine = sistema
    token = _registro_y_token(cliente)
    admin = {"X-API-Key": "test-admin-secret"}
    assert cliente.get('/portal/vacantes', headers=token).json() == []
    assert cliente.put('/api/v1/publicaciones/1', json={"publicada": True}).status_code == 401
    r = cliente.put('/api/v1/publicaciones/1', json={"publicada": True}, headers=admin)
    assert r.status_code == 200, r.text
    assert len(cliente.get('/portal/vacantes', headers=token).json()) == 1
    assert cliente.post('/portal/vacantes/1/postularse', headers=token).status_code == 422

    with Session(engine) as db:
        from servicios.portal_expediente import ExpedienteCandidato
        exp = ExpedienteCandidato(usuario_id=1, cv_nombre='cv.txt',
            cv_texto='Tengo experiencia en contabilidad y manejo Excel, facturación y conciliación.',
            habilidades='Excel, contabilidad, facturación', experiencia='Dos años de contabilidad')
        db.add(exp)
        db.commit()
    r = cliente.post('/portal/vacantes/1/postularse', headers=token)
    assert r.status_code == 201, r.text
    assert cliente.post('/portal/vacantes/1/postularse', headers=token).status_code == 409
    from database import Candidato
    with Session(engine) as db:
        assert db.query(Candidato).count() == 1
        c = db.query(Candidato).one()
        assert c.edad == 'No especificada' and c.sexo == 'No especificado'
        assert 'Excel' in c.skills
    assert len(cliente.get('/portal/postulaciones', headers=token).json()) == 1

    # El administrador puede actualizar etapa; el candidato ve solo su resultado.
    p = cliente.get('/api/v1/postulaciones-admin', headers=admin).json()[0]
    assert p['nombre'] == 'Ana López'
    r = cliente.put(f"/api/v1/postulaciones-admin/{p['id']}/estado",
                    json={"estado": "Preseleccionado"}, headers=admin)
    assert r.status_code == 200, r.text
    assert cliente.get('/portal/postulaciones', headers=token).json()[0]['estado'] == 'En revisión'

    # Otra cuenta nunca puede consultar ni modificar la primera.
    otro = _registro_y_token(cliente, nombre='Luis Pérez', usuario='luis', correo='luis@example.com')
    assert cliente.get('/portal/postulaciones', headers=otro).json() == []
    assert cliente.post(f"/portal/postulaciones/{p['id']}/retirar", headers=otro).status_code == 404
    assert cliente.post(f"/portal/postulaciones/{p['id']}/retirar", headers=token).status_code == 200
    assert cliente.get('/portal/postulaciones', headers=token).json()[0]['estado'] == 'Retirada'

    # No eliminar a ciegas vacantes o expedientes relacionados: el main añade guardas.
    assert cliente.put('/api/v1/publicaciones/1', json={"publicada": False}, headers=admin).status_code == 200
    assert cliente.get('/portal/vacantes', headers=token).json() == []
    assert len(cliente.get('/portal/postulaciones', headers=token).json()) == 1


def test_compartir_cv_sin_postularse_una_sola_vez_y_recalcular(sistema):
    cliente, engine = sistema
    token = _registro_y_token(cliente, usuario='marisol', correo='marisol@example.com')
    admin = {'X-API-Key': 'test-admin-secret'}
    # La cuenta sin consentimiento no aparece en el pool.
    assert cliente.post('/portal/expediente/compartir', headers=token).status_code == 422
    from servicios.portal_expediente import ExpedienteCandidato
    from database import Candidato, Evaluacion
    with Session(engine) as db:
        db.add(ExpedienteCandidato(usuario_id=1, cv_nombre='cv_marisol.txt',
            cv_texto='Experiencia en administración documental y en atención de clientes con Excel.',
            habilidades='Excel, CRM', experiencia='Administración de oficina'))
        db.commit()
    compartido = cliente.post('/portal/expediente/compartir', headers=token)
    assert compartido.status_code == 200, compartido.text
    cid = compartido.json()['candidato_id']
    assert cliente.get('/portal/expediente/compartido', headers=token).json()['compartido'] is True
    admin_lista = cliente.get('/api/v1/portal-candidatos', headers=admin).json()
    assert admin_lista[0]['expediente_administrativo_id'] == cid
    with Session(engine) as db:
        assert db.query(Candidato).count() == 1
        candidato = db.get(Candidato, cid)
        assert candidato.nombre_archivo == 'cv_marisol.txt'
        assert candidato.sexo == 'No especificado' and candidato.edad == 'No especificada'
        db.add(Evaluacion(vacante_id=1, candidato_id=cid, score_similitud=0.7))
        db.commit()
    actualizado = cliente.post('/portal/expediente/compartir', headers=token)
    assert actualizado.status_code == 200, actualizado.text
    assert actualizado.json()['candidato_id'] == cid
    with Session(engine) as db:
        assert db.query(Candidato).count() == 1
        assert db.query(Evaluacion).filter_by(candidato_id=cid).count() == 0


def test_notificaciones_y_entrevistas_solo_propietario(sistema):
    cliente, engine = sistema
    a = _registro_y_token(cliente, usuario='personaa', correo='a@example.com')
    b = _registro_y_token(cliente, usuario='personab', correo='b@example.com', nombre='Persona B')
    admin = {'X-API-Key': 'test-admin-secret'}
    from servicios.portal_expediente import ExpedienteCandidato
    from database import Entrevista, EntrevistaVacante
    with Session(engine) as db:
        db.add(ExpedienteCandidato(usuario_id=1, cv_nombre='cv_a.txt',
            cv_texto='Trabajo ficticio con Excel y contabilidad para auxiliar administrativo.',
            habilidades='Excel, contabilidad'))
        db.commit()
    assert cliente.put('/api/v1/publicaciones/1', json={'publicada': True}, headers=admin).status_code == 200
    assert cliente.post('/portal/vacantes/1/postularse', headers=a).status_code == 201
    post = cliente.get('/api/v1/postulaciones-admin', headers=admin).json()[0]
    notifs = cliente.get('/portal/notificaciones', headers=a).json()
    assert len(notifs) == 1 and notifs[0]['titulo'] == 'Postulación recibida'
    assert cliente.get('/portal/notificaciones', headers=b).json() == []
    assert cliente.put(f"/portal/notificaciones/{notifs[0]['id']}/leida", headers=b).status_code == 404
    assert cliente.put(f"/portal/notificaciones/{notifs[0]['id']}/leida", headers=a).status_code == 200
    assert cliente.get('/portal/notificaciones', headers=a).json()[0]['leida'] is True
    assert cliente.put(f"/api/v1/postulaciones-admin/{post['id']}/estado",
                       json={'estado':'Aceptado'}, headers=admin).status_code == 200
    avisos = cliente.get('/portal/notificaciones', headers=a).json()
    assert len(avisos) == 2 and avisos[0]['titulo'] == '¡Has sido seleccionado!'
    assert cliente.get('/portal/postulaciones', headers=a).json()[0]['estado'] == 'Seleccionado'
    assert cliente.get('/portal/postulaciones', headers=b).json() == []
    with Session(engine) as db:
        e = Entrevista(candidato_id=post['candidato_id'], nombre='Persona A',
                       puesto='Auxiliar contable', fecha='2026-12-18', hora='11:00', lugar='Video llamada')
        db.add(e)
        db.flush()
        db.add(EntrevistaVacante(entrevista_id=e.id, vacante_id=1))
        db.commit()
    mis_entrevistas = cliente.get('/portal/entrevistas', headers=a).json()
    assert len(mis_entrevistas) == 1
    assert mis_entrevistas[0]['fecha'] == '2026-12-18'
    assert cliente.get('/portal/entrevistas', headers=b).json() == []


def test_retirar_cv_elimina_texto_compartido_y_puntajes(sistema):
    cliente, engine = sistema
    token = _registro_y_token(cliente, usuario='rocio', correo='rocio@example.com')
    from servicios.portal_expediente import ExpedienteCandidato
    from database import Candidato, Evaluacion
    with Session(engine) as db:
        db.add(ExpedienteCandidato(usuario_id=1, cv_nombre='rocio.txt',
            cv_texto='Experiencia ficticia como auxiliar contable con Excel, conciliación y facturación.',
            habilidades='Excel'))
        db.commit()
    r = cliente.post('/portal/expediente/compartir', headers=token)
    assert r.status_code == 200, r.text
    cid = r.json()['candidato_id']
    with Session(engine) as db:
        db.add(Evaluacion(vacante_id=1, candidato_id=cid, score_similitud=.8))
        db.commit()
    eliminado = cliente.delete('/portal/expediente/cv', headers=token)
    assert eliminado.status_code == 200, eliminado.text
    assert cliente.get('/portal/expediente/compartido', headers=token).json()['compartido'] is False
    with Session(engine) as db:
        c = db.get(Candidato, cid)
        assert c is not None  # Se conserva el ID de la vinculación.
        assert c.texto_completo == '' and c.skills == ''
        assert db.query(Evaluacion).filter_by(candidato_id=cid).count() == 0


def test_invitacion_a_cv_compartido_sin_postulacion(sistema):
    cliente, engine = sistema
    token = _registro_y_token(cliente, usuario='lucia', correo='lucia@example.com')
    admin = {'X-API-Key': 'test-admin-secret'}
    from servicios.portal_expediente import ExpedienteCandidato
    with Session(engine) as db:
        db.add(ExpedienteCandidato(usuario_id=1, cv_nombre='cv.txt',
            cv_texto='Experiencia en Excel, auxiliar contable, archivos, facturas y administración.',
            habilidades='Excel'))
        db.commit()
    r=cliente.post('/portal/expediente/compartir', headers=token)
    assert r.status_code==200, r.text
    cid=r.json()['candidato_id']
    ruta=f'/api/v1/invitaciones/1/{cid}'
    assert cliente.post(ruta).status_code == 401
    assert cliente.post(ruta, headers=admin).status_code == 409  # Aún no publicada.
    assert cliente.put('/api/v1/publicaciones/1', json={'publicada':True}, headers=admin).status_code == 200
    assert cliente.post(ruta, headers=admin).status_code == 200
    assert cliente.post(ruta, headers=admin).status_code == 409  # Evita invitaciones repetidas sin leer.
    avisos=cliente.get('/portal/notificaciones', headers=token).json()
    assert len(avisos)==1 and avisos[0]['tipo']=='invitacion'
    assert 'postúlate' in avisos[0]['mensaje']
    assert cliente.post('/portal/vacantes/1/postularse',headers=token).status_code == 201
    assert cliente.post(ruta, headers=admin).status_code == 409

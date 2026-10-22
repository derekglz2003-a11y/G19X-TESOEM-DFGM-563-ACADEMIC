"""Pruebas funcionales aisladas: nunca usan la base de datos del usuario.

Ejecutar: python -m pytest -q tests/test_api.py
"""
import os
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="module")
def sistema(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("datos_prueba") / "curriculai_test.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["GEMINI_API_KEY"] = ""
    os.environ["ADMIN_API_KEY"] = "prueba-local-de-acceso-123456789012345678901234567890"

    # Simula solamente la función de vectores: no certifica la calidad del modelo ML.
    fake_embeddings = types.ModuleType("embeddings")
    fake_embeddings.calcular_similitud_semantica_lote = lambda texto, cvs: [round(75 - i * 8, 1) for i in range(len(cvs))]
    previous = sys.modules.get("embeddings")
    sys.modules["embeddings"] = fake_embeddings
    import database
    import main

    client = TestClient(main.app)
    client.headers.update({"X-API-Key": os.environ["ADMIN_API_KEY"]})
    try:
        yield client, database
    finally:
        client.close()
        if previous is None:
            sys.modules.pop("embeddings", None)
        else:
            sys.modules["embeddings"] = previous


def test_api_operaciones_principales_y_mensajes(sistema):
    client, dbm = sistema
    with dbm.SessionLocal() as db:
        for i in range(2):
            db.add(dbm.Candidato(
                nombre=f"Persona prueba {i+1}", email=f"test{i}@example.test",
                telefono=f"551234000{i}", perfil_destacado="Administración",
                skills="Excel, atención a clientes",
                experiencia="Administración de oficinas y facturación",
                texto_completo="Administración, facturación, Excel, atención a clientes; experiencia comprobable." * 2,
            ))
        db.commit()

    candidatos = client.get("/api/v1/candidatos").json()
    assert len(candidatos) == 2
    c1, c2 = (candidatos[0]["id"], candidatos[1]["id"])

    crear = client.post("/api/v1/vacantes", data={"titulo": "Analista administrativo", "descripcion": "Excel, facturación y atención a clientes"})
    assert crear.status_code == 200, crear.text
    vid = crear.json()["id"]

    modificar = client.put(f"/api/v1/vacantes/{vid}", json={"titulo": "Analista de operaciones", "descripcion": "Excel y facturación"})
    assert modificar.status_code == 200
    assert modificar.json()["titulo"] == "Analista de operaciones"

    ranking = client.post(f"/api/v1/evaluar/{vid}")
    assert ranking.status_code == 200, ranking.text
    assert ranking.json()["evaluados"] == 2
    assert len(client.get(f"/api/v1/ranking/{vid}").json()) == 2

    seguim = client.put(f"/api/v1/seguimientos/{vid}/{c1}", json={"estado": "Preseleccionado"})
    assert seguim.status_code == 200
    assert client.put(f"/api/v1/seguimientos/{vid}/{c2}", json={"estado": "Descartado"}).status_code == 200
    assert len(client.get(f"/api/v1/seguimientos?vacante_id={vid}").json()) == 2

    programar = client.post("/api/v1/entrevistas", json={
        "candidato_id": c1, "nombre": "Persona prueba 1", "vacante_id": vid,
        "puesto": "Analista de operaciones", "fecha": "2026-12-01", "hora": "10:30", "lugar": "Google Meet",
    })
    assert programar.status_code == 200, programar.text
    eid = programar.json()["id"]
    detalle = client.get("/api/v1/entrevistas").json()
    assert len(detalle) == 1
    assert detalle[0]["vacante_id"] == vid

    mensaje = client.post("/api/v1/mensajes-whatsapp", json={
        "candidato_id": c1, "entrevista_id": eid,
        "telefono": "525512340000", "mensaje": "Confirmación de prueba",
        "estado": "Enviado", "proveedor": "UltraMsg", "detalle": "Aceptado para envío",
    })
    assert mensaje.status_code == 200, mensaje.text
    assert client.get("/api/v1/mensajes-whatsapp").json()[0]["entrevista_id"] == eid

    editar = client.put(f"/api/v1/entrevistas/{eid}", json={
        "puesto": "Analista de operaciones", "fecha": "2026-12-02", "hora": "12:00", "lugar": "Sala A",
    })
    assert editar.status_code == 200

    decision = client.put(f"/api/v1/entrevistas/{eid}/decision", json={"estado": "Finalista", "tipo_finalista": "En evaluación"})
    assert decision.status_code == 200
    assert any(s["estado"] == "Finalista" for s in client.get(f"/api/v1/seguimientos?vacante_id={vid}").json())

    aceptado = client.put(f"/api/v1/entrevistas/{eid}/decision", json={"estado": "Aceptado", "tipo_finalista": "En evaluación"})
    assert aceptado.status_code == 200
    assert client.get("/api/v1/entrevistas").json()[0]["estado"] == "Aceptado"

    rechazar = client.put(f"/api/v1/entrevistas/{eid}/decision", json={"estado": "Rechazado", "tipo_finalista": ""})
    assert rechazar.status_code == 200

    quitar = client.delete(f"/api/v1/entrevistas/{eid}")
    assert quitar.status_code == 200
    assert client.get("/api/v1/entrevistas").json() == []
    assert client.get("/api/v1/mensajes-whatsapp").json()[0]["entrevista_id"] is None

    eliminar_cv = client.delete(f"/api/v1/candidatos/{c1}/cv")
    assert eliminar_cv.status_code == 200

    eliminar_vac = client.delete(f"/api/v1/vacantes/{vid}")
    assert eliminar_vac.status_code == 200

    limpiar = client.delete("/api/v1/limpiar-pool")
    assert limpiar.status_code == 200, limpiar.text
    assert client.get("/api/v1/candidatos").json() == []
    # La bitácora se conserva pero no su vinculación personal.
    assert client.get("/api/v1/mensajes-whatsapp").json()[0]["candidato_id"] is None


def test_generador_sin_clave_da_error_util(sistema):
    client, _ = sistema
    r = client.post("/api/v1/generar-descripcion", json={"titulo": "Analista", "contexto": "Excel"})
    assert r.status_code == 503
    assert "GEMINI_API_KEY" in r.json()["detail"]


def test_importacion_txt_con_evidencias_no_inventadas(sistema):
    client, _ = sistema
    archivo = (
        b"Nombre: Mariana Prueba\nCorreo: mariana@example.test\n"
        b"Experiencia laboral en facturacion, uso de Excel, SQL y atencion a clientes "
        b"en proyectos administrativos. Contacto: 5512345689.\n"
    )
    resp = client.post("/api/v1/analizar-cvs-masivo", files=[("files", ("mariana_prueba.txt", archivo, "text/plain"))])
    assert resp.status_code == 200, resp.text
    assert "1 candidato" in resp.json().get("mensaje", "")
    registros = client.get("/api/v1/candidatos").json()
    assert len(registros) == 1
    candidato = registros[0]
    assert "Excel" in candidato["skills"] or "Sql" in candidato["skills"]
    assert "Compromiso, Responsabilidad, Adaptabilidad" not in candidato["skills"]
    assert candidato["desempeno"] == "Pendiente de evaluación"
    assert client.delete("/api/v1/limpiar-pool").status_code == 200


def test_cv_vacio_no_genera_perfil(sistema):
    client, _ = sistema
    resp = client.post("/api/v1/analizar-cvs-masivo", files=[("files", ("vacio.txt", b"CV", "text/plain"))])
    assert resp.status_code == 200
    assert "vacio.txt" in resp.json().get("mensaje", "")
    assert client.get("/api/v1/candidatos").json() == []


def test_seguridad_impide_lecturas_y_eliminaciones_sin_clave(sistema):
    client, _ = sistema
    # Una lectura sin credenciales no puede exponer datos personales.
    sin_acceso = client.get("/api/v1/candidatos", headers={"X-API-Key": ""})
    assert sin_acceso.status_code == 401
    assert "nombre" not in sin_acceso.text.lower()
    # Tampoco basta usar DELETE sobre una ruta destructiva.
    sin_permiso = client.delete("/api/v1/limpiar-pool", headers={"X-API-Key": "invalida"})
    assert sin_permiso.status_code == 401
    assert client.get("/api/v1/candidatos").status_code == 200


def test_api_sin_secreto_configurado_se_cierra(sistema, monkeypatch):
    client, _ = sistema
    with monkeypatch.context() as m:
        m.setenv("ADMIN_API_KEY", "")
        assert client.get("/api/v1/candidatos").status_code == 503
    assert client.get("/api/v1/candidatos").status_code == 200


def test_hash_de_administrador_con_salt(monkeypatch):
    import hashlib
    from servicios.seguridad import acceso_configurado, verificar_contrasena
    sal = bytes.fromhex("06" * 16)
    contraseña = "Una-Frase-Muy-Larga-Para-Pruebas"
    digest = hashlib.pbkdf2_hmac("sha256", contraseña.encode(), sal, 200_000)
    registro = f"pbkdf2_sha256$200000${sal.hex()}${digest.hex()}"
    with monkeypatch.context() as m:
        m.setenv("ADMIN_PASSWORD_HASH", registro)
        m.setenv("ADMIN_API_KEY", "q" * 45)
        assert acceso_configurado()
        assert verificar_contrasena(contraseña)
        assert not verificar_contrasena("contraseña-incorrecta")
    assert not verificar_contrasena("contraseña-incorrecta")


def test_generador_de_env_preserva_configuracion_existente():
    from scripts.configurar_acceso import guardar_variables
    original = "DATABASE_URL=postgresql://localhost/ejemplo\nGEMINI_API_KEY=\nADMIN_API_KEY=antigua\n"
    nuevo = guardar_variables(original, {"ADMIN_API_KEY": "NuevaClave", "ADMIN_PASSWORD_HASH": "HashNuevo"})
    assert "DATABASE_URL=postgresql://localhost/ejemplo" in nuevo
    assert "GEMINI_API_KEY=" in nuevo
    assert "ADMIN_API_KEY=NuevaClave" in nuevo
    assert "ADMIN_API_KEY=antigua" not in nuevo
    assert nuevo.count("ADMIN_PASSWORD_HASH=") == 1

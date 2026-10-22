"""Pruebas locales del generador de vacantes. No llaman a Google ni a Supabase."""
from types import SimpleNamespace
import pytest

from servicios import gemini_ia


class TiposSimulados:
    class GenerateContentConfig:
        def __init__(self, **kwargs):
            self.valores = kwargs

    class Part:
        @staticmethod
        def from_text(text):
            return {"texto": text}

        @staticmethod
        def from_bytes(data, mime_type):
            return {"tamano": len(data), "tipo": mime_type}


class ClienteSimulado:
    def __init__(self, respuesta="", error=None):
        self.respuesta = respuesta
        self.error = error
        self.peticiones = []
        self.models = self

    def generate_content(self, **kwargs):
        self.peticiones.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.respuesta)


def test_requisitos_laborales_se_conservan_sin_edad_sexo_apariencia():
    texto = (
        "debe de tener 3 años de experiencia, buena presencia, minimo tener la prepa, "
        "que sea mujer entre 20 a 30 años y si es hombre de 22 a 40"
    )
    limpio, omitidos = gemini_ia.limpiar_requisitos_de_vacante(texto)
    assert omitidos is True
    assert "3 años" in limpio and "prepa" in limpio
    for personal in ("presencia", "mujer", "hombre", "20 a 30", "22 a 40"):
        assert personal not in limpio.lower()


def test_generar_descripcion_con_gemini_actual_inserta_texto_y_marca_omisiones(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    cliente = ClienteSimulado("OBJETIVO DEL PUESTO\nApoyar el área administrativa.\nREQUISITOS\nPreparatoria y 3 años de experiencia.")
    monkeypatch.setattr(gemini_ia, "_cliente_y_tipos", lambda: (cliente, TiposSimulados))
    resultado = gemini_ia.generar_descripcion_puesto(
        "Auxiliar", "3 años de experiencia, mínimo prepa, mujer de 20 a 30 años, buena presencia"
    )
    assert resultado["criterios_omitidos"] is True
    assert "OBJETIVO DEL PUESTO" in resultado["descripcion"]
    req = cliente.peticiones[0]
    assert req["model"] == "gemini-3.8-flash"
    assert "3 años de experiencia" in req["contents"]
    assert "mínimo prepa" in req["contents"]
    assert "mujer" not in req["contents"]
    assert "presencia" not in req["contents"]


def test_gemini_no_publica_texto_discriminatorio(monkeypatch):
    cliente = ClienteSimulado("Solo mujeres de 20 a 30 años para el puesto.")
    monkeypatch.setattr(gemini_ia, "_cliente_y_tipos", lambda: (cliente, TiposSimulados))
    with pytest.raises(gemini_ia.ErrorGemini, match="criterios personales"):
        gemini_ia.generar_descripcion_puesto("Puesto de prueba", "3 años de experiencia")


def test_error_modelo_retirado_se_explica_sin_filtrar_secreto(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "clave-secreta-no-mostrar")
    cliente = ClienteSimulado(error=RuntimeError("404 models/gemini-2.0-flash no longer available"))
    monkeypatch.setattr(gemini_ia, "_cliente_y_tipos", lambda: (cliente, TiposSimulados))
    with pytest.raises(gemini_ia.ErrorGemini) as err:
        gemini_ia.generar_descripcion_puesto("Auxiliar")
    assert err.value.status_code == 503
    assert "GEMINI_MODEL" in str(err.value)
    assert "clave-secreta-no-mostrar" not in str(err.value)


def test_extraccion_de_cv_con_sdk_actual_devuelve_json(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    cliente = ClienteSimulado('{"nombre":"Candidato de prueba","email":"No contiene correo"}')
    monkeypatch.setattr(gemini_ia, "_cliente_y_tipos", lambda: (cliente, TiposSimulados))
    datos = gemini_ia.extraer_datos_cv_gemini(b"%PDF", "Texto", "perfil.pdf")
    assert datos["nombre"] == "Candidato de prueba"
    assert cliente.peticiones[0]["contents"][0] == {"tamano": 4, "tipo": "application/pdf"}
    assert cliente.peticiones[0]["config"].valores["response_mime_type"] == "application/json"

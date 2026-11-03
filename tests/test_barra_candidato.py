"""Pruebas aisladas de navegación; no requieren API, cuenta ni SQLite."""
from pathlib import Path

import pytest

from servicios import barra_candidato


class CambioDeVista(Exception):
    pass


class _Contexto:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _StreamlitFicticio:
    def __init__(self, click=None, state=None):
        self.session_state = state if state is not None else {}
        self.click = click
        self.botones = []
        self.html = []

    def markdown(self, texto, **_):
        self.html.append(texto)

    def container(self, **_):
        return _Contexto()

    def columns(self, ratios, **_):
        return [_Contexto() for _ in ratios]

    def button(self, etiqueta, key=None, **_):
        self.botones.append((etiqueta, key))
        return key == self.click

    def rerun(self):
        raise CambioDeVista()

    def stop(self):
        raise CambioDeVista()


def test_menu_completo_y_seleccion_actual(monkeypatch):
    fake = _StreamlitFicticio(state={'cai_candidato_seccion': 'Mis entrevistas'})
    monkeypatch.setattr(barra_candidato, 'st', fake)
    pagina = barra_candidato.mostrar_barra_candidato('Candidato ficticio', 3, lambda: None)
    assert pagina == 'Mis entrevistas'
    assert len(fake.botones) == 8  # siete opciones + cerrar sesión
    assert any(nombre == 'Avisos (3)' for nombre, _ in fake.botones)
    assert any(nombre == 'Cerrar sesión' for nombre, _ in fake.botones)
    assert any('cai-candidate-brand-title' in html for html in fake.html)


def test_cambio_de_seccion_al_pulsar_nav(monkeypatch):
    fake = _StreamlitFicticio(click='cai_candidato_nav_ir_2')
    monkeypatch.setattr(barra_candidato, 'st', fake)
    with pytest.raises(CambioDeVista):
        barra_candidato.mostrar_barra_candidato('Candidato ficticio', 0, lambda: None)
    assert fake.session_state['cai_candidato_seccion'] == 'Mi CV'


def test_cerrar_sesion_limpia_navegacion(monkeypatch):
    fake = _StreamlitFicticio(
        click='cai_candidato_cerrar_sesion',
        state={'cai_candidato_seccion': 'Notificaciones'},
    )
    monkeypatch.setattr(barra_candidato, 'st', fake)
    salidas = []
    with pytest.raises(CambioDeVista):
        barra_candidato.mostrar_barra_candidato('Candidato ficticio', 1, lambda: salidas.append(True))
    assert salidas == [True]
    assert 'cai_candidato_seccion' not in fake.session_state


def test_estilos_y_pantallas_limitados_al_candidato():
    css = barra_candidato.CSS_BARRA_CANDIDATO
    assert 'position: fixed !important' in css
    assert 'st-key-cai_candidate_topbar' in css
    assert 'st-key-cai_topbar' not in css  # no toca el menú admin
    vista = (Path(__file__).resolve().parents[1] / 'servicios' / 'portal_expediente_ui.py').read_text(encoding='utf-8')
    assert 'with tabs[' not in vista
    assert 'Bienvenido, {nombre_candidato}, a CurriculAi' in vista
    for seccion in barra_candidato.SECCIONES:
        assert f"if seccion == {seccion!r}:" in vista

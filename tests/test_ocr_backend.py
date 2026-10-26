"""Pruebas locales del OCR, sin Supabase y sin datos reales."""

import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from servicios import extractores_cv as ext


def test_tesseract_variable_explicita(tmp_path, monkeypatch):
    ejecutable = tmp_path / "tesseract.exe"
    ejecutable.write_bytes(b"binario de prueba")
    monkeypatch.setenv("TESSERACT_CMD", str(ejecutable))
    assert ext.localizar_tesseract() == str(ejecutable)


def test_tesseract_variable_incorrecta_da_mensaje(monkeypatch):
    monkeypatch.setenv("TESSERACT_CMD", "/ruta/que/no/existe/tesseract.exe")
    with pytest.raises(ValueError, match="TESSERACT_CMD"):
        ext.localizar_tesseract()


def test_tesseract_sin_path_busca_program_files(tmp_path, monkeypatch):
    carpeta = tmp_path / "Program Files" / "Tesseract-OCR"
    carpeta.mkdir(parents=True)
    ejecutable = carpeta / "tesseract.exe"
    ejecutable.write_bytes(b"binario de prueba")
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "Program Files"))
    monkeypatch.setattr(ext.shutil, "which", lambda _: None)
    assert ext.localizar_tesseract() == str(ejecutable)


def test_imagen_invalida_informa_error():
    with pytest.raises(ValueError, match="No se pudo procesar la imagen"):
        ext.extraer_texto_multiformato("falso.png", b"no es png")


def test_txt_no_necesita_ocr(monkeypatch):
    monkeypatch.setenv("TESSERACT_CMD", "/no/existe")
    texto = ext.extraer_texto_multiformato(
        "prueba.txt", "Perfil profesional: Excel, experiencia y organización".encode()
    )
    assert "Excel" in texto


def test_png_valido_con_ocr_simulado(monkeypatch):
    from PIL import Image
    imagen = Image.new("RGB", (40, 50), "white")
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    monkeypatch.setattr(ext, "_texto_por_ocr", lambda _: "Elena: 3 años de experiencia, CRM y Excel")
    assert "Elena" in ext.extraer_texto_multiformato("cv.png", buffer.getvalue())

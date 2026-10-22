"""Extracción controlada de texto de PDF, DOCX, TXT e imágenes.

Importar este módulo no conecta a ninguna base de datos ni requiere secretos.
El formato .doc legado no se admite: convertirlo antes a .docx/PDF.
"""
import io
import re

def limpiar_texto_para_db(texto: str) -> str:
    """Filtro de Limpieza Extrema para evitar que Supabase/PostgreSQL colapse."""
    if not texto: return ""
    # 1. Eliminar Null Bytes (\x00) que rompen los INSERTS en PostgreSQL
    t = texto.replace('\x00', ' ')
    # 2. Eliminar bloques de código binario de PDF (ej. << /Type /Catalog >>)
    t = re.sub(r'<<.*?>>', '', t, flags=re.DOTALL)
    # 3. Eliminar rutas internas de PDF
    t = re.sub(r'/[A-Za-z0-9_]+', ' ', t)
    # 4. Limitar espacios y saltos de línea
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

def extraer_texto_multiformato(filename: str, file_bytes: bytes) -> str:
    """Extrae texto; no fabrica perfiles cuando la lectura falla."""
    ext = filename.rsplit(".", 1)[-1].lower()
    texto = ""
    if ext == "pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            texto = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            pass
        if not texto.strip():
            try:
                import fitz
                with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                    texto = "\n".join(page.get_text() for page in doc)
            except Exception:
                pass
        # Para PDF escaneados sin texto seleccionable, OCR de las tres primeras
        # páginas como máximo, con límite de resolución para evitar saturación.
        if len(texto.strip()) < 35:
            try:
                import fitz
                from PIL import Image
                import pytesseract
                with fitz.open(stream=file_bytes, filetype="pdf") as documento:
                    fragmentos_ocr = []
                    for numero in range(min(len(documento), 3)):
                        pix = documento[numero].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                        imagen = Image.open(io.BytesIO(pix.tobytes("png")))
                        fragmentos_ocr.append(pytesseract.image_to_string(imagen))
                    texto = "\n".join(fragmentos_ocr)
            except Exception:
                pass  # El endpoint informará que no hay texto legible.
    elif ext == "docx":
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        partes = [p.text for p in doc.paragraphs if p.text.strip()]
        for tabla in doc.tables:
            for fila in tabla.rows:
                partes.append(" | ".join(celda.text for celda in fila.cells if celda.text.strip()))
        texto = "\n".join(partes)
    elif ext == "doc":
        raise ValueError("El formato .doc antiguo no está soportado. Guarda el CV como .docx o PDF.")
    elif ext == "txt":
        texto = file_bytes.decode("utf-8-sig", errors="replace")
    elif ext in ("png", "jpg", "jpeg", "webp"):
        try:
            from PIL import Image
            import pytesseract
            imagen = Image.open(io.BytesIO(file_bytes))
            texto = pytesseract.image_to_string(imagen)
        except Exception as exc:
            raise ValueError("No se pudo leer la imagen; verifica Tesseract OCR o utiliza PDF con texto") from exc
    else:
        raise ValueError("Formato de CV no admitido")
    return limpiar_texto_para_db(texto)[:15000]
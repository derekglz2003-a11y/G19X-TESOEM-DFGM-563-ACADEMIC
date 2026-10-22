# parser.py
import fitz
import re
import unicodedata

SKILLS_UNIVERSALES = [
    # Logística y Transporte
    "chofer", "licencia tipo a", "licencia tipo b", "licencia tipo c", "licencia federal", 
    "3.5 toneladas", "trailer", "rabon", "gps", "rutas locales", "rutas foraneas", "almacen", "inventarios",
    
    # Servicios Generales, Mantenimiento y Limpieza
    "limpieza", "sanitizacion", "mantenimiento", "limpieza de oficinas", "mantenimiento correctivo", 
    "mantenimiento preventivo", "desinfeccion", "pulido de pisos", "productos de limpieza",
    
    # Administración, Finanzas y Ventas
    "excel", "word", "sap", "contabilidad", "facturacion", "cobranza", "ventas", "atencion a clientes", "crm",
    
    # Idiomas y Certificaciones
    "ingles", "ingles avanzado", "ingles intermedio", "iso 9001", "scrum",
    
    # Tecnología
    "python", "java", "sql", "html", "css", "javascript", "c#", "php", "power bi"
]

def extraer_texto_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    texto = ""
    for page in doc:
        texto += page.get_text() + "\n"
    return texto

def extraer_email(texto: str) -> str:
    patron = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(patron, texto)
    return match.group(0) if match else "No detectado"

def extraer_telefono(texto: str) -> str:
    patron = r'(\+?\d{1,3}[\s-]?)?\(?\d{2,3}\)?[\s-]?\d{3,4}[\s-]?\d{4}'
    match = re.search(patron, texto)
    return match.group(0).strip() if match else "No detectado"

def extraer_skills(texto_cv: str, descripcion_vacante: str = "") -> list:
    """Identifica solo habilidades del catálogo que aparecen en el documento.

    La descripción del puesto no debe inventar habilidades del postulante.
    No transforma coincidencias de palabras arbitrarias en capacidades.
    """
    def normalizar(txt):
        txt = unicodedata.normalize("NFKD", str(txt or "").casefold())
        return "".join(ch for ch in txt if not unicodedata.combining(ch))

    contenido = normalizar(texto_cv)
    encontradas = set()
    for skill in SKILLS_UNIVERSALES:
        token = normalizar(skill)
        if re.search(r"(?<!\w)" + re.escape(token) + r"(?!\w)", contenido):
            encontradas.add(skill.title())
    return sorted(encontradas)


def generar_resumen_y_fit(texto_cv: str, descripcion_vacante: str, score: float, modo: str = "detallado") -> tuple:
    """Justificación exploratoria con evidencias textuales, sin recomendaciones automáticas."""
    import unicodedata

    def palabras(texto):
        normal = unicodedata.normalize("NFKD", str(texto or "").lower())
        normal = "".join(c for c in normal if not unicodedata.combining(c))
        return set(re.findall(r"[a-z][a-z0-9+#.]{2,}", normal))

    stop = set("para como sobre entre desde hasta que las los una unos unas del por con sin este estas estos donde debe debera puesto vacante experiencia conocimientos habilidades trabajo persona anos perfil requerimos buscamos tener cuenta mas sus".split())
    req = palabras(descripcion_vacante) - stop
    cv = palabras(texto_cv) - stop
    coincidencias = sorted(req & cv)
    sin_evidencia = sorted(req - cv)
    lineas = [l.strip() for l in str(texto_cv).splitlines() if 14 < len(l.strip()) < 500]
    resumen = (
        "Fragmento del CV (verificar fuente original): "
        + (" ".join(lineas[:2])[:280] if lineas else "No se identificó un resumen textual claro.")
    )
    justificacion = (
        f"Similitud semántica calculada: {float(score):.1f} % (indicador orientativo, no probabilidad). "
        f"Términos presentes en CV y requisitos: {', '.join(coincidencias[:14]) or 'sin coincidencias detectadas'}. "
        f"Términos que requieren verificación: {', '.join(sin_evidencia[:14]) or 'no identificados'}. "
        "La ausencia de una palabra NO demuestra ausencia de una habilidad. "
        "Revisar manualmente los requisitos y la experiencia; no tomar decisiones automáticas."
    )
    return resumen, justificacion

# parser.py
import fitz
import re

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
    texto_lower = texto_cv.lower()
    skills_encontradas = set()
    
    # 1. Catálogo universal
    for skill in SKILLS_UNIVERSALES:
        if re.search(r'\b' + re.escape(skill) + r'\b', texto_lower):
            skills_encontradas.add(skill.title())
            
    # 2. Extracción dinámica basada en la Vacante
    if descripcion_vacante:
        palabras_vacante = set(re.findall(r'\b[a-zA-Za-áéíóúñÑ]{5,}\b', descripcion_vacante.lower()))
        stopwords = {"experiencia", "requerido", "solicita", "trabajo", "mínimo", "años", "conocimiento", "capacidad", "perfil", "vacante", "puesto", "empresa", "área"}
        palabras_clave = palabras_vacante - stopwords
        
        for kw in palabras_clave:
            if re.search(r'\b' + re.escape(kw) + r'\b', texto_lower):
                skills_encontradas.add(kw.title())

    return sorted(list(skills_encontradas))

def generar_resumen_y_fit(texto_cv: str, descripcion_vacante: str, score: float, modo: str = "detallado") -> tuple:
    lineas = [l.strip() for l in texto_cv.split("\n") if len(l.strip()) > 15]
    
    if modo == "corto":
        extracto = " ".join(lineas[:2]) if lineas else "Sin información suficiente."
        resumen = f"**Síntesis:** {extracto[:180]}..."
        
        if score >= 60:
            justificacion = f"🟢 **Match Alto ({score}%):** Alta compatibilidad con los requerimientos principales."
        elif score >= 25:
            justificacion = f"🟡 **Match Medio ({score}%):** Compatibilidad parcial. Validar en entrevista."
        else:
            justificacion = f"🔴 **Match Bajo ({score}%):** Poca o nula coincidencia con el perfil buscado."
    else:
        extracto_ampliado = " ".join(lineas[:6]) if lineas else "Sin información suficiente."
        puntos_destacados = lineas[2:6] if len(lineas) >= 6 else lineas[1:]
        bloque_puntos = "\n".join([f"• {p[:110]}..." for p in puntos_destacados[:3]])
        
        resumen = (
            f"**Síntesis Ampliada del Perfil:**\n"
            f"{extracto_ampliado[:450]}...\n\n"
            f"**Trayectoria y Aspectos Destacados:**\n"
            f"{bloque_puntos if bloque_puntos else '• Información extraída del documento.'}"
        )
        
        if score >= 60:
            justificacion = (
                f"🟢 **Perfil Altamente Compatible ({score}% match)**\n"
                f"• **Análisis:** El candidato cubre las competencias clave y la trayectoria solicitada para el puesto.\n"
                f"• **Recomendación:** Agendar entrevista directamente."
            )
        elif score >= 25:
            justificacion = (
                f"🟡 **Candidato Potencial ({score}% match)**\n"
                f"• **Análisis:** Presenta coincidencia en aspectos generales pero requiere evaluación en áreas específicas.\n"
                f"• **Recomendación:** Realizar filtro telefónico previo."
            )
        else:
            justificacion = (
                f"🔴 **Match Bajo ({score}% match)**\n"
                f"• **Análisis:** El perfil difiere considerablemente del área funcional y requerimientos de la vacante.\n"
                f"• **Recomendación:** No recomendado para esta posición."
            )
            
    return resumen, justificacion
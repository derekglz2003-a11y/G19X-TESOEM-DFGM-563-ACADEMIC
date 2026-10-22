"""Texto permitido en comparaciones de empleabilidad.

Este módulo construye el insumo del embedding exclusivamente a partir de perfil,
experiencia y habilidades. No concatena nombre, edad, sexo, correo, teléfono ni
el CV íntegro. El filtrado determinista reduce fugas de datos personales, pero
no sustituye la revisión humana de extracciones con texto libre.
"""

import re
import unicodedata
from typing import Any

# No se consideran evidencia laboral los valores genéricos del extractor antiguo.
VALORES_GENERICOS = {
    "", "no disponible", "no especificado", "no especificada", "n/a",
    "sin informacion", "sin habilidades detectadas", "sin experiencia registrada",
    "sin experiencia", "sin datos", "sin informacion disponible",
    "perfil general", "perfil operativo", "adaptabilidad", "disposicion laboral",
    "compromiso, responsabilidad, adaptabilidad", "compromiso responsabilidad adaptabilidad",
    "trayectoria no especificada en formato legible", "procesado visualmente",
}

# Campos estrictamente administrativos / características personales.
PATRON_ETIQUETA_PRIVADA = re.compile(
    r"(?im)^\s*(?:nombre(?:\s+completo)?|candidato|apellidos?|edad|sexo|g[eé]nero|"
    r"fecha\s+de\s+nacimiento|nacionalidad|estado\s+civil|direcci[oó]n|domicilio|"
    r"tel[eé]fono|celular|correo(?:\s+electr[oó]nico)?|email|e-mail|curp|rfc|"
    r"fotograf[ií]a|religi[oó]n|discapacidad)\s*[:\-].*$"
)
PATRON_EMAIL = re.compile(r"(?i)\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
PATRON_TELEFONO = re.compile(r"(?<!\w)(?:\+?52[\s.-]?)?(?:\(?\d{2,3}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}(?!\w)")
PATRON_EDAD = re.compile(
    r"(?i)\b(?:edad\s*:?\s*\d{1,2}(?:\s*a[ñn]os)?|"
    r"tengo\s*\d{1,2}\s*a[ñn]os|\d{1,2}\s*a[ñn]os\s*de\s*edad)\b"
)
PATRON_NOMBRE_LIBRE = re.compile(r"(?i)\b(?:mi nombre es|me llamo)\s+[^,.;\n]{2,65}")
PATRON_SEXO = re.compile(r"(?i)\b(?:sexo|g[eé]nero|estado\s+civil)\s*:\s*[\wáéíóúñ\-/ ]{1,25}")
PATRON_REQUISITO_DISCRIMINATORIO = re.compile(
    r"(?i)\b(?:solo\s+(?:hombres|mujeres)|(?:sexo|g[eé]nero)\s*:?\s*(?:masculino|femenino|hombre|mujer)|"
    r"edad\s*:?\s*\d{1,2}(?:\s*(?:a|hasta|-)\s*\d{1,2})?(?:\s*a[ñn]os)?|"
    r"(?:soltero|soltera|casado|casada)|(?:hombre|mujer)\s+de\s+\d{1,2}\s*a[ñn]os)\b"
)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or "").casefold())
    return "".join(c for c in texto if not unicodedata.combining(c)).strip(" .;,:\t\r\n")


def limpiar_texto_laboral(texto: Any) -> str:
    """Redacta datos explícitos; conserva contenido profesional verificable."""
    resultado = []
    for linea in str(texto or "").splitlines():
        linea = linea.replace("\x00", " ").strip()
        if not linea or PATRON_ETIQUETA_PRIVADA.match(linea):
            continue
        linea = PATRON_EMAIL.sub(" ", linea)
        linea = PATRON_TELEFONO.sub(" ", linea)
        linea = PATRON_EDAD.sub(" ", linea)
        linea = PATRON_NOMBRE_LIBRE.sub(" ", linea)
        linea = PATRON_SEXO.sub(" ", linea)
        linea = PATRON_REQUISITO_DISCRIMINATORIO.sub(" ", linea)
        linea = re.sub(r"\s+", " ", linea).strip(" ,.;:-")
        if linea and _normalizar(linea) not in VALORES_GENERICOS:
            resultado.append(linea)
    return "\n".join(resultado)[:4500]


def texto_laboral_candidato(candidato: Any) -> str:
    """Construye el texto exclusivamente con campos profesionales.

    Excluye el campo texto_completo de los embeddings porque puede contener
    información sensible; si las fichas antiguas están incompletas, deben
    revisarse o actualizarse antes de obtener un ranking confiable.
    """
    segmentos = []
    for nombre, campo in (
        ("Perfil profesional", "perfil_destacado"),
        ("Experiencia laboral", "experiencia"),
        ("Habilidades y competencias", "skills"),
    ):
        valor = limpiar_texto_laboral(getattr(candidato, campo, ""))
        if valor and _normalizar(valor) not in VALORES_GENERICOS:
            segmentos.append(f"{nombre}: {valor}")
    texto = "\n".join(segmentos)
    # Exigir información mínima que permita comparar; un perfil genérico no vale.
    contenido = re.sub(r"(?im)^(?:Perfil profesional|Experiencia laboral|Habilidades y competencias):\s*", "", texto)
    return texto if len(contenido.strip()) >= 8 else ""


def texto_laboral_vacante(titulo: str, descripcion: str) -> str:
    """Descarta requisitos demográficos explícitos también de la vacante."""
    contenido = limpiar_texto_laboral(f"{titulo or ''}\n{descripcion or ''}")
    return contenido

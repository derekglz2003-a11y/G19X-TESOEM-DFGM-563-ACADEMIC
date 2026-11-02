"""Catálogos sin dependencias de FastAPI, Streamlit ni bases de datos."""
CAMPOS = (
    'telefono', 'sexo', 'estado', 'municipio', 'domicilio_general',
    'nivel_estudios', 'carrera', 'institucion', 'estudios_detalle', 'certificaciones',
    'primer_empleo', 'anos_experiencia', 'experiencia', 'habilidades', 'fortalezas',
    'idiomas', 'resumen_profesional', 'puesto_deseado', 'area_interes',
    'zonas_preferidas', 'modalidad', 'jornada', 'disponibilidad',
)
NIVELES = (
    '', 'Sin escolaridad formal', 'Primaria', 'Secundaria', 'Bachillerato / Preparatoria',
    'Técnico / TSU', 'Licenciatura / Ingeniería', 'Especialidad', 'Maestría',
    'Doctorado', 'Otro',
)
SEXOS = ('', 'Prefiero no responder', 'Mujer', 'Hombre', 'No binario', 'Otra identidad')
MODALIDADES = ('', 'Presencial', 'Híbrido', 'Remoto', 'Indistinto')
JORNADAS = ('', 'Tiempo completo', 'Medio tiempo', 'Por proyecto', 'Prácticas', 'Indistinto')

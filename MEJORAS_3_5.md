# CurriculAi 3.5 — Motor semántico centrado en información laboral

## Objetivo

Atender las observaciones técnicas del corte previo sin cambiar el diseño de la interfaz ni las tablas de candidatos y vacantes.

## Qué cambió

1. **Evaluación de perfiles:** `main.py` deja de pasar `texto_completo` al motor de embeddings. `servicios/perfil_laboral.py` prepara exclusivamente `perfil_destacado`, `experiencia` y `skills`, y elimina etiquetas de información personal explícita. El resultado **no es una decisión de contratación**.
2. **Fichas incompletas:** omite perfiles sin evidencia profesional útil y reporta cuántos quedaron pendientes; si se reevalúa una vacante, retira solamente sus evaluaciones antiguas que ya no tienen respaldo profesional. **No borra los candidatos ni sus CV.**
3. **Extracción independiente:** `servicios/extractores_cv.py` centraliza PDF, DOCX (incluidas tablas), TXT e imágenes. Si un PDF no tiene texto extraíble, intenta OCR de las tres primeras páginas. El archivo `.doc` binario antiguo **no se admite**; se indica cómo convertirlo.
4. **Extractor local:** identifica habilidades del catálogo incluso cuando hay acentos, y evita asignar fortalezas o potencial sin evidencia. La extracción con Gemini usa `GEMINI_MODEL` cuando está configurado.
5. **Motor principal:** `embeddings.py` sigue siendo el motor de similitud; opcionalmente permite `EMBEDDINGS_MODEL` en `.env`. `motor_ranking.py` se excluye del paquete completo porque no es utilizado. En instalaciones existentes, elimínalo de Git solo después de confirmar que no hay importaciones locales.
6. **UI:** Radar y Vacantes explican la cantidad de expedientes omitidos por información profesional insuficiente. No se modifica el menú horizontal de 3.3.3.

## Pruebas reproducibles

Ejecutar desde la raíz, sin usar CV reales:

```powershell
.\venv\Scripts\python.exe -m pytest -q tests
```

Se ejecutaron **19 pruebas y pasaron** en entorno de desarrollo, con SQLite temporal y embeddings simulados, incluyendo importación de DOCX/TXT, creación de ranking, ausencia de datos personales en la entrada semántica, omisión de campos genéricos, borrado de rankings obsoletos, autenticación y flujo de entrevistas. El OCR de un PDF escaneado se validó con una respuesta simulada de Tesseract.

**No se ha medido con CV reales la precisión del modelo semántico** ni se ha probado esta versión con Supabase, Gemini, WhatsApp o Tesseract real. Antes de re-evaluar registros reales, realiza una copia de seguridad y prueba con documentos ficticios.

## Privacidad y límites

- En los embeddings no entran directamente el nombre, la edad, el sexo, el correo, el teléfono ni el CV completo. Las cadenas libres de perfil/experiencia/habilidades pueden contener datos personales inesperados; el filtrado basado en patrones reduce ese riesgo, pero **no garantiza anonimización**.
- Los datos de contacto y las características históricas de expedientes anteriores pueden seguir existiendo en la base de datos. Esta actualización **no los borra** ni introduce una migración de esquema.
- La similitud expresa cercanía matemática entre textos, **no probabilidad de éxito laboral**. Revisión humana y auditoría de sesgos siguen pendientes.
- El motor por defecto conserva `all-MiniLM-L6-v2` para no cambiar puntuaciones sorpresivamente. Se puede experimentar con `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` para CV en español: requiere descarga y validación nueva.

## Siguiente paso

Actualizar PRD y MVP con objetivos y criterios de aceptación, incorporar una política de retención de CV y realizar pruebas de aceptación del flujo completo en un entorno separado de datos reales.

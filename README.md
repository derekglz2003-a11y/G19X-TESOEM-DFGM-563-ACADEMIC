# CurriculAI — Optimizador de Filtrado Curricular

Prototipo académico de gestión de vacantes, carga de CV, ranking semántico orientativo, entrevistas y notificaciones WhatsApp.

## Requisitos
- Python 3.11 recomendado.
- Tesseract OCR instalado y disponible en PATH para imágenes.
- Conexión a Internet en el primer uso de `sentence-transformers` para descargar `all-MiniLM-L6-v2`.
- SQLite local por defecto o PostgreSQL mediante `DATABASE_URL`.

## Instalación (PowerShell)
```powershell
cd C:\motorcv
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```
Edita `.env` con tus valores reales. **Nunca publiques `.env` ni claves.** `DATABASE_URL` puede omitirse para SQLite; `API_URL=http://127.0.0.1:8000` para desarrollo local. `GEMINI_API_KEY` es necesaria para generar descripciones y extraer datos con Gemini, pero el ranking semántico funciona localmente.

## Ejecución (dos terminales)
```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```
```powershell
.\venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```
Abrir http://localhost:8501. Documentación API: http://localhost:8000/docs.

## Recorrido
1. Crear una vacante.
2. Cargar CVs y comprobar que se extrajo texto (PDF, DOCX o imagen con OCR).
3. Ir a **Radar de talentos**, seleccionar vacante y pulsar **Encontrar los 5 mejores candidatos**. Se recalculan y guardan evaluaciones.
4. Revisar manualmente la pertinencia y agendar entrevistas.
5. Eliminar CV, candidato o vacante con confirmación cuando corresponda.

## Limitaciones y seguridad
- El porcentaje es una **similitud semántica**, no una probabilidad de éxito ni una decisión automatizada de contratación.
- La evaluación y los resúmenes locales no utilizan Gemini. El generador de descripciones sí lo usa cuando hay clave válida.
- Antes de publicar: añadir autenticación, autorización por roles, protección de datos personales, validación de archivos, límites de subida y políticas de retención.
- El esquema incluye datos sensibles de postulantes; usar datos de prueba para demostraciones.

## Uso de IA en el desarrollo
Se utilizó asistencia de ChatGPT para revisar código, integrar el ranking y redactar documentación. Las decisiones y pruebas finales corresponden al desarrollador.

# CurriculAi — Optimizador de filtrado curricular con IA

Prototipo académico de gestión de vacantes y candidatos, análisis semántico orientativo, entrevistas y bitácora de WhatsApp. **MVP administrativo**: acceso de un único administrador. No incluye todavía portal de candidatos ni permisos por roles.

## Requisitos

- Python 3.11 recomendado y las dependencias de `requirements.txt`.
- Tesseract OCR instalado para reconocer texto en imágenes.
- Conexión a Internet en la primera ejecución del modelo `all-MiniLM-L6-v2`, que puede tardar en descargarse.
- SQLite para desarrollo o PostgreSQL cuando se configure `DATABASE_URL`.

## Instalación en Windows / PowerShell

Desde la **carpeta del repositorio** (sin usar una ruta fija):

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe scripts\configurar_acceso.py
```

El asistente pedirá una contraseña de al menos 12 caracteres y creará/actualizará `.env` con una **derivación PBKDF2** y una **clave aleatoria para FastAPI**. Si ya tienes `.env`, conserva sus otras variables, incluida tu conexión a la base de datos y las integraciones opcionales. No subas `.env` a GitHub.

`.env.example` contiene únicamente los nombres y valores públicos de ejemplo. Puedes copiarlo primero para establecer `DATABASE_URL` y `API_URL`, aunque el generador ya puede crear `.env` directamente.

**IMPORTANTE:** La nueva versión bloqueará el panel y las rutas de API si no ejecutas la configuración de acceso. Haz un respaldo de tu base de datos antes de actualizar.

## Iniciar CurriculAi (dos terminales)

**Terminal 1 — Backend:**

```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

**Terminal 2 — Interfaz:**

```powershell
.\venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

Entra a `http://localhost:8501`, escribe la contraseña creada y utiliza los módulos. En `Configuración` puedes cerrar sesión. Si cambias la contraseña o clave de API, **reinicia ambos procesos**.

Swagger puede abrirse en `http://localhost:8000/docs`, pero **todas las operaciones** exigen el encabezado `X-API-Key`. No compartas esa clave ni la incrustes en JavaScript o en código que llega al navegador.

## Flujo del MVP

1. Crea una vacante con responsabilidades y requisitos.
2. Carga CV en PDF, DOCX, TXT o imagen, respetando las limitaciones de extracción y OCR.
3. Abre la vacante o Radar de talentos y ejecuta el ranking semántico.
4. Revisa las evidencias manualmente y da seguimiento al candidato.
5. Agenda entrevistas, gestiona finalistas y registra la notificación WhatsApp si el proveedor está configurado.

## Qué protege la versión 3.4

- La interfaz solicita contraseña antes de mostrar los expedientes.
- El servidor FastAPI exige una clave privada `X-API-Key` para todas las rutas operativas (lectura, creación, edición y borrado).
- No se permite un acceso abierto cuando faltan credenciales: se rechazan peticiones.
- Las credenciales están en `.env` y no se incluyen en el repositorio.
- Las pruebas verifican que una lectura y un DELETE sin autorización fallen.

**Limitaciones de seguridad:** Esta protección es un primer corte para un prototipo académico, **no una solución lista para Internet**. Para producción faltan HTTPS, cuentas individuales, autorización por roles, control de intentos, auditoría, sesiones de mayor seguridad, políticas de retención y despliegue aislado. No subir CV reales, datos personales ni bases de datos al repositorio público.

## CurriculAi 3.5 — perfil laboral y ranking

El ranking usa únicamente `perfil_destacado`, `experiencia` y `skills`. No incluye
`nombre`, `edad`, `sexo`, contacto ni `texto_completo` en los embeddings. Si
las fichas heredadas solo tienen valores genéricos, se omiten hasta revisarlas.
Al evaluar una vacante se actualizan sus evaluaciones y pueden retirarse
puntuaciones antiguas carentes de evidencia; no se eliminan los candidatos.

Los PDF escaneados pueden requerir OCR (máximo tres páginas en el fallback),
`.docx` incluye tablas, `.txt` está admitido y `.doc` antiguo no: convértelo
antes a DOCX o PDF. El motor por defecto sigue siendo
`sentence-transformers/all-MiniLM-L6-v2`; puedes probar el modelo multilingüe
estableciendo `EMBEDDINGS_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
en `.env` (descarga inicial y puntuaciones diferentes). **No es una
validación de sesgos**: revisa con personas los resultados y los campos
extraídos, porque puede quedar información privada en texto libre.

## Limitaciones del motor IA

El porcentaje es una **similitud semántica orientativa**, no una probabilidad de contratación ni una decisión automática. La revisión humana es obligatoria. No deben usarse características personales protegidas para clasificar perfiles. Los resultados requieren validación de extracción y pertinencia. La generación de descripciones usa Gemini si existe una credencial `GEMINI_API_KEY` válida; el ranking semántico opera localmente.

## Pruebas

```powershell
.\venv\Scripts\python.exe -m pytest -q tests
```

Las pruebas usan una **base temporal** y simulan el cálculo de embeddings; no son una medición de calidad del modelo semántico. Verifican además los permisos del backend. Antes de registrar el commit, comprueba que `git status` no incluya `.env`, CV ni bases de datos.

## Entorno reproducible y modelo Gemini (versión 3.8)

- Las dependencias se declaran en `requirements.txt`, incluido `google-genai` (SDK actual utilizado por `servicios/gemini_ia.py`) y `pytest` para pruebas. No instalar `google-generativeai` como reemplazo del SDK nuevo.
- `GEMINI_MODEL=gemini-3.8-flash` es el valor de ejemplo en `.env.example` y el valor predeterminado del servicio. Requiere `GEMINI_API_KEY` y acceso habilitado por Google para la cuenta. Si la cuenta no dispone del modelo, selecciona uno **realmente disponible en tu proyecto**, actualiza `.env` y reinicia FastAPI. No publiques tu clave.
- El modelo de similitud (distinto a Gemini) se configura opcionalmente con `EMBEDDINGS_MODEL`; su primera descarga requiere conexión a Internet.
- En CurriculAi 3.8 se ejecutaron **28 pruebas exitosas** con SQLite aislado y simulaciones; esta cifra es una evidencia del corte y puede crecer con nuevos tests. La integración real con Supabase, Gemini y UltraMsg requiere pruebas separadas.
- Cuando falle el endpoint de ranking, FastAPI devuelve `500` en lugar de simular que no hay candidatos; las pantallas Radar y Vacantes muestran ese error explícitamente.

El procedimiento de aceptación manual, las capturas previstas y la trazabilidad de pruebas se describen en `docs/PLAN_EVIDENCIAS_MVP.md`. Las capturas y datos usados para demostración deben ser ficticios.

## Uso de IA en el desarrollo

Se utilizó asistencia de ChatGPT para revisión técnica, mejoras de seguridad, generación de pruebas y documentación. El desarrollador revisa, valida y decide qué cambios integrar.

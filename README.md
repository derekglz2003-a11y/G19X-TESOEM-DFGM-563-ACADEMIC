# CurriculAi — Optimizador de filtrado curricular con IA

Prototipo académico de reclutamiento con **dos vistas separadas**: administración (vacantes, expedientes, ranking semántico orientativo, entrevistas y decisiones) y portal del candidato (cuenta propia, perfil, CV manual o cargado, vacantes publicadas, postulaciones y avisos en la web). El sistema incorpora controles básicos de acceso por rol; **no es una aplicación validada para desplegarse públicamente con CV reales**.

## Requisitos

- Python 3.11 recomendado y las dependencias de `requirements.txt`.
- Tesseract OCR instalado para reconocer texto en imágenes.
- Conexión a Internet en la primera ejecución del modelo `all-MiniLM-L6-v2`, que puede tardar en descargarse.
- **Base de datos de referencia para esta entrega reproducible: SQLite** (`DATABASE_URL=sqlite:///./motor_cv.db`, según `.env.example`). PostgreSQL/Supabase es una alternativa opcional que requiere configurar `DATABASE_URL` explícitamente. No se afirma que la base actualmente utilizada en la computadora del desarrollador sea SQLite: hay que comprobar su `.env` privado antes de las pruebas.

## Instalación en Windows / PowerShell

Desde la **carpeta del repositorio** (sin usar una ruta fija):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\configurar_acceso.py
```

El asistente pedirá una contraseña de al menos 12 caracteres y creará/actualizará `.env` con una **derivación PBKDF2** y una **clave aleatoria para FastAPI**. Si ya tienes `.env`, conserva sus otras variables, incluida tu conexión a la base de datos y las integraciones opcionales. Para una **instalación de entrega o prueba aislada**, comprueba que `DATABASE_URL` apunte a SQLite de prueba, **nunca** a una base remota que contenga datos reales. No subas `.env` a GitHub.

`.env.example` contiene únicamente nombres y valores de ejemplo. Para reproducir la entrega, utiliza `DATABASE_URL=sqlite:///./motor_cv.db` en el `.env` privado (según la configuración de referencia indicada en la revisión). Puedes copiar `.env.example` antes de ejecutar el generador, que conserva otras variables. PostgreSQL/Supabase es opcional, pero **no se necesita** para la instalación de referencia; tampoco se debe apuntar a una base remota real durante pruebas destructivas.

**IMPORTANTE:** La nueva versión bloqueará el panel y las rutas de API si no ejecutas la configuración de acceso. Haz un respaldo de tu base de datos antes de actualizar.

## Iniciar CurriculAi (dos terminales)

**Terminal 1 — Backend:**

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

**Terminal 2 — Interfaz:**

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

Entra a `http://localhost:8501`. Selecciona **Administrador** para entrar con la contraseña configurada, o **Candidato** para registrarte/iniciar sesión con tu cuenta propia. Ambos tienen cierre de sesión. Si cambias las credenciales de la API, **reinicia ambos procesos**.

Los puertos **8000/8501 son los valores de ejemplo para una instalación nueva**. Si trabajas con FastAPI en 8010 y Streamlit en 8502, establece `API_URL=http://127.0.0.1:8010` en la terminal de Streamlit (o en `.env`) y arranca los procesos en esos puertos. Los dos procesos deben usar la **misma `DATABASE_URL`**; no se sincronizan automáticamente las bases SQLite de prueba ni Supabase.

Swagger administrativo puede abrirse en `http://localhost:8000/docs`. Las rutas administrativas protegidas exigen el encabezado `X-API-Key`; las rutas privadas del candidato bajo `/portal` utilizan su token de sesión `Bearer`, y registro/ingreso tienen sus propias validaciones. No compartas ninguna credencial ni la incrustes en JavaScript o código que llega al navegador.

## Flujo del MVP

1. Crea una vacante con responsabilidades y requisitos.
2. Carga CV en PDF, DOCX, TXT o imagen, respetando las limitaciones de extracción y OCR.
3. Abre la vacante o Radar de talentos y ejecuta el ranking semántico.
4. Revisa las evidencias manualmente y da seguimiento al candidato.
5. Agenda entrevistas, gestiona finalistas y registra la notificación WhatsApp si el proveedor está configurado.


## Funciones del portal del candidato

- **Registro y acceso independientes** del administrador. La cuenta recién creada no se incorpora automáticamente al pool evaluable.
- **Mi perfil y Mi CV:** completar información laboral, crear CV manualmente o cargar un archivo; descargar el CV elaborado en Word. El CV solo pasa al pool administrativo cuando la persona elige **Compartir mi CV**.
- **Expediente único:** las actualizaciones del CV compartido reutilizan la vinculación de la cuenta y retiran puntajes anteriores para recalcularlos. No se generan resultados automáticos de contratación.
- **Vacantes y postulaciones:** el administrador publica expresamente una vacante; el candidato puede consultarla y postularse. El sistema impide repetir la misma postulación activa.
- **Mis entrevistas y Notificaciones:** el candidato consulta citas asociadas a sus postulaciones y avisos persistentes sobre invitaciones, entrevistas y resultados que un reclutador haya registrado. Los avisos son privados de su cuenta.
- **Limitación del esquema actual:** `Entrevista.candidato_id` es único; aún no se admiten varias entrevistas independientes por candidato sin rediseñar/migrar esa relación.

**Regla de uso de IA:** el porcentaje del ranking es orientativo, no una probabilidad de contratación; solo el reclutador decide y el candidato no recibe el ranking interno de otros usuarios.

**Validación:** el portal forma parte del alcance ampliado descrito en `PRD.md` y `MVP.md`. Las pruebas automáticas incluyen escenarios simulados de portal y notificaciones, pero **no sustituyen** la comprobación con OCR, Gemini, UltraMsg, permisos reales y una instalación limpia. Antes de la entrega final, conserva evidencia de `pytest` y comprueba que la base de pruebas sea aislada.

## Seguridad: antecedente de la versión 3.4 y portal actual

- La interfaz solicita contraseña antes de mostrar los expedientes.
- El servidor FastAPI exige una clave privada `X-API-Key` para las rutas administrativas protegidas (lectura, creación, edición y borrado); el portal verifica su propia sesión `Bearer` en las operaciones privadas.
- No se permite un acceso abierto cuando faltan credenciales: se rechazan peticiones.
- Las credenciales están en `.env` y no se incluyen en el repositorio.
- Las pruebas verifican que una lectura y un DELETE sin autorización fallen.

**Estado actual:** el portal de candidatos añade registro y sesiones propias mediante `Bearer`; sus rutas de perfil, postulaciones y notificaciones comprueban la identidad del candidato. El backend administrativo continúa protegido con `X-API-Key`. No se deben confundir estas dos credenciales.

**Limitaciones de seguridad:** estos controles son para un **prototipo académico local**, no constituyen una solución lista para Internet. Antes de desplegar con datos reales faltan HTTPS, limitación de intentos, auditoría de accesos, política de retención/supresión, evaluación de seguridad, estrategia de respaldo y autorización por empresa si se implementan múltiples administradores. No subir CV reales, datos personales ni bases de datos al repositorio público.

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

## Pruebas automatizadas y evidencia vigente

Desde la raíz del repositorio, con las dependencias de `requirements.txt` instaladas:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
```

**Resultado local informado el 7 de noviembre de 2026:** **50 pruebas aprobadas, 0 fallidas y 2 advertencias**; duración de la ejecución: **36.68 s**. **HEAD consultado después de la ejecución:** `c8db09a`. Salida observada:

```text
50 passed, 2 warnings in 36.68s
```

**Alcance de la evidencia:** el resultado corresponde al **directorio local `C:\motorcv`**, donde `git status --short` mostró archivos sin seguimiento. El SHA `c8db09a` identifica el HEAD consultado, **pero no garantiza por sí mismo que un clon de ese commit reproduzca el resultado**. Faltan el registro de instalación limpia, la comprobación de archivos entregados y la evidencia de la interfaz de extremo a extremo. Conservar la captura de la terminal sin información confidencial.

Las pruebas usan bases temporales y simulaciones de embeddings, Gemini y parte del OCR; comprueban código y controles básicos de acceso, **no** la pertinencia del modelo ni el funcionamiento real de Supabase, Gemini, UltraMsg o Tesseract. Las **28 pruebas del corte administrativo 3.8 (26-oct-2026)** son un resultado **histórico**, no la cifra vigente. Antes del commit final revisa también que `git status` no incluya `.env`, CV reales ni bases de datos privadas.

## Entorno reproducible y modelo Gemini

- Las dependencias de pruebas **`pytest`**, **`httpx`** y **`PyMuPDF`** figuran en `requirements.txt` (comprobadas en la terminal el 7-nov-2026). El proyecto documenta `google-genai` como SDK de `servicios/gemini_ia.py`; no usar `google-generativeai` como sustituto sin adaptar el código.
- El valor declarado en el código y en la documentación anterior es `GEMINI_MODEL=gemini-3.8-flash`. **No hay evidencia adjunta de que ese modelo haya respondido realmente con la cuenta del proyecto.** No debe presentarse como modelo validado. Para cerrar este punto: configurar una clave privada autorizada, generar una descripción, anotar **el identificador del modelo que sí respondió** y alinear `.env.example`, `MODELO_PREDETERMINADO` del servicio y este README; conservar una captura sin la clave. Si se cambia el valor, repetir `pytest`.
- El modelo de similitud (distinto de Gemini) se configura con `EMBEDDINGS_MODEL`; su primera descarga requiere Internet.
- Cuando falla el endpoint de ranking, la API debe comunicar el error en vez de simular una lista de cero candidatos; verificarlo de nuevo en la instalación limpia.

## Datos de prueba y demostración reproducible (pendiente de completar)

Para la evaluación final se debe agregar al repositorio un directorio `datos_prueba/` con al menos **tres CV íntegramente ficticios en formatos diferentes** (por ejemplo, TXT, DOCX y PNG) y un archivo `datos_prueba/vacantes_ejemplo.md` con vacantes ficticias. No se incluyen esos archivos en esta actualización de documentación y **aún no se considera completado este requisito**.

Con esos materiales, la demostración será:

1. Crear una instalación limpia con SQLite de prueba y configurar la contraseña administrativa mediante `scripts/configurar_acceso.py` (no publicarla).
2. Iniciar FastAPI y Streamlit; seleccionar **Administrador** y crear/publicar una vacante ficticia.
3. Cargar CV ficticios desde `datos_prueba/` y ejecutar el ranking. Interpretar los porcentajes como similitud orientativa.
4. Seleccionar **Candidato**, registrarse con datos ficticios, crear/cargar un CV y elegir **Compartir mi CV**.
5. Postularse a la vacante publicada; comprobar desde administración la postulación, crear una entrevista y revisar el aviso en la cuenta del candidato.
6. Guardar los resultados, errores y capturas de la instalación aislada en `docs/cierre_mvp_2026-10-26/INSTALACION_LIMPIA.md` o en el registro de entrega correspondiente (archivo **pendiente de crear**).

**No hay credenciales de demostración publicadas:** el administrador utiliza la contraseña definida localmente y cada candidato se registra con una contraseña ficticia de prueba. No incluir credenciales reales, CV reales ni archivos `.env` en Git.

La evidencia histórica del MVP administrativo está en [`docs/cierre_mvp_2026-10-26/README.md`](docs/cierre_mvp_2026-10-26/README.md). Revisa que esa ruta exista en el commit final; el documento histórico no sustituye las pruebas de la versión con portal. Usa únicamente datos ficticios en las capturas.

## Uso de IA en el desarrollo

Se utilizó asistencia de ChatGPT para revisión técnica, mejoras de seguridad, generación de pruebas y documentación. El desarrollador revisa, valida y decide qué cambios integrar.

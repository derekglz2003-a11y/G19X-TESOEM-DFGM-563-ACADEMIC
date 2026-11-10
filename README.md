# CurriculAi — Optimizador de filtrado curricular con IA

Prototipo académico de reclutamiento con **dos vistas separadas**: administración (vacantes, expedientes, ranking semántico orientativo, entrevistas y decisiones) y portal del candidato (cuenta propia, perfil, CV manual o cargado, vacantes publicadas, postulaciones y avisos en la web). El sistema incorpora controles básicos de acceso por rol; **no es una aplicación validada para desplegarse públicamente con CV reales**.

## Requisitos

- Python 3.11 recomendado y las dependencias de `requirements.txt`.
- Tesseract OCR instalado para reconocer texto en imágenes.
- Conexión a Internet en la primera ejecución del modelo `all-MiniLM-L6-v2`, que puede tardar en descargarse.
- **Base de datos de referencia para esta entrega reproducible: SQLite** (`DATABASE_URL=sqlite:///./motor_cv.db`, según `.env.example`). PostgreSQL/Supabase es una alternativa opcional que requiere configurar `DATABASE_URL` explícitamente. No se afirma que la base actualmente utilizada en la computadora del desarrollador sea SQLite: hay que comprobar su `.env` privado antes de las pruebas.

## Instalación en Windows / PowerShell

Desde la **carpeta del repositorio** (sin usar una ruta fija), selecciona explícitamente **Python 3.11** en Windows. Comprueba las versiones disponibles con `py -0p` si es necesario; en una instalación anterior, `python` apuntaba a una versión diferente y creó un entorno virtual con estructura no compatible con los comandos de Windows:

```powershell
py -3.11 -m venv .venv
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

**Validación:** el portal forma parte del alcance ampliado descrito en `PRD.md` y `MVP.md`. En el clon independiente `C:\prueba-limpia` se comprobaron el acceso del administrador y del candidato, una vacante publicada, la evaluación real de 15 CV, la postulación, los avisos, una entrevista y la decisión final. Las pruebas automáticas contienen simulaciones y **no sustituyen** la comprobación independiente de OCR real, Gemini, UltraMsg, seguridad de producción ni calidad del ranking. Véase [`INSTALACION_LIMPIA.md`](docs/cierre_mvp_2026-10-26/INSTALACION_LIMPIA.md).

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

**Resultado vigente verificado el 7 de noviembre de 2026 en clon independiente:** **52 pruebas aprobadas, 0 fallidas y 1 advertencia** en **46.81 s**. **Commit del código verificado:** `9f9bbc8` (confirmado con `git rev-parse --short HEAD` en `C:\prueba-limpia`). Se clonó desde GitHub, se instaló un entorno virtual nuevo en Windows con Python 3.11 y se ejecutó `pytest`:

```text
52 passed, 1 warning in 46.81s
```

**Evidencia manual:** en la misma instalación de prueba se creó y publicó una vacante ficticia, se ejecutó el ranking semántico real sobre **15 CV**, se observó la postulación de una cuenta de candidato, las notificaciones, una entrevista y una decisión final. El error inicial provocado por `EMBEDDINGS_MODEL` vacía se corrigió en `embeddings.py` y `.env.example`; dos pruebas de regresión se añadieron al commit `9f9bbc8`. La bitácora completa está en [`docs/cierre_mvp_2026-10-26/INSTALACION_LIMPIA.md`](docs/cierre_mvp_2026-10-26/INSTALACION_LIMPIA.md). La bitácora fue publicada en el commit `36eb2f9`. Los datos de demostración se describen abajo y se integran en un commit separado; no se consideran publicados hasta comprobarlos en GitHub.

**Historial de resultados:** antes de esa corrección se registraron **50 pruebas, 0 fallidas y 2 advertencias** (36.68 s) en `C:\motorcv`, HEAD `c8db09a`; y **50 pruebas, 1 advertencia** en un clon de `fac9ce2`. Son ejecuciones anteriores, **no el conteo vigente**.

Las pruebas automatizadas usan bases temporales y simulaciones de embeddings, Gemini y parte del OCR; comprueban código y controles básicos de acceso, **no** la pertinencia del modelo ni el funcionamiento real de Supabase, Gemini, UltraMsg o Tesseract. El cálculo real del ranking sí se comprobó **por separado en la demostración manual**. Las **28 pruebas del corte administrativo 3.8 (26-oct-2026)** son un resultado histórico. Antes del commit final revisa también que `git status` no incluya `.env`, CV reales ni bases de datos privadas.

## Entorno reproducible y modelo Gemini

- Las dependencias de pruebas **`pytest`**, **`httpx`** y **`PyMuPDF`** figuran en `requirements.txt` (comprobadas en la terminal el 7-nov-2026). El proyecto documenta `google-genai` como SDK de `servicios/gemini_ia.py`; no usar `google-generativeai` como sustituto sin adaptar el código.
- El valor declarado en el código y en la documentación anterior es `GEMINI_MODEL=gemini-3.8-flash`. **No hay evidencia adjunta de que ese modelo haya respondido realmente con la cuenta del proyecto.** No debe presentarse como modelo validado. Para cerrar este punto: configurar una clave privada autorizada, generar una descripción, anotar **el identificador del modelo que sí respondió** y alinear `.env.example`, `MODELO_PREDETERMINADO` del servicio y este README; conservar una captura sin la clave. Si se cambia el valor, repetir `pytest`.
- El modelo de similitud (distinto de Gemini) se configura con `EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2` en `.env.example`. Desde `9f9bbc8`, `embeddings.py` también usa ese valor si la variable está vacía o ausente; su primera descarga requiere Internet.
- Cuando falla el endpoint de ranking, la API comunica el error en vez de simular una lista de cero candidatos. Durante la prueba manual se detectó un HTTP 500 por una variable de modelo vacía; tras corregirla, el ranking real procesó 15 CV.

## Datos de prueba y demostración reproducible

La carpeta [`datos_prueba/`](datos_prueba/README.md) se preparó con **tres CV completamente ficticios**, en distintos formatos, y **dos vacantes de ejemplo**. Está destinada a la demostración de la entrega y debe incluirse junto con este README en el commit de datos de prueba; hasta verificar ese commit en GitHub no debe considerarse publicada.

| Archivo | Uso en la demostración |
|---|---|
| [`CV_01_Auxiliar_Administrativo.txt`](datos_prueba/cv/CV_01_Auxiliar_Administrativo.txt) | Extracción de texto y ranking sobre una vacante administrativa. |
| [`CV_02_Auxiliar_Contable.docx`](datos_prueba/cv/CV_02_Auxiliar_Contable.docx) | Lectura de Word y de información organizada en tablas. |
| [`CV_03_Soporte_Tecnico_OCR.png`](datos_prueba/cv/CV_03_Soporte_Tecnico_OCR.png) | Prueba de OCR en imagen, **si se ha instalado y configurado Tesseract**. |
| [`vacantes_ejemplo.md`](datos_prueba/vacantes_ejemplo.md) | Textos de dos vacantes para registrar manualmente en la interfaz. |
| [`datos_prueba/README.md`](datos_prueba/README.md) | Procedimiento detallado y precauciones de demostración. |

### Acceso a las dos vistas

**Administrador:** en una instalación aislada, ejecuta `scripts/configurar_acceso.py` con Python del entorno virtual; elige una contraseña local de al menos 12 caracteres, inicia FastAPI y Streamlit como se indica arriba, selecciona «Administrador» e inicia sesión con la contraseña recién creada. **No existe una contraseña administrativa publicada ni se debe compartir el `.env`.**

**Candidato:** en la pantalla inicial selecciona «Candidato» y «Registrarse». Usa únicamente datos sintéticos y una contraseña de prueba de al menos 12 caracteres; luego completa el perfil y crea o carga su CV. El CV pasa al pool administrativo cuando la persona lo comparte expresamente; postularse a una vacante es una acción separada.

### Orden recomendado para demostrar el sistema

1. Clonar el repositorio en una carpeta nueva y crear una **base SQLite de prueba**, nunca una base remota con datos reales.
2. Instalar dependencias, configurar la contraseña administrativa y arrancar FastAPI y Streamlit en dos terminales.
3. Entrar como **Administrador**, crear una de las vacantes de [`vacantes_ejemplo.md`](datos_prueba/vacantes_ejemplo.md) y publicarla.
4. Cargar los CV TXT y DOCX desde **Candidatos** y, si Tesseract está disponible, probar también el PNG. Registrar cualquier error de extracción sin ocultarlo.
5. Ejecutar el ranking desde **Vacantes** o **Radar de talentos**. Los porcentajes expresan similitud textual orientativa, no probabilidad de contratación.
6. Cerrar sesión administrativa; entrar como **Candidato**, registrar una cuenta ficticia, crear o cargar un CV y seleccionar **Compartir mi CV**.
7. Abrir la vacante publicada y postularse; regresar como administrador y comprobar la postulación, agendar una entrevista y registrar una decisión humana.
8. Volver a la cuenta de candidato y comprobar sus avisos y seguimiento. Para probar el aislamiento, utilizar una **segunda cuenta ficticia** y verificar que no pueda consultar avisos ajenos.

**Evidencia anterior:** la instalación limpia, el cálculo semántico con 15 CV y el recorrido de postulación a finalista quedaron documentados en [`INSTALACION_LIMPIA.md`](docs/cierre_mvp_2026-10-26/INSTALACION_LIMPIA.md), publicado en `36eb2f9`. Esos resultados corresponden a los datos y al entorno utilizados entonces; **la nueva carpeta `datos_prueba/` todavía requiere su propia comprobación después de publicarse**.

**Privacidad:** no publicar `.env`, contraseñas, claves API, CV reales, bases SQLite ni capturas con datos personales. La prueba de Gemini real es **independiente y sigue pendiente de acreditación**. La documentación histórica del MVP administrativo está en [`docs/cierre_mvp_2026-10-26/README.md`](docs/cierre_mvp_2026-10-26/README.md).

## Uso de IA en el desarrollo

Se utilizó asistencia de ChatGPT para revisión técnica, mejoras de seguridad, generación de pruebas y documentación. El desarrollador revisa, valida y decide qué cambios integrar.

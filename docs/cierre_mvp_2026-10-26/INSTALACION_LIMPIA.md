# CurriculAi — Bitácora de instalación limpia y validación funcional

**Fecha de ejecución:** 7 de noviembre de 2026
**Proyecto:** CurriculAi (prototipo académico)
**Plataforma:** Windows, PowerShell, Python 3.11
**Carpeta del clon:** `C:\prueba-limpia`
**Repositorio:** clon independiente de GitHub; no se copiaron el entorno virtual, `.env` ni la base de datos del proyecto original.
**Commit de referencia inicial:** `fac9ce2` (verificado tras la clonación)
**Commit de corrección publicado:** `9f9bbc8` (corrección de `EMBEDDINGS_MODEL` y dos pruebas de regresión)
**SHA del clon en la ejecución final de 52 pruebas:** **`9f9bbc8`**, confirmado mediante `git rev-parse --short HEAD` en `C:\prueba-limpia` después de la ejecución mostrada.

> **Alcance de la evidencia:** resultados observados en la terminal y capturas del recorrido manual. La aprobación de `pytest` por sí sola no certifica la precisión del ranking ni el funcionamiento real de servicios externos (Gemini, UltraMsg, Supabase o Tesseract).

## 1. Objetivo

Verificar que un clon independiente del repositorio pueda instalar dependencias, ejecutar pruebas automatizadas e iniciar el MVP de CurriculAi usando SQLite de prueba. Adicionalmente, comprobar manualmente el flujo de vacante, CV, ranking, postulación, entrevista, notificaciones y decisión final.

## 2. Procedimiento y observaciones

| Paso | Operación | Resultado observado |
|---|---|---|
| 1 | Clonación del repositorio en `C:\prueba-limpia` | Realizada; se verificó el commit inicial `fac9ce2` y `git status --short` sin cambios al terminar el clon. |
| 2 | Creación de entorno virtual Windows con Python 3.11 | Realizada usando `py -3.11 -m venv .venv`. Un intento inicial con `python` produjo un `venv` con estructura no adecuada para PowerShell. |
| 3 | Instalación con `pip install -r requirements.txt` | Instalación completada en el entorno `.venv`. |
| 4 | Ejecución automatizada inicial | **50 passed, 1 warning, 32.82 s** en el clon limpio. |
| 5 | Configuración privada | `.env` creado desde `.env.example`; SQLite configurada con `DATABASE_URL=sqlite:///./motor_cv.db`; credenciales administrativas generadas con `scripts/configurar_acceso.py`. No se publican valores privados. |
| 6 | Inicio de FastAPI | `Application startup complete` y servidor en `http://127.0.0.1:8000`. |
| 7 | Inicio de Streamlit | La interfaz administrativa abrió y mostró conexión activa. |
| 8 | Creación y publicación de vacante de ejemplo | Vacante ficticia «Auxiliar administrativo» creada y publicada. |
| 9 | Cuenta, CV y compartición | Se observó el portal del candidato con CV guardado y compartido con reclutamiento. |
| 10 | Evaluación semántica | La primera ejecución falló con `AttributeError`; se identificó `EMBEDDINGS_MODEL` vacía. Tras configurar explícitamente el modelo se observó «Evaluación terminada: 15 CV procesados» y el listado de resultados. |
| 11 | Postulación y avisos | Se observaron avisos de «Postulación recibida», «Entrevista programada» y «Avanzaste a entrevista». |
| 12 | Entrevista y finalista | La interfaz mostró una entrevista y una decisión de finalista registrada como «Aceptado». |
| 13 | Corrección permanente | Se publicó el commit `9f9bbc8` con el valor de ejemplo de `EMBEDDINGS_MODEL`, fallback de configuración vacía en `embeddings.py` y dos pruebas de regresión. |
| 14 | Pruebas automatizadas tras corrección, en proyecto principal | **52 passed, 1 warning, 45.02 s** (`C:\motorcv`). |
| 15 | Pruebas automatizadas tras actualización, en clon de prueba | **52 passed, 1 warning, 46.81 s** (`C:\prueba-limpia`), commit verificado `9f9bbc8`. |

## 3. Error encontrado y solución

**Síntoma:** `POST /api/v1/evaluar/1` devolvió HTTP 500; la interfaz indicó `Falló la evaluación semántica: AttributeError`.

**Diagnóstico:** el traceback de `embeddings.py` apuntaba a `SentenceTransformer(nombre)`. La variable `EMBEDDINGS_MODEL` existía, pero su valor estaba vacío, por lo que el programa intentaba iniciar el modelo con un identificador vacío. La carga directa del modelo `sentence-transformers/all-MiniLM-L6-v2` sí funcionó y produjo vectores de dimensión 384.

**Solución aplicada:** completar el valor de muestra en `.env.example` y usar en `embeddings.py` un valor alternativo cuando `EMBEDDINGS_MODEL` esté vacía o ausente. Se añadieron dos pruebas que verifican ambos casos. No fue necesario borrar la base de datos ni eliminar candidatos.

**Advertencia de biblioteca:** PyMuPDF emitió una advertencia de deprecación por `fitz`; la última ejecución de `pytest` terminó con una advertencia, sin fallos. Es una mejora futura; no debe confundirse con una prueba fallida.

## 4. Evidencia automatizada

Comando utilizado en la carpeta de prueba:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
```

Salida final observada:

```text
52 passed, 1 warning in 46.81s
```

**Nota:** el SHA `9f9bbc8` ya se confirmó. Para adjuntar también en el repositorio una evidencia textual exportada, se puede guardar desde el clon actualizado:

```powershell
cd C:\prueba-limpia
git rev-parse --short HEAD
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pytest -q tests 2>&1 | Tee-Object -FilePath .\resultado_pytest.txt
```

`resultado_pytest.txt` es una salida local; revisar su contenido antes de agregarlo al repositorio. Para documentar el resultado basta con registrar el resumen y el SHA en esta bitácora.

## 5. Evidencia visual y protección de datos

Se tomaron capturas del panel, Radar, portal del candidato, notificaciones, entrevistas y finalistas. **Antes de subir capturas al repositorio**, reemplazar nombres, correos, teléfonos y otros datos que identifiquen personas por datos totalmente ficticios o redactarlos de forma irreversible. No publicar `.env`, contraseñas, tokens, claves API ni bases SQLite.

**Ubicación sugerida para imágenes depuradas:** `docs/cierre_mvp_2026-10-26/evidencias/`.

| Evidencia sugerida | Estado |
|---|---|
| Terminal con resultados `52 passed` y SHA del clon | Ambas capturas observadas y SHA `9f9bbc8` confirmado; falta incorporar el registro al repositorio. |
| Panel administrativo y vacante de ejemplo | Capturas observadas; revisar anonimización antes de publicar. |
| Radar con evaluación terminada y 15 CV procesados | Captura observada; revisar anonimización antes de publicar. |
| Avisos de postulación y entrevista | Capturas observadas; revisar anonimización antes de publicar. |
| Entrevista y finalista aceptado | Capturas observadas; revisar anonimización antes de publicar. |

## 6. Pendientes para cierre de evaluación

- Incorporar al repositorio esta bitácora y, si corresponde, las capturas **anonimizadas**.
- Incorporar ejemplos de CV y vacantes enteramente ficticios en `datos_prueba/`, para que otra persona pueda repetir la demostración sin depender de datos creados manualmente en esta sesión.
- Probar Gemini con una cuenta autorizada y anotar qué modelo respondió, sin publicar credenciales.
- Confirmar la persistencia de los registros tras reiniciar ambos procesos, si el criterio de aceptación lo requiere.

**Conclusión acotada:** se demostró la instalación de dependencias, **52 pruebas automatizadas aprobadas en el clon del commit `9f9bbc8`** y un recorrido manual exitoso después de corregir la configuración del modelo semántico. Para que un evaluador independiente repita la demostración sin datos preexistentes todavía hay que agregar datos ficticios descargables y evidencias depuradas; las integraciones externas no se dan por verificadas.

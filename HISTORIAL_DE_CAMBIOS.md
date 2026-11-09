# Historial de cambios — CurriculAi

Este historial corresponde al **MVP de CurriculAi con dos accesos: administrador y candidato**. Se distinguen las versiones del producto, los resultados históricos y la validación vigente en un clon independiente. No se publican credenciales, datos reales de postulantes ni información confidencial. Las pruebas reproducibles y el recorrido manual no suponen aprobación de producción.

## Validación automatizada vigente — 7 de noviembre de 2026

- **Commit `9f9bbc8`**, publicado en `main`: corrección del valor por defecto de `EMBEDDINGS_MODEL` en `embeddings.py`, declaración en `.env.example` y dos pruebas de regresión.
- **Resultado en clon independiente `C:\prueba-limpia`, Python 3.11:** **52 pruebas aprobadas, 0 fallidas y 1 advertencia**, en **46.81 s**; SHA `9f9bbc8` confirmado con `git rev-parse --short HEAD`.
- **Resultado en `C:\motorcv` tras corregir el modelo:** 52 pruebas aprobadas, 0 fallidas y 1 advertencia en 45.02 s.
- **Recorrido manual observado:** aplicación iniciada con SQLite, vacante publicada, ranking real de 15 CV, postulación, notificaciones, entrevista y decisión final. Se documenta en [`INSTALACION_LIMPIA.md`](docs/cierre_mvp_2026-10-26/INSTALACION_LIMPIA.md), pendiente de incorporar al repositorio con este cambio documental.
- **Commits documentales previos:** `fac9ce2` unificó los archivos y retiró `MEJORAS_3_5.md`; el corte anterior de 50 pruebas (HEAD `c8db09a`, 36.68 s con dos advertencias) es **histórico**. Las cifras de 19, 25, 27 y 28 también son **históricas**.
- Las pruebas automatizadas simulan Gemini, embeddings y parte del OCR; no acreditan la integración real con Gemini, UltraMsg, Tesseract ni PostgreSQL/Supabase, y la demostración del ranking no constituye una evaluación de precisión.

## 4.0 — Portal del candidato (2 de noviembre de 2026)

- Se incorpora al alcance actual el portal del candidato con registro, inicio de sesión propio y token `Bearer`; el acceso administrativo conserva sus controles por `X-API-Key`.
- El candidato puede crear o subir su CV, modificar su expediente y **compartir explícitamente** su información con el área de reclutamiento.
- Se incorporan vacantes publicadas, postulaciones, entrevistas asociadas y notificaciones privadas; los controles por usuario evitan mostrar avisos y postulaciones ajenos.
- Se incluyen pruebas automatizadas del portal y del flujo candidato–reclutador. El recorrido manual de vacante a finalista ya se observó en el clon; falta evaluar con dos cuentas el aislamiento y publicar evidencias anonimizadas.
- **Commits señalados en la revisión 7:** `07b7fed` y `8b479c7`. **Verificar localmente con `git show` antes de dar por confirmada su relación exacta con esta versión.**

## 3.8 — Estabilidad y reproducibilidad (corte administrativo del 26 de octubre de 2026)

- Se evita mostrar una lista vacía cuando falla la consulta del ranking: respuesta HTTP 500 sin exponer información interna; Radar y Vacantes muestran el estado de error.
- Se valida mediante Pydantic el esquema de los mensajes de WhatsApp.
- Se mejora el manejo de errores transaccionales en actualización y eliminación de vacantes y entrevistas.
- Se alinean dependencias, configuración del modelo Gemini y evidencias documentales; se establece un plan de prueba de extremo a extremo con datos ficticios.
- **Resultados históricos de pruebas:** 27 aprobadas en una ejecución aislada preliminar; **28 aprobadas** en el corte administrativo 3.8 documentado en README/PRD/MVP anteriores. **Ninguna de estas cifras es el resultado vigente.**
- **Commits específicos de la versión 3.8:** deben cotejarse con `git log --since="2026-10-26 00:00" --until="2026-10-27 00:00" --oneline`. Los cuatro documentos proporcionados **no incluyen esos SHA**, por lo que no se inventan.

## 3.7 — Integración Gemini

- Actualización del SDK de generación y extracción para usar `google-genai`.
- Modelo configurable desde `.env` y descripción estructurada en el formulario de vacantes.
- Commit histórico: `56a8523` — `fix: actualizar Gemini y corregir generacion de vacantes`.
- Resultado histórico reportado por el desarrollador: **25 pruebas automatizadas aprobadas**.
- **Estado actual de la integración real:** el valor declarado `gemini-3.8-flash` todavía necesita evidencia de respuesta con una cuenta autorizada; no se afirma una prueba real aprobada.

## 3.6 — Documentación y criterios de aceptación

- `PRD.md` y `MVP.md` definen objetivos medibles, requisitos, alcance y escenarios de verificación.
- Commit histórico: `4306982` — `docs: definir PRD y MVP con criterios de aceptacion`.
- Se retiraron los borradores para evitar documentos contradictorios: commit `9fbb8d8`.

## 3.5 — Motor semántico

- Evaluación basada en experiencia, perfil y habilidades; se evitan campos administrativos y datos personales explícitos en los embeddings.
- Extracción de documentos separada, manejo de omisiones y pruebas sin datos reales.
- Commit histórico: `dd6f532` — `feat: optimizar motor IA y evaluacion curricular`.
- Resultado histórico: **19 pruebas automatizadas aprobadas**.

## 3.4 — Seguridad inicial

- Pantalla de acceso de administrador; rutas FastAPI protegidas por `X-API-Key`; generación local de credenciales con PBKDF2 y clave API.
- README e historial documentados en commit `829cfdb`; ejemplo de configuración añadido en commit `f773c19`.
- Este era el alcance original con **un solo administrador**; la versión 4.0 agrega el portal del candidato, **no** varias empresas ni administradores diferenciados.

## Alcance y limitaciones actuales

- CurriculAi es una herramienta de apoyo al reclutamiento; el resultado de IA es orientativo y la decisión corresponde a una persona autorizada.
- **Dentro del alcance ampliado:** portal de candidatos, sesiones independientes, CV manual/cargado, compartición, postulaciones y notificaciones privadas.
- **Fuera del alcance actual:** múltiples empresas y administradores con permisos distintos; múltiples entrevistas independientes por candidato, auditoría completa y despliegue público validado.
- **Entrega reproducible de referencia:** SQLite (`DATABASE_URL=sqlite:///./motor_cv.db`). PostgreSQL/Supabase es una opción, no un requisito del clon limpio; la configuración privada que usa el desarrollador no se ha comprobado aquí.
- **Pendientes de la revisión 7:** incorporar la bitácora de instalación limpia y evidencias depuradas al repositorio, agregar CV y vacantes totalmente ficticios a `datos_prueba/`, comprobar con cuenta autorizada qué modelo Gemini responde y completar la limpieza de parches obsoletos tras verificar que no se utilicen.
- Toda prueba o captura debe usar datos ficticios y no incluir `.env`, bases de datos privadas ni credenciales.

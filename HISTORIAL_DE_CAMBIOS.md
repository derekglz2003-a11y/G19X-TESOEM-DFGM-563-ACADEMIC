# Historial de cambios — CurriculAi

Este historial corresponde al **MVP de CurriculAi con dos accesos: administrador y candidato**. Se distinguen explícitamente las **versiones del producto**, los **resultados históricos** de pruebas y la **última comprobación local**. No se publican credenciales, datos reales de postulantes ni información confidencial. La aceptación final requiere una instalación limpia y pruebas manuales.

## Validación automatizada vigente — 7 de noviembre de 2026 (sin crear una versión nueva)

- **Resultado en `C:\motorcv`: 50 pruebas aprobadas, 0 fallidas y 2 advertencias**, en **36.68 s**.
- **HEAD local informado:** `c8db09a`; comando: `.\.venv\Scripts\python.exe -m pytest -q tests`.
- El árbol local tenía **archivos sin seguimiento**. Este resultado **no demuestra todavía** que un clon del commit `c8db09a` ejecute correctamente todo el flujo; falta el registro de instalación limpia.
- Las pruebas incluyen simulaciones de Gemini, embeddings y parte del OCR; la integración real con Gemini, UltraMsg, Tesseract y PostgreSQL/Supabase queda pendiente de verificación independiente.
- **Resultado vigente de referencia para README, PRD, MVP e historial: 50 pruebas aprobadas.** Las cifras de 19, 25, 27 y 28 que aparecen más abajo son **históricas**, con sus cortes correspondientes.

## 4.0 — Portal del candidato (2 de noviembre de 2026)

- Se incorpora al alcance actual el portal del candidato con registro, inicio de sesión propio y token `Bearer`; el acceso administrativo conserva sus controles por `X-API-Key`.
- El candidato puede crear o subir su CV, modificar su expediente y **compartir explícitamente** su información con el área de reclutamiento.
- Se incorporan vacantes publicadas, postulaciones, entrevistas asociadas y notificaciones privadas; los controles por usuario evitan mostrar avisos y postulaciones ajenos.
- Se incluyen pruebas automatizadas del portal y del flujo candidato–reclutador. La comprobación manual de extremo a extremo en instalación limpia sigue pendiente.
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
- **Pendientes de la revisión 7:** evidencia de instalación limpia, CV y vacantes ficticios en `datos_prueba/`, comprobación real del modelo Gemini y su configuración uniforme, además de retirar referencias y archivos de parches obsoletos del repositorio, después de confirmar que ya no sean necesarios.
- Toda prueba o captura debe usar datos ficticios y no incluir `.env`, bases de datos privadas ni credenciales.

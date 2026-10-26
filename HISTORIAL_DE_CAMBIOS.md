# Historial de cambios — CurriculAi

Este documento resume las versiones del **MVP administrativo**. Los commits siguientes corresponden a cambios ya registrados; la versión 3.8 se registrará después de instalar y ejecutar pruebas en el equipo del desarrollador. No contiene secretos, datos de candidatos ni instrucciones de copiar ZIP sobre una base de datos.

## 3.8 — Estabilidad y reproducibilidad (por publicar)
- Se evita mostrar una lista vacía cuando falla la consulta del ranking: respuesta HTTP 500 sin exponer información interna; Radar y Vacantes muestran el estado de error.
- Se valida mediante Pydantic el esquema de los mensajes de WhatsApp.
- Se mejora el manejo de errores transaccionales en actualización y eliminación de vacantes y entrevistas.
- Se alinean dependencias, el modelo Gemini y las evidencias documentales; se prepara un plan de prueba E2E con datos ficticios.
- Resultado de pruebas en entorno aislado: **27 aprobadas**; pendiente repetirlas en Windows y conservar la captura del terminal.

## 3.7 — Integración Gemini
- Actualización del SDK de generación y extracción para usar `google-genai`.
- Modelo configurable desde `.env` y descripción estructurada en el formulario de vacantes.
- Commit: `56a8523` — `fix: actualizar Gemini y corregir generacion de vacantes`.
- Resultado reportado por el desarrollador: **25 pruebas automatizadas aprobadas**.

## 3.6 — Documentación y criterios de aceptación
- `PRD.md` y `MVP.md` definen objetivos medibles, requisitos, alcance y escenarios de verificación.
- Commit: `4306982` — `docs: definir PRD y MVP con criterios de aceptacion`.
- Se retiraron los borradores para evitar documentos contradictorios: commit `9fbb8d8`.

## 3.5 — Motor semántico
- Evaluación basada en experiencia, perfil y habilidades; se evitan campos administrativos y datos personales explícitos en los embeddings.
- Extracción de documentos separada, manejo de omisiones y pruebas sin datos reales.
- Commit: `dd6f532` — `feat: optimizar motor IA y evaluacion curricular`.
- Resultado histórico: **19 pruebas automatizadas aprobadas**.

## 3.4 — Seguridad inicial
- Pantalla de acceso de administrador; rutas FastAPI protegidas por `X-API-Key`; generación local de credenciales PBKDF2 y API Key.
- README e historial documentados en commit `829cfdb`; ejemplo de configuración añadido en commit `f773c19`.
- La autenticación actual es para un administrador de prototipo, no un despliegue público multiusuario.

## Alcance y limitaciones
- CurriculAi es una herramienta de apoyo al reclutamiento. El resultado de IA es orientativo y requiere revisión humana.
- El portal de candidatos y el control de acceso por roles están fuera del MVP administrativo actual.
- Para evidencias usar exclusivamente CV y nombres ficticios. Mantener `.env` y bases de datos fuera de Git.

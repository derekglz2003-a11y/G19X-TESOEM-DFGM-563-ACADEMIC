# PRD — CurriculAi

**Nombre del producto:** CurriculAi — Optimizador de filtrado curricular mediante IA
**Versión del documento:** 2.1 · coherencia documental de la revisión 7
**Fecha de referencia:** 7 de noviembre de 2026; versiones administrativas anteriores conservadas como antecedentes
**Estado:** Propuesta para revisión académica y validación funcional, no aprobación de producción
**Responsable:** Desarrollo del proyecto CurriculAi
**Documento complementario:** [`MVP.md`](MVP.md)

> **Alcance de este PRD:** especifica el producto, las funciones existentes y los compromisos de verificación propuestos. Incluye el portal de candidatos en el alcance actual (integración indicada en la revisión 7). No acredita por sí mismo la calidad del ranking con CV reales, el funcionamiento de servicios externos ni un despliegue de producción. No contiene información identificable de clientes, empresas receptoras o postulantes.

## 1. Resumen ejecutivo

CurriculAi es una aplicación de asistencia al reclutamiento que centraliza vacantes, expedientes curriculares, evaluaciones semánticas, entrevistas, decisiones de selección y registros de mensajes. El MVP administrativo original atiende a **un administrador de reclutamiento**; el alcance vigente incorpora un **portal de candidatos**, donde pueden registrar una cuenta, crear o cargar su CV, compartirlo voluntariamente, consultar vacantes publicadas y seguir postulaciones y avisos. Ambos utilizan Streamlit, FastAPI y una base de datos configurada mediante variables de entorno.

El motor inteligente compara el texto profesional de una vacante con **perfil, experiencia y habilidades** de los candidatos. Devuelve un porcentaje de **similitud textual orientativo**, una explicación y el número de expedientes excluidos por información insuficiente. **No determina por sí solo si una persona debe ser contratada.**

La versión actual utiliza `sentence-transformers` para el análisis semántico; Gemini es una integración opcional para generar descripciones de puestos y extraer datos de CV, y UltraMsg es opcional para enviar invitaciones por WhatsApp. La revisión y la decisión corresponden a una persona autorizada.

## 2. Problema que buscamos resolver

Cuando las vacantes, los currículums y las entrevistas se administran mediante archivos o canales separados, el responsable de reclutamiento debe localizar documentos, comparar manualmente perfiles, recordar en qué etapa se encuentra cada persona y repetir información entre herramientas. Esto dificulta consultar el estado de una vacante y justificar por qué un candidato pasó a la siguiente etapa.

**Necesidad:** disponer de un flujo unificado para registrar vacantes, organizar CV, obtener una comparación inicial explicable, actualizar el seguimiento y programar entrevistas, **sin delegar automáticamente las decisiones laborales a una IA**.

Esta necesidad es la hipótesis de producto; el ahorro de tiempo y la utilidad efectiva del ranking se deben medir con una prueba de usuarios y datos ficticios antes de afirmarlos como beneficios logrados.

## 3. Usuarios y actores

| Actor | Necesidad | Acceso en la versión ampliada |
|---|---|---|
| Administrador de reclutamiento (usuario principal) | Gestionar vacantes, CV, ranking, entrevistas y estados | **Implementado:** una cuenta administrativa de acceso al panel |
| Postulante / candidato (persona cuyos datos se gestionan) | Mantener su perfil, compartir CV y consultar procesos propios | **Implementado:** registro, sesión propia, CV manual/cargado, vacantes publicadas, postulación, entrevistas y notificaciones privadas |
| Evaluador académico o de calidad | Comprobar requisitos, instalación y pruebas | Acceso por repositorio, documentación y ejecución con datos ficticios; **no debe acceder a CV reales** |
| Proveedor externo de servicios | Ofrecer almacenamiento remoto, generación de texto o mensajería | Integración técnica, no usuario con acceso autónomo al panel |

**Decisión de alcance actualizada:** existen **dos tipos de acceso**: administrador con `X-API-Key` en API y candidato autenticado con sesión `Bearer` en `/portal`. Esto **no** incluye múltiples empresas ni diferentes cuentas administrativas con permisos distintos.

## 4. Propuesta de valor

- Consultar vacantes y expedientes en un mismo entorno, con búsqueda, filtros y paginación.
- Obtener una primera aproximación de compatibilidad basada en información laboral y revisarla de forma explícita.
- Conservar los resultados del análisis por vacante y actualizar el estado de los perfiles mediante acciones del administrador.
- Programar, modificar o cancelar entrevistas y consultar decisiones de finalistas.
- Registrar las solicitudes de envío y respuestas de mensajería cuando se configure el proveedor.
- Mantener un código modular y pruebas automatizadas reproducibles en una base aislada.

## 5. Objetivos medibles propuestos

Las metas siguientes son **criterios para evaluar el MVP, no métricas de rendimiento ya demostradas**. Se medirán con expedientes **ficticios o anonimizados para prueba**, sin usar datos reales de candidatos.

| ID | Objetivo | Meta de aceptación propuesta | Cómo se mide |
|---|---|---|---|
| OBJ-01 | Completar el proceso administrativo de extremo a extremo | Ejecutar **5 de 5** escenarios de vacante → CV → ranking → seguimiento → entrevista/decisión sin bloqueos | Lista de verificación E2E documentada en `MVP.md`, ambiente de prueba |
| OBJ-02 | Asegurar una extracción controlada de documentos | Obtener texto laboral utilizable en **al menos 18 de 20** CV ficticios legibles de los formatos admitidos; registrar por separado casos de OCR | Dataset de prueba definido, revisión manual de texto extraído y registro de errores; **meta, no resultado** |
| OBJ-03 | Mantener resultados explicables y evitar influencia directa de atributos protegidos | En **100 %** de las pruebas de insumo del motor, excluir campos administrativos explícitos (nombre, edad, sexo, teléfono, correo y CV íntegro) y presentar justificación/omitidos | Pruebas del módulo `servicios/perfil_laboral.py`, inspección del ranking y revisión humana |
| OBJ-04 | Verificar controles de acceso | **100 %** de las rutas administrativas protegidas probadas sin clave válida deben denegar acceso y **0** secretos reales deben figurar en Git | Pruebas negativas de API, búsqueda de secretos y `git status` / `.gitignore` |
| OBJ-05 | Demostrar reproducibilidad técnica | Una instalación limpia con instrucciones debe ejecutar el sistema y completar **la totalidad de las pruebas automatizadas del repositorio** (52 verificadas en clon independiente del commit `9f9bbc8`), o documentar las diferencias de entorno | Ejecución de `pytest`, evidencia del entorno, README y [`INSTALACION_LIMPIA.md`](docs/cierre_mvp_2026-10-26/INSTALACION_LIMPIA.md) |

**Pendientes de medición:** tiempos reales de análisis, pertinencia de resultados, tasa de errores de OCR con Tesseract real, eficacia de las recomendaciones, latencia de servicios externos, seguridad en despliegue público y pruebas de sesgos. No deben presentarse como aprobados sin evidencia.

## 6. Alcance funcional

### 6.1 Incluido en el MVP administrativo

1. Inicio de sesión de **un administrador** y protección por clave privada de las rutas operativas del backend.
2. Panel inicial con indicadores de vacantes, candidatos, entrevistas y finalistas.
3. Alta, consulta, edición y eliminación controlada de vacantes.
4. Carga múltiple de CV con extracción de texto para PDF, DOCX, TXT e imágenes PNG, JPG, JPEG y WEBP. OCR dependiente de Tesseract en imágenes y algunos PDF escaneados; límite actual por archivo: **15 MB**.
5. Consulta, búsqueda, edición, seguimiento y eliminación controlada de expedientes o solo de sus CV.
6. Evaluación semántica por vacante con embeddings, persistencia de puntuación y explicación, y aviso de registros omitidos por información profesional insuficiente.
7. Consulta del ranking en Radar y acceso desde Vacantes a decisiones y agenda.
8. Registro, edición, estado y cancelación/eliminación de entrevistas.
9. Selección de finalistas, aceptación, rechazo o retiro de la etapa final, bajo criterio humano.
10. Bitácora de WhatsApp; envío automático únicamente si UltraMsg está configurado y disponible.
11. Generación asistida de la descripción de una vacante únicamente si Gemini está configurado y responde.
12. Configuración básica, reinicio de vista y cierre de sesión; tareas destructivas con confirmación.

### 6.2 Portal del candidato incorporado al alcance actual

1. Registro e inicio de sesión propios; perfil laboral privado.
2. Generación manual de CV y carga de documento, con corrección posterior.
3. Compartición **explícita** de CV con reclutamiento; vínculo único a un expediente administrativo evaluable, sin necesitar postularse primero.
4. Publicación voluntaria de vacantes por el administrador, consulta y postulación por el candidato.
5. Seguimiento de postulaciones, entrevistas asociadas y notificaciones persistentes privadas.
6. Invitaciones del reclutador a revisar vacantes, sin prometer selección ni contratación.

### 6.3 Fuera de alcance / pendientes

- Sistema multiempresa y varias cuentas de reclutadores con permisos diferenciados.
- Publicación anónima sin cuenta, firma de contratos o contratación automática.
- Aprobación/rechazo laboral **automático** por puntuación.
- Verificación independiente de veracidad de los CV o certificación de ausencia de sesgos.
- Envíos garantizados, lectura confirmada o entrega final de WhatsApp sin verificación del proveedor.
- Despliegue de producción con auditoría completa, cifrado extremo a extremo y política aprobada de retención y supresión de datos.
- Conversión nativa del formato Word binario `.doc`: se requiere convertirlo a DOCX o PDF.

## 7. Requisitos funcionales (RF)

**Estados:** `Implementado` significa que existe una ruta o interfaz en la versión de código de referencia, no que haya sido validada en producción. `Opcional` requiere servicio o credencial externa. `Pendiente` está fuera del MVP actual.

| ID | Requisito comprobable | Prioridad | Estado y evidencia técnica |
|---|---|---|---|
| RF-01 | Restringir la interfaz a un administrador autenticado y proteger las rutas operativas mediante `X-API-Key` | P0 | Implementado; `app.py`, `servicios/seguridad.py`, `main.py` |
| RF-02 | Registrar, visualizar, editar y eliminar vacantes | P0 | Implementado; rutas `/api/v1/vacantes` y `paginas/vacantes.py` |
| RF-03 | Importar múltiples CV de tipos admitidos y explicar por archivo los fallos de extracción | P0 | Implementado; `/api/v1/analizar-cvs-masivo` y `servicios/extractores_cv.py` |
| RF-04 | Consultar, buscar y editar información curricular; eliminar CV o expediente con confirmación | P0 | Implementado; `paginas/candidatos.py` y API de candidatos |
| RF-05 | Calcular el ranking mediante perfil/experiencia/habilidades sin usar directamente campos demográficos ni CV íntegro | P0 | Implementado; `servicios/perfil_laboral.py`, `embeddings.py`, `/api/v1/evaluar/{vacante_id}` |
| RF-06 | Guardar o actualizar una evaluación por candidato y vacante; invalidar resultados antiguos sin perfil laboral | P0 | Implementado; entidad `Evaluacion`, `main.py`; integridad por escenario a comprobar |
| RF-07 | Mostrar puntuación, explicación y cantidad de candidatos omitidos; exigir revisión humana | P0 | Implementado; `/api/v1/ranking/{vacante_id}`, `paginas/radar.py` y Vacantes |
| RF-08 | Mantener estado de candidato por vacante | P0 | Implementado; entidad `Seguimiento`, API de seguimientos |
| RF-09 | Agendar, editar y cancelar/eliminar entrevistas | P0 | Implementado; entidad `Entrevista`, `paginas/entrevistas.py` |
| RF-10 | Marcar finalista, aceptar, rechazar o retirar de esa etapa | P0 | Implementado; rutas de decisión y `paginas/finalistas.py` |
| RF-11 | Registrar envíos de WhatsApp con estado de respuesta del proveedor; no afirmar entrega sin verificación | P1 | Bitácora implementada; envío condicionado a UltraMsg |
| RF-12 | Generar borradores de descripción de puestos con IA y permitir revisión antes de guardarlos | P1 | Integración implementada; depende de `GEMINI_API_KEY` válida |
| RF-13 | Mostrar errores legibles cuando no hay conexión, faltan credenciales o un formato es incompatible | P0 | Rutas y controles presentes; validación integral pendiente |
| RF-14 | Proporcionar documentación, variables de entorno de ejemplo y ejecución de pruebas con datos aislados | P0 | `README.md`, `.env.example`, `tests/` y documentos 3.6 |
| RF-15 | Permitir al candidato registrarse y consultar su propio proceso | P0 (portal) | **Implementado:** `servicios/portal_auth.py`, `servicios/portal_expediente.py`, `servicios/portal_oportunidades.py` y pruebas del portal; validar manualmente sobre el commit final |
| RF-16 | Registrar múltiples administradores y gestionar permisos por empresa | P2 | **Pendiente:** existe un acceso administrativo, no un sistema multiempresa o de reclutadores independientes |
| RF-17 | Crear/actualizar CV manual o importar archivo desde la cuenta personal | P0 (portal) | Implementado; `servicios/portal_expediente.py` y `tests/test_cv_manual_portal.py` |
| RF-18 | Compartir CV con consentimiento e incorporarlo sin duplicar al pool de ranking | P0 (portal) | Implementado; `portal_candidato_vinculos`, rutas de compartición y pruebas de flujo |
| RF-19 | Publicar vacantes expresamente y admitir una postulación por candidato/vacante | P0 (portal) | Implementado; `servicios/portal_oportunidades.py` y pruebas de postulaciones |
| RF-20 | Mostrar solo postulaciones y avisos propios; informar etapas y entrevistas vinculadas | P0 (portal) | Implementado; sesiones Bearer, validación del dueño y prueba de aislamiento; despliegue público no validado |
| RF-21 | Permitir invitación desde la evaluación y aviso interno sin prometer contratación | P1 (portal) | Implementado; ruta `/api/v1/invitaciones/{vacante_id}/{candidato_id}`; verificar en UI con cuenta ficticia |

## 8. Requisitos no funcionales (RNF)

| ID | Requisito / meta | Verificación | Situación actual |
|---|---|---|---|
| RNF-01 Seguridad | Denegar rutas administrativas sin `X-API-Key` válida y rutas privadas del portal sin sesión `Bearer` válida; evitar secretos en el repositorio | Pruebas negativas de API, revisión de `.env` y `.gitignore` | Protección básica implementada; no implica seguridad de producción |
| RNF-02 Privacidad | Limitar campos usados por el embedding a perfil, experiencia y habilidades; no compartir CV reales en código o evidencias públicas | Pruebas unitarias, revisión del insumo y repositorio | Medida técnica implementada; anonimización total **no garantizada** |
| RNF-03 Trazabilidad | Conservar estado por vacante y justificación de evaluaciones | Pruebas API y revisión en UI | Flujo funcional implementado; auditoría de modificaciones completa pendiente |
| RNF-04 Reproducibilidad | Instalar desde el repositorio y ejecutar pruebas sin una conexión remota real | README, `.env.example` y base aislada | **52 pruebas aprobadas y 1 advertencia** en clon Windows con Python 3.11, commit `9f9bbc8`, el 7-nov-2026; FastAPI, Streamlit y recorrido manual demostrados. Las 28 del corte 3.8 son históricas |
| RNF-05 Usabilidad | Buscar expedientes y vacantes sin recorrer listados extensos; menú usable en escritorio | Pruebas manuales a resolución definida y registro de incidencias | Búsqueda, selección y paginación implementadas; prueba formal de usabilidad pendiente |
| RNF-06 Resiliencia | Explicar formatos inválidos y fallos de OCR / servicios externos sin fabricar resultados | Pruebas negativas y revisión de mensajes | Manejo parcial implementado; evaluación de errores de producción pendiente |
| RNF-07 Portabilidad | Ejecutar en Windows con Python 3.11 recomendado y **SQLite como base de referencia de la entrega**; PostgreSQL/Supabase opcional mediante `DATABASE_URL` | Instalación documentada en máquina limpia | Clon independiente Windows/Python 3.11 ejecutado con SQLite de prueba (commit `9f9bbc8`); la configuración privada del proyecto principal no se ha inspeccionado |
| RNF-08 Calidad de resultados | Alcanzar OBJ-02 y demostrar pertinencia de rankings en casos de prueba | Corpus ficticio con revisión humana | **Pendiente: no hay validación de precisión con datos reales** |
| RNF-09 Rendimiento | Medir tiempo de carga y evaluación de 20 expedientes ficticios con modelo ya descargado | Cronometraje repetido, especificaciones de equipo y entorno | **Meta de medición futura; no se afirma tiempo** |
| RNF-10 Conservación de datos | Definir y aprobar consentimiento/base de tratamiento, plazo de retención, acceso, respaldo y eliminación | Política documentada y casos de prueba | **Pendiente antes de uso real en producción** |

**Privacidad y uso responsable:** los CV contienen datos personales. Aunque el ranking no concatena directamente nombre, edad, sexo, correo o teléfono, los campos libres pueden contener información identificable. El proyecto requiere supervisión humana, un conjunto de pruebas representativo, revisión de sesgos y políticas de tratamiento antes de un despliegue público.

## 9. Arquitectura de alto nivel

```text
Administrador autorizado
         |
         v
Streamlit (app.py + paginas/)
         |
         | HTTP con X-API-Key en solicitudes operativas
         v
FastAPI (main.py)
         |
         +--> servicios/extractores_cv.py (PDF/DOCX/TXT/OCR)
         +--> servicios/perfil_laboral.py (insumo laboral)
         +--> embeddings.py (similitud semántica)
         +--> parser.py (resumen y explicación)
         +--> Gemini [opcional: extracción/descr. puesto]
         +--> UltraMsg [opcional: mensajería]
         |
         +--> Portal candidato (/portal): cuenta, expediente, publicaciones, postulaciones y avisos
         |
         v
SQLAlchemy (database.py)
         +--> SQLite local [referencia de la entrega: sqlite:///./motor_cv.db]
         +--> PostgreSQL / Supabase [opcional, al cambiar DATABASE_URL]
```

Las credenciales se leen de `.env` y **no** deben aparecer en GitHub ni documentos de entrega. Para una entrega reproducible se documenta **SQLite** (`DATABASE_URL=sqlite:///./motor_cv.db`, valor de referencia citado en la revisión). PostgreSQL/Supabase queda como **opción**. No se puede afirmar qué motor utiliza el `.env` privado del desarrollador sin inspeccionarlo localmente; la base local y remota no se sincronizan automáticamente.

## 10. Recorridos principales (historias de usuario)

**HU-01 — Crear vacante.** Como administrador quiero registrar una descripción clara del puesto para comparar expedientes con requisitos laborales definidos.
**HU-02 — Procesar CV.** Como administrador quiero cargar varios CV y revisar errores individuales para no inventar información faltante.
**HU-03 — Comparar perfiles.** Como administrador quiero observar un ranking explicable, junto con perfiles omitidos, para priorizar una revisión humana.
**HU-04 — Gestionar etapas.** Como administrador quiero identificar el estado de cada persona por vacante para mantener un seguimiento coherente.
**HU-05 — Entrevistar.** Como administrador quiero agendar y cambiar una cita para coordinar con cada postulante.
**HU-06 — Tomar decisión.** Como administrador quiero marcar finalistas y aceptar, rechazar o retirar perfiles, de manera deliberada y trazable.
**HU-07 — Resguardar información.** Como administrador quiero que las rutas estén protegidas y evitar publicar datos privados accidentalmente.

**HU-08 — Crear y compartir CV.** Como candidato quiero generar o cargar mi CV, editarlo y autorizar su compartición antes de entrar al pool del administrador.
**HU-09 — Postularme.** Como candidato quiero consultar vacantes publicadas y enviar una solicitud una sola vez por puesto.
**HU-10 — Conocer avances.** Como candidato quiero consultar mis entrevistas, etapas y notificaciones sin ver información de otras cuentas.

Los casos de aceptación verificables para estas historias están en `MVP.md`.

## 11. Dependencias, restricciones y riesgos

| Riesgo / restricción | Efecto posible | Mitigación o decisión |
|---|---|---|
| CV escaneados o con formatos complejos | Texto incompleto, candidatos omitidos | OCR, control de errores, revisión manual; PDF escaneado limitado a tres páginas en fallback |
| Extracción generativa no confiable | Datos inventados u omitidos | Fallback local, edición manual de expedientes, validación con corpus ficticio |
| Puntaje semántico mal interpretado | Exclusión injustificada | Etiquetar como similitud orientativa, mostrar explicación, decisión humana |
| Embeddings en otro idioma | Variación en los puntajes | Validar corpus en español; modelo multilingüe opcional no asumido equivalente |
| Integraciones opcionales inactivas | Descripciones/WhatsApp no disponibles | Mostrar error o estado, mantener el flujo principal sin ellas |
| Seguridad insuficiente para Internet | Exposición de información personal | Uso académico restringido; HTTPS, roles, auditoría y retención antes de producción |
| Base de datos remota accidentalmente utilizada en pruebas | Cambios a datos reales | Dataset ficticio y `DATABASE_URL` de pruebas aislada, respaldo previo |
| Restricción actual: una entrevista por candidato | Limita varios procesos simultáneos | Documentar y rediseñar modelo de entrevistas en iteración posterior |

## 12. Plan de validación y aceptación

1. Resultado vigente del **clon independiente Windows/Python 3.11**, commit `9f9bbc8`: `.\.venv\Scripts\python.exe -m pytest -q tests`, **52 aprobadas, 0 fallidas y 1 advertencia**, **7-nov-2026**, **46.81 s**. El flujo administrativo y del candidato se ejercitó manualmente con SQLite en `C:\prueba-limpia`. Registrar en la entrega la bitácora [`INSTALACION_LIMPIA.md`](docs/cierre_mvp_2026-10-26/INSTALACION_LIMPIA.md). Las 28 pruebas del corte administrativo 3.8 son históricas.
2. Ejecutar el recorrido manual E2E con una vacante y CV ficticios, **sin utilizar credenciales reales de postulantes**.
3. Verificar autenticación, lectura prohibida sin clave, edición y eliminaciones solo en datos de prueba.
4. Ejecutar un escenario con CV profesional válido, uno genérico, uno DOCX con tablas y uno `.doc` heredado; registrar resultado observado.
5. Validar puntuación/justificación en Radar y decisión humana explícita.
6. Comprobar funciones opcionales (Gemini, UltraMsg, Supabase) **solo en un entorno autorizado y separado**, si se dispone de sus credenciales.
7. Guardar evidencias: capturas sin datos personales, comando, resultado esperado/obtenido y referencia de commit.

**Criterio de cierre del MVP:** aprobar todos los criterios **P0** descritos en `MVP.md` y documentar sin ocultar los casos fallidos. Las metas OBJ-01 a OBJ-05 deben tener resultado medido; hasta entonces su estado es **propuesto**. Las **52 pruebas automatizadas y la demostración manual realizadas** no sustituyen la validación de pertinencia, pruebas reales de Gemini/OCR/mensajería ni la entrega de datos ficticios y evidencias despersonalizadas.

**Trazabilidad vigente (7-nov-2026):** **52 aprobadas, 0 fallidas, 1 advertencia**, en `C:\prueba-limpia` con commit **`9f9bbc8`** y Python 3.11; bitácora de recorrido E2E disponible para incorporar al repositorio. Anteriormente se aprobaron 50 en la instalación local, HEAD `c8db09a`, resultado **histórico**. El valor declarado para Gemini `gemini-3.8-flash` **no está validado por una respuesta real**: modelo efectivo por comprobar y alinear con `.env.example`, el servicio y el README.

## 13. Roadmap después del MVP

- **Consolidación de lo implementado:** conservar la evidencia del clon limpio ya probado; verificar además la persistencia tras reiniciar los servidores y publicar datos de demostración ficticios, sin extender nuevas funcionalidades.
- **Siguiente mejora técnica:** asociación de múltiples entrevistas y vacantes por candidato, historial de cambios por administrador y borrados auditables.
- **Privacidad/seguridad:** revisión legal, política de retención y consentimiento aplicable, HTTPS, autorización por roles, limitación de intentos y auditoría.
- **Evaluación de calidad:** corpus de CV ficticios representativos, revisión humana de pertinencia, estudio de resultados por subgrupos sin uso de datos personales sensibles en el ranking.
- **Operación:** métricas de tiempo de procesamiento, procedimientos de respaldo/restauración y monitorización de fallos externos.

## 14. Decisiones por validar

1. Aprobación académica de los objetivos medibles (OBJ-01 a OBJ-05) y del alcance ampliado a administrador + candidato.
2. Responsable autorizado de los expedientes, finalidad y plazo de conservación de CV.
3. Política de credenciales y requisitos de despliegue cuando el sistema deje de ser prototipo local.
4. Reglas de comunicación con candidatos y cómo se informarán los cambios en postulaciones, incluidas invitaciones y decisiones.
5. Conjunto y método de evaluación de pertinencia del ranking para CV redactados en español.

---

**Regla de documentación:** en cada actualización del repositorio, distinguir `Implementado`, `Probado`, `Validado manualmente`, `Pendiente` y `Fuera de alcance`. No declarar una métrica como lograda sin salida de prueba o evidencia reproducible.

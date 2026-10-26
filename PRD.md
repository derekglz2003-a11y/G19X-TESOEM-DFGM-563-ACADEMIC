# PRD — CurriculAi

**Nombre del producto:** CurriculAi — Optimizador de filtrado curricular mediante IA
**Versión del documento:** 1.0 · CurriculAi 3.6 (documentación del MVP 3.5)
**Fecha de referencia:** 21 de octubre de 2026
**Estado:** Propuesta para revisión académica y validación funcional, no aprobación de producción
**Responsable:** Desarrollo del proyecto CurriculAi
**Documento complementario:** [`MVP.md`](MVP.md)

> **Alcance de este PRD:** especifica el producto, las funciones existentes y los compromisos de verificación propuestos. Se basa en el código de CurriculAi 3.5. No acredita por sí mismo la calidad del ranking con CV reales, el funcionamiento de servicios externos ni un despliegue de producción. No contiene información identificable de clientes, empresas receptoras o postulantes.

## 1. Resumen ejecutivo

CurriculAi es una aplicación de asistencia al reclutamiento que centraliza vacantes, expedientes curriculares, evaluaciones semánticas, entrevistas, decisiones de selección y registros de mensajes. Su primer producto mínimo viable (MVP) está dirigido a **un administrador de reclutamiento** que utiliza un panel de Streamlit conectado a una API FastAPI y a una base de datos configurada mediante variables de entorno.

El motor inteligente compara el texto profesional de una vacante con **perfil, experiencia y habilidades** de los candidatos. Devuelve un porcentaje de **similitud textual orientativo**, una explicación y el número de expedientes excluidos por información insuficiente. **No determina por sí solo si una persona debe ser contratada.**

La versión actual utiliza `sentence-transformers` para el análisis semántico; Gemini es una integración opcional para generar descripciones de puestos y extraer datos de CV, y UltraMsg es opcional para enviar invitaciones por WhatsApp. La revisión y la decisión corresponden a una persona autorizada.

## 2. Problema que buscamos resolver

Cuando las vacantes, los currículums y las entrevistas se administran mediante archivos o canales separados, el responsable de reclutamiento debe localizar documentos, comparar manualmente perfiles, recordar en qué etapa se encuentra cada persona y repetir información entre herramientas. Esto dificulta consultar el estado de una vacante y justificar por qué un candidato pasó a la siguiente etapa.

**Necesidad:** disponer de un flujo unificado para registrar vacantes, organizar CV, obtener una comparación inicial explicable, actualizar el seguimiento y programar entrevistas, **sin delegar automáticamente las decisiones laborales a una IA**.

Esta necesidad es la hipótesis de producto; el ahorro de tiempo y la utilidad efectiva del ranking se deben medir con una prueba de usuarios y datos ficticios antes de afirmarlos como beneficios logrados.

## 3. Usuarios y actores

| Actor | Necesidad | Acceso en la versión 3.5 |
|---|---|---|
| Administrador de reclutamiento (usuario principal) | Gestionar vacantes, CV, ranking, entrevistas y estados | **Implementado:** una cuenta administrativa de acceso al panel |
| Postulante / candidato (persona cuyos datos se gestionan) | Proporcionar CV y conocer el estado de su proceso | **No implementado:** no dispone de un portal ni credenciales propias |
| Evaluador académico o de calidad | Comprobar requisitos, instalación y pruebas | Acceso por repositorio, documentación y ejecución con datos ficticios; **no debe acceder a CV reales** |
| Proveedor externo de servicios | Ofrecer almacenamiento remoto, generación de texto o mensajería | Integración técnica, no usuario con acceso autónomo al panel |

**Decisión de alcance:** el rol de candidato se propone para una fase posterior. El MVP evaluable no debe anunciar acceso individual de postulantes ni autorización por roles múltiples.

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
| OBJ-04 | Verificar controles de acceso | **100 %** de las rutas operativas probadas sin clave válida deben denegar acceso y **0** secretos reales deben figurar en Git | Pruebas negativas de API, búsqueda de secretos y `git status` / `.gitignore` |
| OBJ-05 | Demostrar reproducibilidad técnica | Una instalación limpia con instrucciones debe ejecutar el sistema y completar **la totalidad de las pruebas automatizadas del repositorio** (27 incluidas en el corte 3.8), o documentar las diferencias de entorno | Ejecución de `pytest`, evidencia del entorno, README e informe de instalación |

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

### 6.2 Fuera del MVP actual

- Portal público de candidatos, autoservicio, registro de cuentas y autenticación del postulante.
- Sistema multiempresa, cuentas de reclutadores múltiples y autorización por roles.
- Publicación pública de vacantes, postulación externa o firma de contratos.
- Aprobación/rechazo laboral **automático** por puntuación.
- Verificación independiente de veracidad de los CV o certificación de ausencia de sesgos.
- Envíos garantizados, lectura confirmada o entrega final de WhatsApp sin verificación del proveedor.
- Despliegue de producción con auditoría completa, cifrado extremo a extremo y política aprobada de retención y supresión de datos.
- Conversión nativa del formato Word binario `.doc`: se requiere convertirlo a DOCX o PDF.

## 7. Requisitos funcionales (RF)

**Estados:** `Implementado` significa que existe una ruta o interfaz en el código 3.5, no que haya sido validada en producción. `Opcional` requiere servicio o credencial externa. `Pendiente` está fuera del MVP actual.

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
| RF-15 | Permitir al candidato registrarse y consultar su propio proceso | P2 | **Pendiente — fuera del MVP administrativo** |
| RF-16 | Registrar múltiples administradores y gestionar permisos por rol | P2 | **Pendiente — fuera del MVP administrativo** |

## 8. Requisitos no funcionales (RNF)

| ID | Requisito / meta | Verificación | Situación actual |
|---|---|---|---|
| RNF-01 Seguridad | Denegar rutas operativas sin clave válida y evitar secretos en el repositorio | Pruebas negativas de API, revisión de `.env` y `.gitignore` | Protección básica implementada; no implica seguridad de producción |
| RNF-02 Privacidad | Limitar campos usados por el embedding a perfil, experiencia y habilidades; no compartir CV reales en código o evidencias públicas | Pruebas unitarias, revisión del insumo y repositorio | Medida técnica implementada; anonimización total **no garantizada** |
| RNF-03 Trazabilidad | Conservar estado por vacante y justificación de evaluaciones | Pruebas API y revisión en UI | Flujo funcional implementado; auditoría de modificaciones completa pendiente |
| RNF-04 Reproducibilidad | Instalar desde el repositorio y ejecutar pruebas sin una conexión remota real | README, `.env.example` y base aislada | 28 pruebas automatizadas aprobadas en una base aislada durante el corte 3.8; falta repetir la instalación desde cero |
| RNF-05 Usabilidad | Buscar expedientes y vacantes sin recorrer listados extensos; menú usable en escritorio | Pruebas manuales a resolución definida y registro de incidencias | Búsqueda, selección y paginación implementadas; prueba formal de usabilidad pendiente |
| RNF-06 Resiliencia | Explicar formatos inválidos y fallos de OCR / servicios externos sin fabricar resultados | Pruebas negativas y revisión de mensajes | Manejo parcial implementado; evaluación de errores de producción pendiente |
| RNF-07 Portabilidad | Ejecutar en Windows con Python 3.11 recomendado, SQLite aislada o PostgreSQL mediante `DATABASE_URL` | Instalación documentada en máquina limpia | Documentado; instalación independiente por evaluar |
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
         v
SQLAlchemy (database.py)
         +--> SQLite local de desarrollo [por defecto]
         +--> PostgreSQL / Supabase [cuando DATABASE_URL está configurada]
```

Las credenciales se leen de `.env` y **no** deben aparecer en GitHub ni documentos de entrega. La base local y la base remota son opciones de configuración, no bases que se deban sincronizar automáticamente.

## 10. Recorridos principales (historias de usuario)

**HU-01 — Crear vacante.** Como administrador quiero registrar una descripción clara del puesto para comparar expedientes con requisitos laborales definidos.
**HU-02 — Procesar CV.** Como administrador quiero cargar varios CV y revisar errores individuales para no inventar información faltante.
**HU-03 — Comparar perfiles.** Como administrador quiero observar un ranking explicable, junto con perfiles omitidos, para priorizar una revisión humana.
**HU-04 — Gestionar etapas.** Como administrador quiero identificar el estado de cada persona por vacante para mantener un seguimiento coherente.
**HU-05 — Entrevistar.** Como administrador quiero agendar y cambiar una cita para coordinar con cada postulante.
**HU-06 — Tomar decisión.** Como administrador quiero marcar finalistas y aceptar, rechazar o retirar perfiles, de manera deliberada y trazable.
**HU-07 — Resguardar información.** Como administrador quiero que las rutas estén protegidas y evitar publicar datos privados accidentalmente.

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

1. Ejecutar `python -m pytest -q tests` en un entorno aislado: **28 pruebas disponibles en el corte 3.8**. Registrar salida, versión de Python y fecha de ejecución.
2. Ejecutar el recorrido manual E2E con una vacante y CV ficticios, **sin utilizar credenciales reales de postulantes**.
3. Verificar autenticación, lectura prohibida sin clave, edición y eliminaciones solo en datos de prueba.
4. Ejecutar un escenario con CV profesional válido, uno genérico, uno DOCX con tablas y uno `.doc` heredado; registrar resultado observado.
5. Validar puntuación/justificación en Radar y decisión humana explícita.
6. Comprobar funciones opcionales (Gemini, UltraMsg, Supabase) **solo en un entorno autorizado y separado**, si se dispone de sus credenciales.
7. Guardar evidencias: capturas sin datos personales, comando, resultado esperado/obtenido y referencia de commit.

**Criterio de cierre del MVP:** aprobar todos los criterios **P0** descritos en `MVP.md` y documentar sin ocultar los casos fallidos. Las metas OBJ-01 a OBJ-05 deben tener resultado medido; hasta entonces su estado es **propuesto**.

## 13. Roadmap después del MVP

- **Fase siguiente:** cuentas de candidato, postulación propia y consulta de estado con aislamiento de información por identidad.
- **Siguiente mejora técnica:** asociación de múltiples entrevistas y vacantes por candidato, historial de cambios por administrador y borrados auditables.
- **Privacidad/seguridad:** revisión legal, política de retención y consentimiento aplicable, HTTPS, autorización por roles, limitación de intentos y auditoría.
- **Evaluación de calidad:** corpus de CV ficticios representativos, revisión humana de pertinencia, estudio de resultados por subgrupos sin uso de datos personales sensibles en el ranking.
- **Operación:** métricas de tiempo de procesamiento, procedimientos de respaldo/restauración y monitorización de fallos externos.

## 14. Decisiones por validar

1. Aprobación académica de los objetivos medibles (OBJ-01 a OBJ-05) y del alcance estrictamente administrativo.
2. Responsable autorizado de los expedientes, finalidad y plazo de conservación de CV.
3. Política de credenciales y requisitos de despliegue cuando el sistema deje de ser prototipo local.
4. Modelo de cuenta de candidato y capacidad de postularse a varias vacantes en fases futuras.
5. Conjunto y método de evaluación de pertinencia del ranking para CV redactados en español.

---

**Regla de documentación:** en cada actualización del repositorio, distinguir `Implementado`, `Probado`, `Validado manualmente`, `Pendiente` y `Fuera de alcance`. No declarar una métrica como lograda sin salida de prueba o evidencia reproducible.

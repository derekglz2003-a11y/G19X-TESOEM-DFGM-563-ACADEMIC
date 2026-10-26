# MVP — CurriculAi

**Producto:** CurriculAi — Optimizador de filtrado curricular mediante IA
**Versión del documento:** 1.0 · CurriculAi 3.6 (alcance técnico del código 3.5)
**Fecha de referencia:** 21 de octubre de 2026
**Estado:** MVP administrativo implementado parcialmente validado; pendiente de aceptación integral
**Documento de requisitos:** [`PRD.md`](PRD.md)

## 1. Qué entregamos como MVP

Un **prototipo académico de reclutamiento para un administrador** que permite:

`Iniciar sesión → Crear vacante → Subir CV → Consultar expediente → Ejecutar ranking semántico → Revisar resultados → Actualizar seguimiento → Agendar entrevista → Decidir etapa final`.

La generación de descripciones con Gemini y el envío automático de WhatsApp mediante UltraMsg son **funciones opcionales**: el flujo central debe poder demostrarse aunque las integraciones no estén configuradas. Ninguna puntuación ejecuta una contratación o un rechazo automático.

El MVP **no** contiene aún portal del candidato ni múltiples usuarios con roles. Estas funciones se documentan como pendientes y no son criterio de aprobación de esta entrega.

## 2. Requisitos mínimos para ejecutar

- Python **3.11 recomendado**, con dependencias de `requirements.txt`.
- Dos procesos: FastAPI (`main.py`) y Streamlit (`app.py`).
- Archivo `.env` privado para `ADMIN_PASSWORD_HASH`, `ADMIN_API_KEY` y, cuando corresponda, `DATABASE_URL` remota. No incluir `.env` en Git.
- SQLite **de pruebas** o PostgreSQL por `DATABASE_URL`; nunca reutilizar la base de producción para pruebas destructivas.
- Descarga inicial del modelo `sentence-transformers/all-MiniLM-L6-v2`, que requiere conexión a Internet; tras descargarlo podrá reutilizarse localmente.
- Tesseract instalado solo para OCR real de imágenes y PDF escaneados.
- Gemini y UltraMsg solo cuando se quiera probar sus integraciones.

**Formatos admitidos del endpoint:** PDF, DOCX, TXT, PNG, JPG, JPEG, WEBP. **No** `.doc` binario antiguo. El límite actual por archivo es **15 MB**.

## 3. Funciones y criterios de aceptación

**Criterios redactados en formato Dado / Cuando / Entonces**, diseñados para probarse con un ambiente separado y datos ficticios. La presencia de código no significa que el caso manual ya se haya aprobado.

| ID | Función (prioridad) | Criterio de aceptación verificable | Estado actual / evidencia |
|---|---|---|---|
| CA-01 | Acceso administrativo (P0) | **Dado** acceso sin contraseña correcta, **cuando** se intenta abrir el panel, **entonces** no se presentan datos; una solicitud API sin `X-API-Key` válida devuelve denegación | Código 3.5; pruebas automatizadas de seguridad |
| CA-02 | CRUD de vacantes (P0) | **Dado** un administrador autenticado, **cuando** crea una vacante con título y descripción, **entonces** figura en el listado, se edita y solo se elimina con confirmación en UI | API/UI implementadas; prueba API |
| CA-03 | Carga múltiple de CV (P0) | **Dado** un PDF, DOCX y TXT ficticios legibles, **cuando** se cargan, **entonces** se informa resultado por archivo y se crean expedientes sin inventar atributos ausentes | Extracción implementada; tests de TXT/DOCX; integración manual pendiente |
| CA-04 | Formato y error de extracción (P0) | **Dado** un `.doc` antiguo o CV sin texto extraíble, **cuando** se intenta cargar, **entonces** se informa la limitación y no se presenta un perfil ficticio como válido | Código y pruebas de error implementadas |
| CA-05 | Consultar y editar expedientes (P0) | **Dado** un candidato registrado, **cuando** se busca por nombre o habilidad y se edita su perfil laboral, **entonces** los cambios se recuperan después de actualizar la vista | Código de Candidatos + API; prueba manual pendiente |
| CA-06 | Ranking por vacante (P0) | **Dada** una vacante válida y dos perfiles ficticios con datos profesionales, **cuando** se ejecuta la evaluación, **entonces** aparece ranking entre 0 y 100, se guarda la evaluación y se muestra justificación | Motor y pruebas con embeddings simulados; pertinencia real pendiente |
| CA-07 | Exclusión de datos demográficos (P0) | **Dado** un candidato, **cuando** cambia únicamente nombre, edad, sexo, correo o teléfono, **entonces** la entrada de texto para embeddings permanece basada en perfil, experiencia y habilidades | Pruebas de `perfil_laboral` aprobadas; no garantiza eliminación de todo PII libre |
| CA-08 | Candidatos con evidencia insuficiente (P0) | **Dado** un expediente solo con valores genéricos, **cuando** se calcula ranking, **entonces** se omite, aumenta el contador y no conserva una puntuación obsoleta en esa vacante | Pruebas API del motor implementadas |
| CA-09 | Seguimiento por vacante (P0) | **Dado** un candidato y una vacante, **cuando** se cambia la etapa, **entonces** el estado queda almacenado para esa relación | API/tabla `Seguimiento`; prueba API |
| CA-10 | Agenda (P0) | **Dado** un candidato válido, **cuando** se programa una entrevista, **entonces** se almacena fecha, hora y lugar; después puede editarse o cancelarse | API/UI implementadas; prueba API básica |
| CA-11 | Finalistas y decisión humana (P0) | **Dada** una entrevista, **cuando** el administrador marca Finalista y después Aceptado/Rechazado, **entonces** se almacena su decisión sin depender del puntaje IA | API/UI implementadas; escenarios de prueba de decisión |
| CA-12 | Bitácora WhatsApp (P1) | **Dada** una acción de mensajería, **cuando** UltraMsg responde, **entonces** se registra estado y respuesta; sin credenciales no se informa falsamente un envío exitoso | Bitácora implementada; envío real externo no validado |
| CA-13 | Descripción con Gemini (P1) | **Dado** un título de puesto y contexto, **cuando** se invoca IA configurada, **entonces** se propone un texto que el humano revisa; sin clave, la API informa indisponibilidad | Ruta implementada y caso sin clave probado; generación real pendiente |
| CA-14 | Eliminación y confirmación (P0) | **Dado** un expediente o pool de prueba, **cuando** no hay confirmación o clave, **entonces** no debe efectuarse eliminación; con ambas y decisión del admin, se elimina según la operación | UI + API implementadas; validación destructiva solo en BD aislada |
| CA-15 | Instalación y pruebas (P0) | **Dado** un clon del repositorio sin secretos, **cuando** se configuran dependencias y credenciales de prueba, **entonces** el sistema inicia y el comando de pruebas finaliza sin fallos | Documentado; 28 pruebas aprobadas en entorno aislado al corte 3.8; instalación limpia desde cero pendiente |

**P0:** imprescindible para considerar completo el MVP administrativo.
**P1:** integración complementaria, operativa solo cuando exista proveedor disponible.
**P2:** futura versión, no requerida en esta aceptación.

## 4. Plan de pruebas de aceptación manual

Usa una copia temporal del proyecto con una base **desechable**, dos o tres vacantes ficticias y al menos 5 CV de prueba sin datos reales.

### Escenario E2E-01 — De vacante a finalista

1. Acceder con contraseña de prueba.
2. Crear una vacante ficticia con requisitos exclusivamente profesionales.
3. Subir dos CV ficticios compatibles y uno con datos insuficientes.
4. Abrir Vacantes o Radar, pulsar evaluación e identificar resultados y omitidos.
5. Examinar justificación, abrir candidato y ajustar seguimiento a `Preseleccionado`.
6. Agendar entrevista, modificar fecha o estado y seleccionar `Finalista`.
7. Confirmar en Finalistas que el administrador puede elegir `Aceptado` o `Rechazado`.

**Resultado esperado:** el recorrido termina sin errores de servidor, conserva estado en la base de prueba y nunca asigna un resultado laboral de forma automática. Registrar el resultado observado y una captura **sin datos personales**.

### Escenario E2E-02 — Protección de información

1. Abrir Streamlit sin autenticación: los listados no deben mostrarse.
2. Solicitar `GET /api/v1/candidatos` sin clave: se debe denegar acceso.
3. Intentar `DELETE /api/v1/limpiar-pool` sin clave: se debe denegar acceso.
4. Revisar que `.env` esté ignorado y que no exista ninguna credencial real en el commit.

**Resultado esperado:** las rutas operativas no entregan datos sin credenciales. Estas pruebas no implican que el prototipo sea apto para Internet público.

### Escenario E2E-03 — Extracción imperfecta

1. Cargar un DOCX ficticio con texto en tabla.
2. Cargar un TXT con habilidades profesionales reconocibles.
3. Intentar cargar un `.doc` antiguo, que debe rechazarse explicando la conversión.
4. Probar un PDF sin texto: si Tesseract está disponible, documentar resultado real de OCR; de lo contrario, documentar dependencia faltante.

**Resultado esperado:** mostrar resultados explícitos, sin atribuir experiencia o habilidades inexistentes.

### Escenario E2E-04 — Consistencia del ranking

1. Evaluar la misma vacante dos veces sin cambiar datos.
2. Comprobar que se actualiza la evaluación existente en vez de crear dos evaluaciones para la misma persona/vacante.
3. Sustituir un perfil profesional por valores genéricos en el entorno de prueba.
4. Recalcular: comprobar contador de omitidos y retiro de su resultado anterior.

**Resultado esperado:** datos coherentes y trazables. Debe revisarse la falta de un índice único de `Evaluacion` como posible endurecimiento futuro.

### Escenario E2E-05 — Funciones externas opcionales

1. Sin `GEMINI_API_KEY`, probar la generación de descripción y documentar el error esperado.
2. Sin credenciales UltraMsg, comprobar que no se muestra confirmación falsa de envío.
3. Si existen cuentas de prueba autorizadas, verificar respuesta del proveedor y bitácora **sin números ni mensajes personales reales**.

**Resultado esperado:** el flujo P0 funciona sin depender de servicios de mensajería y generación de texto. La entrega de WhatsApp no se da por confirmada solo por un HTTP exitoso.

## 5. Evidencia automatizada existente

Al corte CurriculAi 3.8 se incluyen `tests/test_api.py`, `tests/test_perfil_laboral.py` y `tests/test_gemini_ia.py`. Se ejecutó `python -m pytest -q tests` sobre una base SQLite aislada y **28 pruebas finalizaron correctamente** durante la preparación del parche. Es necesario repetir este comando en la computadora del responsable y guardar evidencia del resultado. Las pruebas simulan Gemini, embeddings y parte del OCR: no certifican calidad del modelo ni disponibilidad de servicios externos.

Comando reproducible desde la raíz del repositorio:

```powershell
.\venv\Scripts\python.exe -m pytest -q tests
```

Áreas cubiertas por esas pruebas:

- Alta de vacantes, flujo de API, evaluaciones, seguimiento, entrevistas y bitácora.
- Denegación de solicitudes API sin clave; verificación del hash administrativo.
- Generador de configuración `.env` que conserva las demás variables.
- Extracción de TXT y DOCX, casos con texto insuficiente y `.doc` antiguo.
- Limpieza de datos laborales y exclusión de campos personales explícitos en el insumo del embedding.
- Omisión de perfiles genéricos y eliminación de evaluación obsoleta.
- Comportamiento de PDF y activación simulada de OCR.

**Limitaciones:** las pruebas utilizan SQLite temporal, motores semánticos simulados y OCR simulado en algunos escenarios. **No prueban Supabase, descarga/precisión real del modelo, Gemini, UltraMsg ni Tesseract de extremo a extremo.** Guardar las evidencias sin exponer datos reales.

## 6. Registro de aceptación (rellenar tras ejecución)

| ID | Evidencia esperada | Estado actual |
|---|---|---|
| E2E-01 | Captura del flujo vacante → finalista + registro de estados | **Pendiente de ejecución manual** |
| E2E-02 | Salida de API denegando peticiones + comprobación Git | Pruebas automatizadas disponibles; verificación manual pendiente |
| E2E-03 | Tabla de CV ficticios por formato, texto extraído, error si aplica | **Pendiente de medición manual** |
| E2E-04 | Comparación de ranking antes/después de reevaluar | Pruebas automatizadas disponibles; integración manual pendiente |
| E2E-05 | Respuesta de Gemini/UltraMsg en entorno de prueba, si se dispone | **Opcional; integración real pendiente** |
| TA-01 | Captura del terminal con todas las pruebas aprobadas (27 en 3.8) | **Resultado en entorno aislado**; repetir y conservar evidencia del equipo local |

Para cada evidencia se recomienda documentar: fecha, commit, versión de Python, entorno (local/aislado), datos sintéticos utilizados, resultado esperado, resultado observado, errores y responsable que revisó.

## 7. Requisitos de aceptación para cerrar el MVP

Se considerará **aceptado** cuando:

1. Los 15 criterios CA estén evaluados y **todos los P0** tengan evidencia aprobada; las funcionalidades P1 pueden constar como opcionales/no configuradas.
2. Se registren los resultados de E2E-01 a E2E-04 en base aislada y sin datos reales.
3. Las pruebas automatizadas se ejecuten sin fallos en el entorno de entrega y se conserve la salida.
4. Exista trazabilidad con el PRD, README, commits y listado de limitaciones conocidas.
5. El evaluador o responsable autorizado confirme que el **alcance administrativo** es el alcance evaluado.

**Estado de aceptación actual:** **pendiente**. Hay implementación y pruebas automatizadas, pero faltan evidencias manuales y validaciones externas. No se afirma un resultado académico o productivo definitivo.

## 8. Pendientes y fases posteriores

| Prioridad futura | Función / mejora | Por qué no está en el MVP actual |
|---|---|---|
| P2 | Portal de candidato, inicio de sesión individual y solicitud a vacantes | El MVP es de un administrador; necesita un modelo completo de permisos |
| P2 | Varios reclutadores, roles, auditoría completa y sesiones robustas | Seguridad adicional de producción |
| P2 | Más de una entrevista por candidato y por proceso | La tabla actual `Entrevista` limita a una cita por candidato |
| P2 | Política formal de consentimiento, retención, acceso y supresión de CV | Requiere aprobación organizacional y legal |
| P2 | Evaluación sistemática de pertinencia y sesgo del ranking | Faltan corpus, protocolo y medición con supervisión humana |
| P2 | Métricas de rendimiento, despliegue HTTPS y respaldo/restauración | No forman parte del prototipo académico local |
| P2 | Conversión de `.doc` y mayor cobertura de OCR para PDF | Restricciones técnicas que deben tratarse por separado |

## 9. Definición de terminado (Definition of Done) por mejora

Un cambio se considera terminado solo cuando:

- Cumple un requisito del PRD o una corrección documentada.
- No expone secretos, expedientes ni identidades en el repositorio.
- Incluye pruebas pertinentes y no rompe la batería existente.
- Se prueba manualmente si introduce cambios en la interfaz o servicios reales.
- Actualiza documentación y registra un commit pequeño con mensaje descriptivo.
- Identifica de forma explícita lo que se **implementó**, **probó** y **no pudo validar**.

---

**Nota académica:** este MVP define qué se ofrece y cómo comprobarlo; no convierte un prototipo en producto de producción ni sustituye la evaluación humana de los resultados de IA.

# CurriculAi — cierre de validación del MVP administrativo

**Fecha de pruebas:** 26 de octubre de 2026
**Entorno:** Streamlit local (puerto 8502), FastAPI local (8010), SQLite temporal `curriculai_e2e_seguro.db`
**Naturaleza de los datos:** cinco CV ficticios y dos vacantes ficticias; sin datos productivos de Supabase
**Alcance:** MVP de administración de reclutamiento, no el portal de candidato.

## Resumen ejecutivo

Se completó un recorrido manual observado desde carga multiformato y OCR de CV hasta generación de rankings semánticos por vacante, agenda de entrevistas y decisión de finalistas. También se verificó que una petición a `GET /api/v1/candidatos` sin `X-API-Key` recibió **HTTP 401**. La ejecución final de la suite de pruebas mostró **34 passed, 2 warnings, 0 failed (6.13 s)**.

**Evidencia de persistencia:** la persona que ejecutó el flujo indicó que los datos continuaron visibles después de reiniciar los servidores. No contamos con una captura comparativa antes/después, por lo que se registra como *validación reportada*, no como prueba documental independiente.

### Resultados del corpus y de las vacantes

- Se registraron **cinco CV de prueba válidos** en PDF, DOCX, TXT e imagen PNG (OCR). El archivo adicional sin contenido útil fue rechazado por diseño; falta captura final dedicada del rechazo.
- La primera vacante, **Auxiliar administrativo (#1)**, evaluó cinco CV. Se observó a Elena en el puesto 2 con **54.0 %**.
- La segunda vacante, **Auxiliar contable (#2)**, evaluó cinco CV. Se observó a Carla en puesto 1 con **71.3 %** y Daniel en puesto 2 con **70.3 %**.
- Los porcentajes representan una **medida orientativa de similitud semántica**, no probabilidad de contratación ni recomendación concluyente. El personal debe verificar la experiencia y los documentos originales.
- Se guardó y modificó una entrevista, se envió un expediente a finalistas, se registró una aceptación y posteriormente un rechazo. La interfaz confirmó los cambios.
- La mensajería WhatsApp **no fue enviada** por falta de un número válido; se informó correctamente y no se registró un envío exitoso falso.

## Evidencia visual y trazabilidad

| ID | Resultado mostrado | Imagen |
|---|---|---|
| ENV-01 | Panel de pruebas inicialmente vacío; 0 vacantes y 0 candidatos | [Captura](evidencias/E2E-00_entorno_aislado_sin_registros.png) |
| OCR-01 | Carga correcta del CV 05, tras configurar Tesseract | [Captura](evidencias/E2E-02_carga_cv_05_ocr.png) |
| IA-01 | Primer ranking con cinco CV procesados | [Captura](evidencias/E2E-03_ranking_cinco_cv.png) |
| IA-02 | Elena aparece en ranking tras OCR, 54.0 % | [Captura](evidencias/E2E-03B_cv_elena_ocr_ranking.png) |
| ENT-01 | Cita guardada y WhatsApp no enviado con mensaje claro | [Captura](evidencias/E2E-04_entrevista_creada.png) |
| ENT-02 | Cita actualizada | [Captura](evidencias/E2E-04B_entrevista_editada.png) |
| FIN-01 | Perfil enviado a finalistas | [Captura](evidencias/E2E-05_finalista_registrado.png) |
| FIN-02 | Decisión de aceptación visible | [Captura](evidencias/E2E-05B_decision_aceptado.png) |
| FIN-03 | Rechazo registrado; listado de finalistas vacío | [Captura](evidencias/E2E-05C_decision_rechazado.png) |
| IA-03 | Segunda vacante, cinco CV procesados | [Captura](evidencias/E2E-06_segunda_vacante_cinco_cv.png) |
| IA-04 | Carla, 71.3 %, primer lugar en Auxiliar contable | [Captura](evidencias/E2E-06A_carla_71_3.png) |
| IA-05 | Daniel, 70.3 %, segundo lugar en Auxiliar contable | [Captura](evidencias/E2E-06B_daniel_70_3.png) |
| SEC-01 | GET `/api/v1/candidatos` sin clave, **HTTP 401** | [Captura recortada](evidencias/SEC-01_http_401_sin_api_key.png) |
| TEST-01 | pytest: **34 passed, 2 warnings** | [Captura](evidencias/TEST-01_pytest_34_aprobadas.png) |

> La captura de seguridad se recortó para no mostrar la ruta de perfil personal de Windows. Ninguna captura adjunta contiene tokens, claves administrativas ni CV reales conforme a la revisión visual realizada al generar este paquete. Conviene revisar de nuevo antes de publicar.

## Incidencias detectadas y resolución

1. **Tesseract no encontrado por el backend:** se instaló/configuró `tesseract.exe` mediante `TESSERACT_CMD` y se reinició FastAPI con SQLite de pruebas. Posteriormente se aceptó el CV PNG de Elena.
2. **Puertos ocupados por procesos antiguos:** se reiniciaron las instancias de FastAPI y Streamlit para aislar la prueba.
3. **Prueba de OCR incompatible con cambio del extractor:** se ajustó la simulación en `tests/test_perfil_laboral.py`. Tras corregir la ubicación del `monkeypatch`, se obtuvieron 34 pruebas aprobadas.
4. **WhatsApp no enviado con número ficticio:** la entrevista se registró y la interfaz informó de que no se envió ni almacenó como envío exitoso.

## Límites de esta evidencia

No demuestra: despliegue seguro en producción, instalación limpia en otro equipo, envío real de WhatsApp, calibración/equidad estadística del motor, todas las rutas protegidas ni cuentas de candidato. Estas actividades deben verificarse por separado antes de presentar el sistema para uso real con información personal.

La comprobación manual de persistencia se reportó positiva, pero **falta una captura después del reinicio que muestre la misma base**. El rechazo del CV inválido también carece de una captura definitiva centrada en el mensaje.

## Conclusión

Los pasos principales del **MVP administrativo** fueron observados funcionando en un entorno local aislado con datos ficticios y los controles básicos descritos. Los resultados proporcionan evidencias útiles para la revisión académica, con las limitaciones anteriores explícitas. La vista de candidato continúa fuera de este corte.

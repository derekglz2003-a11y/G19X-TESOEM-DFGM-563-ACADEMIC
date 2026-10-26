# Registro consolidado de pruebas E2E — CurriculAi

**Fecha:** 2026-10-26
**Stack:** Streamlit 8502 → FastAPI 8010 → SQLite temporal
**Commit del código ejecutado:** anotar al publicar (`git rev-parse --short HEAD`); el código local del parche OCR y de la prueba se modificó después del commit 3.7.

| Prueba | Resultado | Estado y límite |
|---|---|---|
| Aislamiento | Panel inicial con 0 vacantes y 0 candidatos; motor SQLite comprobado en terminal | Aprobado en entorno local |
| PDF, DOCX, TXT y PNG | 5 CV válidos llegaron al ranking | Aprobado con corpus ficticio |
| OCR imagen | CV de Elena leído; CRM/Excel/Word; puesto 2 en vacante 1 | Aprobado con Tesseract local |
| Negativo CV 06 | Intento rechazado según mensajes de sesión anterior | Reportado; falta captura dedicada |
| Ranking vacante 1 | 5 procesados; Elena 54.0 % | Aprobado visualmente |
| Ranking vacante 2 | 5 procesados; Carla 71.3 %; Daniel 70.3 % | Aprobado visualmente |
| Entrevista | Se agendó y actualizó correctamente | Aprobado visualmente |
| WhatsApp | No enviado por teléfono inválido, sin bitácora de envío falso | Aprobada la notificación de fallo, no la integración real |
| Finalistas | Registro de finalista, aceptación y rechazo posteriores | Aprobado visualmente |
| Persistencia | Se reiniciaron servidores y usuario confirmó que los registros seguían | Aprobado según usuario; evidencia de pantalla posterior pendiente |
| API sin clave | GET `/api/v1/candidatos` respondió HTTP 401 | Aprobado |
| Suite de pruebas | 34 aprobadas, 2 advertencias, 0 fallidas, 6.13 s | Aprobado en máquina local |

## Evidencias y comprobaciones faltantes

- [ ] Adjuntar captura posterior al reinicio de persistencia, si se requiere prueba visual estricta.
- [ ] Adjuntar el mensaje específico de rechazo del CV 06 si se requiere cubrir el caso negativo.
- [ ] Verificar instalación desde repositorio limpio en otro entorno antes de afirmar reproducibilidad total.
- [ ] Verificar que los cambios de OCR y su prueba estén en un commit publicado.
- [ ] Repetir validación de seguridad y OCR en cualquier despliegue final o cambio de configuración.

**Interpretación:** `pytest` prueba la lógica de los casos automatizados en su entorno; la sesión E2E aportó comprobaciones manuales con modelo semántico real. Ninguna de estas pruebas convierte la similitud en una decisión de contratación automática.

# Datos de prueba de CurriculAi

Esta carpeta contiene **datos enteramente ficticios**. No representan personas, empresas ni instituciones reales. Los correos usan el dominio de documentación `example.com`.

## Archivos de CV

| Archivo | Formato | Objetivo de la prueba |
| --- | --- | --- |
| `cv/CV_01_Auxiliar_Administrativo.txt` | TXT | Extracción de texto y ranking administrativo |
| `cv/CV_02_Auxiliar_Contable.docx` | DOCX | Lectura de documento Word, incluida una tabla |
| `cv/CV_03_Soporte_Tecnico_OCR.png` | PNG | OCR en imagen (solo si Tesseract está disponible) |

`vacantes_ejemplo.md` contiene dos vacantes para crear manualmente desde el panel administrador.

## Secuencia de demostración (administrador y candidato)

1. Clonar el repositorio en una carpeta nueva. Seguir el README principal para instalar dependencias, configurar `.env` de prueba y crear la contraseña administrativa con `scripts/configurar_acceso.py`. **No utilizar la base de datos personal/remota ni un `.env` real.**
2. Iniciar FastAPI y Streamlit según el README principal; entrar como **Administrador** con la contraseña creada localmente. No hay contraseña predefinida publicada.
3. Crear la vacante «Auxiliar administrativo» con el texto de `vacantes_ejemplo.md` y publicarla para candidatos.
4. Cargar al menos los CV TXT y DOCX desde el módulo **Candidatos**; probar el PNG por separado si Tesseract está instalado. Registrar cualquier fallo de OCR.
5. Ejecutar la evaluación desde **Vacantes** o **Radar de talentos** y revisar las similitudes de los CV disponibles. Son resultados orientativos, no decisiones de contratación.
6. Cerrar sesión, elegir **Candidato** y registrarse con datos completamente ficticios y una contraseña nueva de al menos 12 caracteres. Completar el perfil, crear o cargar el CV y usar **Compartir mi CV** si se desea incluirlo en el pool.
7. Desde la cuenta candidata, consultar la vacante publicada y postularse. Volver al administrador para verificar la postulación y, con un perfil ficticio, programar una entrevista.
8. Volver al portal candidato y comprobar el aviso privado. Registrar resultados y evidencias sin datos reales.

## Precauciones

- No publicar bases SQLite, `.env`, contraseñas, claves API ni capturas con datos personales reales.
- Para una prueba de aislamiento, utilizar dos cuentas ficticias distintas y comprobar que no puedan ver avisos ajenos.
- Es posible que el modelo de embeddings requiera descarga inicial. `EMBEDDINGS_MODEL` puede usar el predeterminado `sentence-transformers/all-MiniLM-L6-v2`.
- La prueba real de Gemini es **independiente** y no queda acreditada por estos archivos.

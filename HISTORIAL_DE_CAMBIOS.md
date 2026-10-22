# CurriculAi — Primer commit de seguridad

**Base:** CurriculAi , conservando menú compacto y módulos anteriores.

## Archivos cambiados

- `main.py`: exige `X-API-Key` en todos los endpoints. Sin configuración la API permanece cerrada.
- `app.py`: pantalla de acceso administrativo; controla sesión, deja el menú y estilos intactos.
- `servicios/api.py`: agrega clave al llamar al backend desde Streamlit.
- `servicios/seguridad.py` **nuevo**: comprueba contraseña PBKDF2-HMAC-SHA256.
- `scripts/configurar_acceso.py` **nuevo**: genera clave y hash en `.env`, conserva las demás variables.
- `paginas/configuracion.py`: añade Cerrar sesión.
- `.env.example`: nombres de nuevas variables, sin secretos.
- `tests/test_api.py`: pruebas de acceso autorizado y no autorizado.
- `README.md`: instrucciones actuales de ejecución sin ruta absoluta.

## Orden de instalación sin perder registros

1. Respalda `C:\motorcv` y tu base de datos local/administrada.
2. Descomprime **solo el parche** sobre el proyecto ya instalado, manteniendo carpetas `paginas/`, `servicios/`, `scripts/`, `tests/`.
3. Activa tu entorno virtual o usa `.\\venv\\Scripts\\python.exe`.
4. Corre `python scripts/configurar_acceso.py`. Si estás usando tu Python de `venv`, usa ese intérprete.
5. Reinicia tanto `uvicorn` como `streamlit`.
6. Entra a `http://localhost:8501` con la contraseña creada.
7. Verifica `python -m pytest -q tests/test_api.py` antes de hacer commit.
8. Usa `git status` para comprobar que `.env`, `.db` y CV no están incluidos.

## Commit sugerido

Desde la raíz del repositorio (tras probar los cambios):

```powershell
git add main.py app.py servicios/api.py servicios/seguridad.py paginas/configuracion.py scripts/configurar_acceso.py tests/test_api.py .env.example README.md
git status
git commit -m "feat: proteger acceso administrativo y rutas API"
git push origin main
```

**No subas el ZIP a GitHub si ya has subido los archivos**. No uses `git add .` antes de comprobar que no incluye información privada.

## Seguridad alcanzada y límites

- Bloquea a usuarios sin contraseña en Streamlit.
- Bloquea todos los GET/POST/PUT/DELETE operativos sin clave válida.
- No es todavía autenticación con cuentas múltiples ni permisos por roles.
- No es un reemplazo de HTTPS ni de un despliegue endurecido.
- El sistema no es apto para exponer CV reales públicamente hasta implementar seguridad y cumplimiento adicionales.

## Validación realizada

- Compilación de todos los módulos Python.
- 8 pruebas del backend aprobadas con base de datos aislada.
- No se han probado credenciales externas, el despliegue en Windows ni el renderizado real de Streamlit en la máquina del usuario.

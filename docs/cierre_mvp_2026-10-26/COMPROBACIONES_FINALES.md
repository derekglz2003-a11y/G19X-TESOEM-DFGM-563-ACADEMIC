# Lista de control antes de presentar CurriculAi

Estas comprobaciones son informativas; **no ejecutar contra Supabase real** ni publicar información sensible.

## 1. Confirmar rama y archivos

Desde la carpeta raíz del repositorio en PowerShell:

```powershell
git status
git log -4 --oneline
git ls-files .env
git ls-files '*.db' '*.sqlite' '*.sqlite3'
```

Esperado: `git ls-files .env` y la lista de bases de datos no muestran archivos sensibles rastreados. Si aparecen, detener la publicación y revisar los índices e historial; no se arregla publicando una nueva copia de las credenciales.

## 2. Comprobar que el entorno de pruebas no usa Supabase

En la terminal destinada a FastAPI de pruebas, donde se defina `DATABASE_URL=sqlite:///./curriculai_e2e_seguro.db`, ejecutar antes de iniciar:

```powershell
.\venv\Scripts\python.exe -c "from database import engine; print(engine.dialect.name, engine.url.database)"
```

Debe mostrar `sqlite`; si muestra `postgresql`, **no continuar**.

## 3. Verificar nuevamente las pruebas automáticas

```powershell
.\venv\Scripts\python.exe -m pytest -q tests
```

Captura de esta sesión: `evidencias/TEST-01_pytest_34_aprobadas.png`, con 34 aprobadas y dos advertencias. Si se modifica el código posteriormente, guardar una nueva salida y actualizar las cifras del informe.

## 4. Comprobar la API administrativa sin autorización

Con FastAPI de pruebas en 8010:

```powershell
try {
  $r = Invoke-WebRequest 'http://127.0.0.1:8010/api/v1/candidatos' -Method GET -ErrorAction Stop
  Write-Host "ATENCION: acceso anonimo respondio $($r.StatusCode)"
} catch {
  $s = $_.Exception.Response.StatusCode
  Write-Host "Codigo HTTP:" ([int]$s)
}
```

En la ejecución de 2026-10-26 devolvió 401. Esa prueba cubre ese endpoint; no certifica todas las rutas.

## 5. Revisión visual y privacidad

Revisar todas las imágenes del directorio `evidencias/` antes de hacer `git add`. Solo deben contener datos ficticios, y no deben aparecer contraseñas, tokens, datos de conexión ni direcciones privadas no necesarias.

## 6. Alcance

El **portal de candidato**, auditoría de seguridad completa, pruebas de estrés, prueba de WhatsApp real y validación estadística del ranking no están completados por este recorrido. No declararlos como terminados.

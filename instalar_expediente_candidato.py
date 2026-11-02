"""Instala SOLO el expediente candidato sobre acceso-dos-roles.

Requisitos: instalar_login_roles.py ya aplicado. No altera app.py ni main.py,
no modifica database.py, .env, la autenticación empresarial ni el login visual.
"""
from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
import shutil

raiz = Path(__file__).resolve().parent
seguridad = raiz / 'servicios' / 'portal_auth.py'
login = raiz / 'servicios' / 'login_roles.py'
modulos = [raiz / 'servicios' / nombre for nombre in
           ('portal_expediente.py', 'portal_expediente_ui.py', 'portal_campos.py')]

for ruta in [seguridad, login] + modulos:
    if not ruta.exists():
        raise SystemExit(f'Falta {ruta}. Extrae el ZIP en la RAÍZ C:\\motorcv, conservando servicios/.')

originales = {p: p.read_text(encoding='utf-8-sig') for p in (seguridad, login)}
actualizados = originales.copy()

texto = originales[seguridad]
marca = "    app.mount('/portal', portal)"
if 'agregar_expediente(portal, motor, db_sesion, sesion_autorizada)' not in texto:
    if texto.count(marca) != 1:
        raise SystemExit('portal_auth.py tiene otra estructura. No se modificó nada. Comparte ese archivo para adaptar el parche.')
    agregado = ("    from servicios.portal_expediente import agregar_expediente\n"
                "    agregar_expediente(portal, motor, db_sesion, sesion_autorizada)\n\n")
    actualizados[seguridad] = texto.replace(marca, agregado + marca, 1)

texto = originales[login]
if 'from servicios.portal_expediente_ui import mostrar_expediente_candidato' not in texto:
    if 'from servicios.portal_candidato_ui import mostrar_espacio_candidato' in texto:
        raise SystemExit('Hay otra versión del portal ya instalada. No se cambió nada; requiere integración para no perder secciones.')
    try:
        tree = ast.parse(texto)
    except SyntaxError as exc:
        raise SystemExit(f'login_roles.py tiene sintaxis inválida. No se modificó: {exc}')
    funciones = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == 'mostrar_portal_candidato']
    if len(funciones) != 1:
        raise SystemExit('No se localizó la función mostrar_portal_candidato() exacta. No se modificó nada.')
    fn = funciones[0]
    # Para no perder otras funciones, solo permite reemplazar si es la última.
    if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
           and n.lineno > fn.lineno for n in tree.body):
        raise SystemExit('Hay otras funciones después del portal. No se modificó nada.')
    lineas = texto.splitlines(keepends=True)
    inicio = fn.lineno - 1
    fin = fn.end_lineno
    sustituto = (
        'def mostrar_portal_candidato():\n'
        '    """Expediente personal. Conserva intactos el login y el rol administrativo."""\n'
        '    from servicios.portal_expediente_ui import mostrar_expediente_candidato\n'
        '    mostrar_expediente_candidato()\n'
    )
    actualizados[login] = ''.join(lineas[:inicio]) + sustituto + ''.join(lineas[fin:])

# Verifica sintaxis ANTES de escribir cualquier archivo.
for ruta, contenido in actualizados.items():
    try:
        compile(contenido, str(ruta), 'exec')
    except SyntaxError as exc:
        raise SystemExit(f'No se modificó nada por error de sintaxis en {ruta.name}: {exc}')

cambios = [(p, contenido) for p, contenido in actualizados.items() if contenido != originales[p]]
if cambios:
    sufijo = datetime.now().strftime('%Y%m%d_%H%M%S')
    for ruta, contenido in cambios:
        respaldo = ruta.with_name(ruta.name + f'.bak_antes_expediente_{sufijo}')
        shutil.copy2(ruta, respaldo)
        ruta.write_text(contenido, encoding='utf-8')
        print('Actualizado:', ruta.relative_to(raiz), '| Respaldo:', respaldo.name)
else:
    print('El parche ya está instalado. No se hicieron cambios.')

print('Listo. Conservados: app.py, main.py, database.py, .env y login visual.')
print('Al reiniciar FastAPI se creará la nueva tabla portal_expedientes_laborales en la base seleccionada.')
print('Usa SQLite aislada para las pruebas; NO inicies en Supabase sin revisar primero la migración.')

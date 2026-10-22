"""Genera credenciales para CurriculAi en .env (excluido de Git).

Ejecuta en la raíz del proyecto: python scripts/configurar_acceso.py
"""
from getpass import getpass
from pathlib import Path
import hashlib
import os
import secrets

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"


def guardar_variables(contenido: str, cambios: dict[str, str]) -> str:
    lineas = []
    presentes = set()
    for linea in contenido.splitlines():
        if "=" in linea and not linea.lstrip().startswith("#"):
            clave = linea.split("=", 1)[0].strip()
            if clave in cambios:
                if clave not in presentes:
                    lineas.append(f"{clave}={cambios[clave]}")
                    presentes.add(clave)
                continue
        lineas.append(linea)
    for clave, valor in cambios.items():
        if clave not in presentes:
            lineas.append(f"{clave}={valor}")
    return "\n".join(lineas).rstrip() + "\n"


def main():
    print("Configurar acceso administrativo de CurriculAi")
    print("Se conservarán las demás variables de tu .env.")
    if ENV.exists():
        print("Se sustituirán las credenciales administrativas anteriores.")
    password = getpass("Nueva contraseña de administrador (12 caracteres o más): ")
    confirmacion = getpass("Repite la contraseña: ")
    if len(password) < 12:
        raise SystemExit("La contraseña debe tener 12 caracteres como mínimo.")
    if not secrets.compare_digest(password, confirmacion):
        raise SystemExit("Las contraseñas no coinciden; no se modificó ningún archivo.")
    sal = os.urandom(16)
    iteraciones = 390_000
    clave = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal, iteraciones)
    credenciales = {
        "ADMIN_PASSWORD_HASH": f"pbkdf2_sha256${iteraciones}${sal.hex()}${clave.hex()}",
        "ADMIN_API_KEY": secrets.token_urlsafe(48),
    }
    anterior = ENV.read_text(encoding="utf-8-sig") if ENV.exists() else ""
    ENV.write_text(guardar_variables(anterior, credenciales), encoding="utf-8")
    if os.name != "nt":
        ENV.chmod(0o600)
    print("Configuración lista. Las credenciales están en .env y no se imprimieron.")
    print("Reinicia FastAPI y Streamlit. Nunca publiques .env ni compartas su contenido.")


if __name__ == "__main__":
    main()

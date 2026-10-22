"""Autenticación local de un único administrador (MVP académico).

La contraseña se guarda como derivación PBKDF2 con sal, nunca en el código.
El secreto de la API es independiente de la contraseña de acceso visual.
"""
import hashlib
import hmac
import os


def acceso_configurado() -> bool:
    """Exige ambas credenciales; si faltan, la aplicación no abre el dashboard."""
    return bool(os.getenv("ADMIN_PASSWORD_HASH", "").strip()) and len(
        os.getenv("ADMIN_API_KEY", "").strip()
    ) >= 32


def verificar_contrasena(contrasena: str) -> bool:
    """Comprueba contraseña con PBKDF2-HMAC-SHA256 y comparación constante."""
    registro = os.getenv("ADMIN_PASSWORD_HASH", "").strip()
    if not registro or not contrasena:
        return False
    try:
        metodo, iteraciones_s, sal_hex, derivada_hex = registro.split("$", 3)
        if metodo != "pbkdf2_sha256":
            return False
        iteraciones = int(iteraciones_s)
        if not (200_000 <= iteraciones <= 2_000_000):
            return False
        sal = bytes.fromhex(sal_hex)
        esperado = bytes.fromhex(derivada_hex)
        if len(sal) < 16 or len(esperado) != 32:
            return False
        derivada = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), sal, iteraciones)
        return hmac.compare_digest(derivada, esperado)
    except (ValueError, TypeError):
        return False

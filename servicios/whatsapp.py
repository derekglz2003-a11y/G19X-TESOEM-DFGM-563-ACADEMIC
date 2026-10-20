import os
import re
import requests
from servicios.api import api_post

def enviar_whatsapp_ultramsg(telefono, mensaje):
    """Envía WhatsApp con UltraMsg si está configurado en variables de entorno."""
    instancia = os.getenv("ULTRAMSG_INSTANCE_ID", "").strip()
    token = os.getenv("ULTRAMSG_TOKEN", "").strip()
    if not instancia or not token:
        return False, "UltraMsg no está configurado: faltan ULTRAMSG_INSTANCE_ID y/o ULTRAMSG_TOKEN en .env.", None
    numero = re.sub(r"\D", "", str(telefono or ""))
    if len(numero) == 10:
        numero = "52" + numero
    if len(numero) < 10:
        return False, "El candidato no tiene un teléfono válido.", None
    try:
        url = f"https://api.ultramsg.com/{instancia}/messages/chat"
        respuesta = requests.post(url, data={"token": token, "to": numero, "body": mensaje}, timeout=20)
        try:
            payload = respuesta.json()
        except ValueError:
            payload = {"response": respuesta.text[:300]}
        ok = respuesta.ok and not payload.get("error") and str(payload.get("sent", "true")).lower() not in ("false", "0")
        detalle = str(payload.get("message") or payload.get("error") or payload.get("response") or respuesta.reason)
        return ok, detalle, payload
    except requests.RequestException as exc:
        return False, f"No fue posible conectar con UltraMsg: {exc}", None


def registrar_mensaje_whatsapp(datos):
    """Registra el envío en el backend; requiere /api/v1/mensajes-whatsapp."""
    return api_post("/api/v1/mensajes-whatsapp", data=datos)

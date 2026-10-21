"""Envío voluntario por WhatsApp y bitácora vinculada a entrevistas."""
import os
import requests
from servicios.api import api_post
from servicios.ui_helpers import telefono_mx


def enviar_whatsapp_ultramsg(telefono, mensaje):
    instancia = os.getenv("ULTRAMSG_INSTANCE_ID", "").strip()
    token = os.getenv("ULTRAMSG_TOKEN", "").strip()
    if not instancia or not token:
        return False, "UltraMsg no configurado en las variables de entorno.", None
    numero = telefono_mx(telefono)
    if not numero:
        return False, "El candidato no tiene un teléfono válido.", None
    try:
        # instance_id es un identificador, no parte de un dominio arbitrario.
        if not instancia.replace('-', '').replace('_', '').isalnum():
            return False, "Identificador de instancia UltraMsg inválido.", None
        r = requests.post(f"https://api.ultramsg.com/{instancia}/messages/chat",
                          data={"token": token, "to": numero, "body": mensaje}, timeout=20)
        try:
            payload = r.json()
        except ValueError:
            payload = {"response": "Respuesta no JSON"}
        if not isinstance(payload, dict):
            payload = {"response": "Respuesta inesperada"}
        ok = r.ok and not payload.get("error") and str(payload.get("sent", "true")).lower() not in ("false", "0")
        detalle = str(payload.get("message") or payload.get("error") or r.reason)[:250]
        return ok, detalle, payload
    except requests.RequestException:
        # No registrar errores con URLs que pudieran contener secretos.
        return False, "No se pudo establecer conexión con UltraMsg.", None


def registrar_mensaje_whatsapp(datos):
    return api_post("/api/v1/mensajes-whatsapp", data=datos)


def enviar_invitacion_entrevista(entrevista_id, candidato, puesto, fecha, hora, lugar):
    """Retorna (enviado, detalle, registrado). No confundir aceptado por API con leído."""
    telefono = telefono_mx(candidato.get("telefono"))
    if not telefono:
        return False, "El candidato no tiene un número mexicano válido.", False
    mensaje = (
        f"Hola {candidato.get('nombre') or 'candidato'}, te invitamos a una entrevista "
        f"para {puesto}, el {fecha} a las {hora} en {lugar}. "
        "Por favor confirma tu asistencia. CurriculAi."
    )
    enviado, detalle, payload = enviar_whatsapp_ultramsg(telefono, mensaje)
    registro = registrar_mensaje_whatsapp({
        "entrevista_id": entrevista_id,
        "candidato_id": candidato.get("id"),
        "telefono": telefono,
        "mensaje": mensaje,
        "estado": "Enviado" if enviado else "Fallido",
        "proveedor": "UltraMsg", "detalle": detalle,
        "respuesta": payload,
    })
    return enviado, detalle, bool(registro is not None and registro.ok)

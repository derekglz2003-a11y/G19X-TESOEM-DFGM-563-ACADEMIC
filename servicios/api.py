import requests
import os
from dotenv import load_dotenv
load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
if API_URL.endswith("/api/v1"):
    API_URL = API_URL[:-7].rstrip("/")

def api_get(path, default=None):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return default if default is not None else []


def api_post(path, data=None, files=None):
    try:
        if files:
            # FastAPI UploadFile endpoints necesitan multipart/form-data.
            return requests.post(f"{API_URL}{path}", data=data, files=files, timeout=120)
        # El resto de endpoints reciben normalmente un cuerpo JSON.
        return requests.post(f"{API_URL}{path}", json=data, timeout=180)
    except requests.RequestException:
        return None


def api_post_form(path, data=None):
    """Envía datos como form-urlencoded para endpoints FastAPI con Form(...)."""
    try:
        return requests.post(f"{API_URL}{path}", data=data or {}, timeout=30)
    except requests.RequestException:
        return None


def api_delete(path):
    try:
        r = requests.delete(f"{API_URL}{path}", timeout=15)
        return r
    except Exception:
        return None


def api_put(path, data):
    try:
        r = requests.put(f"{API_URL}{path}", json=data, timeout=15)
        return r
    except Exception:
        return None


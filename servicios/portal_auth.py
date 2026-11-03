"""Acceso separado para candidatos. No modifica la autenticación administrativa.

APIRouter/ASGI sub-app montada en /portal, para no heredar el X-API-Key
administrativo que protege el resto de la API de CurriculAi.

Versión inicial: registro, ingreso, perfil propio y revocación de sesión.
No publica vacantes internas ni expone datos de otros candidatos.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Base, engine as motor_principal

ITERACIONES = 330_000
DURACION_HORAS = 12
USUARIO_RE = re.compile(r"^[a-z0-9._-]{3,40}$")


class UsuarioPortal(Base):
    __tablename__ = "portal_usuarios"

    id = Column(Integer, primary_key=True)
    usuario = Column(String(40), unique=True, nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(254), unique=True, nullable=False, index=True)
    contrasena_hash = Column(String(256), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)


class SesionPortal(Base):
    __tablename__ = "portal_sesiones"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("portal_usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expira_en = Column(DateTime, nullable=False)


class RegistroRequest(BaseModel):
    usuario: str = Field(min_length=3, max_length=40)
    nombre: str = Field(min_length=2, max_length=100)
    correo: str = Field(min_length=5, max_length=254)
    contrasena: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    usuario: str = Field(min_length=1, max_length=40)
    contrasena: str = Field(min_length=1, max_length=128)


def _hash_contrasena(contrasena: str) -> str:
    sal = secrets.token_bytes(16)
    clave = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), sal, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${sal.hex()}${clave.hex()}"


def _verificar_contrasena(contrasena: str, registro: str) -> bool:
    try:
        algoritmo, iteraciones, sal, esperado = registro.split("$", 3)
        n = int(iteraciones)
        if algoritmo != "pbkdf2_sha256" or not 200_000 <= n <= 1_500_000:
            return False
        derivada = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), bytes.fromhex(sal), n)
        return hmac.compare_digest(derivada, bytes.fromhex(esperado))
    except (ValueError, TypeError):
        return False


def _utc_naive() -> datetime:
    """SQLite y PostgreSQL comparten UTC naive en esta tabla controlada."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def montar_portal(app: FastAPI, motor=None) -> FastAPI:
    """Agrega el portal aislado, sin alterar ni relajar la clave X-API-Key.

    motor permite usar SQLite aislado en las pruebas.
    """
    if any(getattr(r, 'path', None) == '/portal' for r in app.routes):
        raise RuntimeError('El portal ya está montado')

    motor = motor if motor is not None else motor_principal
    Base.metadata.create_all(bind=motor, tables=[UsuarioPortal.__table__, SesionPortal.__table__])
    portal = FastAPI(title="Acceso de candidatos", docs_url=None, redoc_url=None, openapi_url=None)

    def db_sesion():
        with Session(motor) as db:
            yield db

    def sesion_autorizada(authorization: Optional[str] = Header(default=None), db: Session = Depends(db_sesion)) -> UsuarioPortal:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Debes iniciar sesión como candidato")
        token = authorization[7:].strip()
        if len(token) > 256 or len(token) < 32:
            raise HTTPException(status_code=401, detail="Sesión no válida")
        hash_token = hashlib.sha256(token.encode("utf-8")).hexdigest()
        sesion = db.query(SesionPortal).filter_by(token_hash=hash_token).first()
        if not sesion or sesion.expira_en <= _utc_naive():
            raise HTTPException(status_code=401, detail="Sesión caducada o inválida")
        usuario = db.get(UsuarioPortal, sesion.usuario_id)
        if not usuario or not usuario.activo:
            raise HTTPException(status_code=401, detail="Cuenta no disponible")
        return usuario

    @portal.post('/registro', status_code=201)
    def registro(datos: RegistroRequest, db: Session = Depends(db_sesion)):
        username = datos.usuario.strip().lower()
        correo = datos.correo.strip().lower()
        nombre = datos.nombre.strip()
        if not USUARIO_RE.fullmatch(username):
            raise HTTPException(status_code=422, detail="Usuario: 3 a 40 caracteres; usa letras, números, punto, guion o guion bajo")
        if not (correo.count('@') == 1 and '.' in correo.partition('@')[2] and ' ' not in correo):
            raise HTTPException(status_code=422, detail="Introduce un correo electrónico válido")
        if not nombre:
            raise HTTPException(status_code=422, detail="Introduce tu nombre")
        nuevo = UsuarioPortal(usuario=username, nombre=nombre, correo=correo, contrasena_hash=_hash_contrasena(datos.contrasena))
        db.add(nuevo)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="El usuario o correo ya está registrado")
        return {"mensaje": "Cuenta creada. Ya puedes iniciar sesión."}

    @portal.post('/ingresar')
    def ingresar(datos: LoginRequest, db: Session = Depends(db_sesion)):
        usuario = db.query(UsuarioPortal).filter_by(usuario=datos.usuario.strip().lower()).first()
        if not usuario or not usuario.activo or not _verificar_contrasena(datos.contrasena, usuario.contrasena_hash):
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
        token = secrets.token_urlsafe(40)
        db.add(SesionPortal(
            usuario_id=usuario.id,
            token_hash=hashlib.sha256(token.encode('utf-8')).hexdigest(),
            expira_en=_utc_naive() + timedelta(hours=DURACION_HORAS),
        ))
        db.commit()
        return {"token": token, "tipo": "Bearer", "expira_en_horas": DURACION_HORAS}

    @portal.get('/yo')
    def perfil(usuario: UsuarioPortal = Depends(sesion_autorizada)):
        return {"id": usuario.id, "usuario": usuario.usuario, "nombre": usuario.nombre, "correo": usuario.correo, "rol": "candidato"}

    @portal.post('/salir')
    def salir(authorization: Optional[str] = Header(default=None), usuario: UsuarioPortal = Depends(sesion_autorizada), db: Session = Depends(db_sesion)):
        token = authorization[7:].strip()
        huella = hashlib.sha256(token.encode('utf-8')).hexdigest()
        sesion = db.query(SesionPortal).filter_by(token_hash=huella, usuario_id=usuario.id).first()
        if sesion:
            db.delete(sesion)
            db.commit()
        return {"mensaje": "Sesión cerrada"}

    from servicios.portal_expediente import agregar_expediente
    agregar_expediente(portal, motor, db_sesion, sesion_autorizada)
    # Nuevas rutas aisladas del candidato: no heredan la API Key del administrador.
    from servicios.portal_oportunidades import agregar_oportunidades
    agregar_oportunidades(portal, motor, db_sesion, sesion_autorizada)

    app.mount('/portal', portal)
    return portal

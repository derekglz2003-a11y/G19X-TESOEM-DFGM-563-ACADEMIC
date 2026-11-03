"""Vacantes públicas, postulación voluntaria y enlace seguro con el pool admin.

Extensión ADITIVA: no altera tablas existentes ni el X-API-Key administrativo.
Registrar cuenta != compartir CV. El CV entra al pool solo con autorización explícita.
Las vacantes existentes NO se publican automáticamente.
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

import database
from database import Base

log = logging.getLogger(__name__)


def ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PublicacionVacante(Base):
    __tablename__ = "portal_publicaciones"
    vacante_id = Column(Integer, ForeignKey("vacantes.id", ondelete="CASCADE"), primary_key=True)
    publicada = Column(Boolean, nullable=False, default=False)
    actualizada_en = Column(DateTime, nullable=False, default=ahora)


class VinculoPortal(Base):
    __tablename__ = "portal_candidato_vinculos"
    usuario_id = Column(Integer, ForeignKey("portal_usuarios.id", ondelete="CASCADE"), primary_key=True)
    candidato_id = Column(Integer, ForeignKey("candidatos.id", ondelete="RESTRICT"), nullable=False, unique=True)
    sincronizado_en = Column(DateTime, nullable=False, default=ahora)


class PostulacionPortal(Base):
    __tablename__ = "portal_postulaciones"
    __table_args__ = (UniqueConstraint("usuario_id", "vacante_id", name="uq_portal_usuario_vacante"),)
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("portal_usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    vacante_id = Column(Integer, ForeignKey("vacantes.id", ondelete="RESTRICT"), nullable=False, index=True)
    candidato_id = Column(Integer, ForeignKey("candidatos.id", ondelete="RESTRICT"), nullable=False, index=True)
    estado = Column(String(40), nullable=False, default="En revisión")
    creada_en = Column(DateTime, nullable=False, default=ahora)
    actualizada_en = Column(DateTime, nullable=False, default=ahora)


class NotificacionPortal(Base):
    """Avisos persistentes privados, independientes de los mensajes de WhatsApp."""
    __tablename__ = "portal_notificaciones"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("portal_usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    vacante_id = Column(Integer, ForeignKey("vacantes.id", ondelete="SET NULL"), nullable=True)
    titulo = Column(String(140), nullable=False)
    mensaje = Column(Text, nullable=False)
    tipo = Column(String(40), nullable=False, default="proceso")
    leida = Column(Boolean, nullable=False, default=False)
    creada_en = Column(DateTime, nullable=False, default=ahora)


TABLAS = [PublicacionVacante.__table__, VinculoPortal.__table__, PostulacionPortal.__table__, NotificacionPortal.__table__]
ESTADOS_ADMIN = {"En revisión", "Preseleccionado", "Descartado", "Entrevista", "Finalista", "Aceptado", "Rechazado"}


class PublicarBody(BaseModel):
    publicada: bool


class EstadoBody(BaseModel):
    estado: str


def _etapa_actual(db: Session, p: PostulacionPortal) -> str:
    if p.estado == "Retirada":
        return "Retirada"
    etapa = db.query(database.Seguimiento).filter_by(
        candidato_id=p.candidato_id, vacante_id=p.vacante_id
    ).first()
    return etapa.estado if etapa else p.estado


def _estado_visible(estado: str) -> str:
    # No expone ranking, evaluación interna ni puntuaciones del resto del pool.
    return {
        "Preseleccionado": "En revisión", "Descartado": "No seleccionado",
        "Rechazado": "No seleccionado", "Entrevista": "Entrevista",
        "Finalista": "Etapa final", "Aceptado": "Seleccionado",
        "Retirada": "Retirada",
    }.get(estado, "En revisión")


def _nuevo_aviso(db: Session, usuario_id: int, vacante_id: Optional[int], titulo: str,
                mensaje: str, tipo: str = "proceso") -> None:
    """Se incluye en la misma transacción de la acción administrativa."""
    db.add(NotificacionPortal(usuario_id=usuario_id, vacante_id=vacante_id,
                              titulo=titulo, mensaje=mensaje, tipo=tipo))


def notificar_cambio_etapa(db: Session, vacante_id: int, candidato_id: int,
                           anterior: str, nuevo: str) -> None:
    """Avisar solo a un postulante y solo si cambia su etapa comunicable."""
    p = db.query(PostulacionPortal).filter_by(vacante_id=vacante_id,
                                              candidato_id=candidato_id).first()
    if p is None or p.estado == "Retirada":
        return
    visible_anterior, visible_nuevo = _estado_visible(anterior), _estado_visible(nuevo)
    if visible_anterior == visible_nuevo:
        return
    vac = db.get(database.Vacante, vacante_id)
    titulo_v = (vac.titulo if vac else "tu vacante")
    mensajes = {
        "Entrevista": ("Avanzaste a entrevista", "Tu postulación avanzó a la etapa de entrevista."),
        "Etapa final": ("Avanzaste a la etapa final", "Tu postulación está en la etapa final de evaluación."),
        "Seleccionado": ("¡Has sido seleccionado!", "El reclutador registró una decisión favorable. Consulta los detalles en tu cuenta."),
        "No seleccionado": ("Resultado de tu postulación", "Tu postulación no fue seleccionada en este proceso."),
        "En revisión": ("Postulación en revisión", "Tu postulación está nuevamente en revisión."),
    }
    if visible_nuevo in mensajes:
        titulo, msg = mensajes[visible_nuevo]
        _nuevo_aviso(db, p.usuario_id, vacante_id, titulo,
                     f"{msg} Vacante: {titulo_v}.", "estado")


def notificar_entrevista(db: Session, vacante_id: Optional[int], candidato_id: int,
                          fecha: str, hora: str, lugar: str, accion: str = "programada") -> None:
    """No revela citas a terceros y requiere postulación para esa vacante."""
    if vacante_id is None:
        return
    p = db.query(PostulacionPortal).filter_by(vacante_id=vacante_id,
                                              candidato_id=candidato_id).first()
    if p is None or p.estado == "Retirada":
        return
    titulos = {"programada": "Entrevista programada", "actualizada": "Tu entrevista fue actualizada",
               "cancelada": "Entrevista cancelada", "confirmada": "Entrevista confirmada"}
    if accion not in titulos:
        return
    vac = db.get(database.Vacante, vacante_id)
    nombre = vac.titulo if vac else "tu postulación"
    detalle = (f"Fecha: {fecha}, hora: {hora}. Modalidad o lugar: {lugar}."
               if accion != "cancelada" else "La entrevista registrada fue cancelada.")
    _nuevo_aviso(db, p.usuario_id, vacante_id, titulos[accion],
                 f"Vacante: {nombre}. {detalle}", "entrevista")


def _asegurar_compartido(db: Session, usuario, exp):
    """Compartición explícita y repetible: siempre existe como máximo un vínculo por usuario."""
    if not exp or len((exp.cv_texto or "").strip()) < 35:
        raise HTTPException(422, "Primero carga un CV legible de al menos 35 caracteres")
    vinculo = db.get(VinculoPortal, usuario.id)
    if vinculo is None:
        candidato = database.Candidato()
        db.add(candidato)
        db.flush()
        vinculo = VinculoPortal(usuario_id=usuario.id, candidato_id=candidato.id)
        db.add(vinculo)
    else:
        candidato = db.get(database.Candidato, vinculo.candidato_id)
        if candidato is None:
            raise HTTPException(409, "El vínculo de tu expediente requiere revisión administrativa")
    _perfil_para_pool(usuario, exp, candidato)
    vinculo.sincronizado_en = ahora()
    # Un CV cambiado no puede conservar compatibilidades antiguas.
    db.query(database.Evaluacion).filter_by(candidato_id=candidato.id).delete(synchronize_session=False)
    return candidato


def _perfil_para_pool(usuario, exp, candidato: database.Candidato) -> None:
    """Copia sólo los datos profesionales autorizados al postularse."""
    candidato.nombre = (usuario.nombre or "Candidato")[:100]
    candidato.nombre_archivo = (exp.cv_nombre or "CV del portal")[:255]
    candidato.email = usuario.correo[:100]
    candidato.telefono = (exp.telefono or "No contiene número")[:50]
    candidato.perfil_destacado = (exp.puesto_deseado or exp.area_interes or "Perfil profesional")[:100]
    candidato.experiencia = (exp.experiencia or exp.resumen_profesional or "")[:5000]
    candidato.skills = (exp.habilidades or "")[:1500]
    candidato.puntos_fuertes = (exp.fortalezas or "")[:1500]
    candidato.texto_completo = (exp.cv_texto or "")[:15000]
    candidato.edad = "No especificada"
    candidato.sexo = "No especificado"
    candidato.desempeno = "Pendiente de evaluación"
    candidato.archivo_bytes = None  # El portal solo conserva texto extraído.


def agregar_oportunidades(portal: FastAPI, motor, db_sesion, sesion_autorizada):
    """Rutas del candidato, protegidas exclusivamente por su propio Bearer."""
    from servicios.portal_auth import UsuarioPortal
    from servicios.portal_expediente import ExpedienteCandidato

    Base.metadata.create_all(bind=motor, tables=TABLAS)

    @portal.get("/vacantes")
    def vacantes_publicadas(usuario: UsuarioPortal = Depends(sesion_autorizada),
                           db: Session = Depends(db_sesion)):
        vacantes = db.query(database.Vacante).join(
            PublicacionVacante, PublicacionVacante.vacante_id == database.Vacante.id
        ).filter(PublicacionVacante.publicada.is_(True)).order_by(database.Vacante.id.desc()).all()
        return [{"id": v.id, "titulo": v.titulo, "descripcion": v.descripcion} for v in vacantes]

    @portal.get("/expediente/compartido")
    def estado_compartido(usuario: UsuarioPortal = Depends(sesion_autorizada),
                          db: Session = Depends(db_sesion)):
        vinculo = db.get(VinculoPortal, usuario.id)
        candidato = db.get(database.Candidato, vinculo.candidato_id) if vinculo else None
        return {"compartido": bool(candidato and (candidato.texto_completo or "").strip()),
                "candidato_id": vinculo.candidato_id if vinculo else None,
                "sincronizado_en": vinculo.sincronizado_en.isoformat() if vinculo and vinculo.sincronizado_en else None}

    @portal.post("/expediente/compartir", status_code=200)
    def compartir_cv(usuario: UsuarioPortal = Depends(sesion_autorizada),
                     db: Session = Depends(db_sesion)):
        exp = db.get(ExpedienteCandidato, usuario.id)
        try:
            candidato = _asegurar_compartido(db, usuario, exp)
            db.commit()
            return {"mensaje": "Tu CV ya aparece entre los expedientes evaluables por reclutamiento",
                    "candidato_id": candidato.id}
        except HTTPException:
            db.rollback()
            raise
        except (IntegrityError, SQLAlchemyError) as exc:
            db.rollback()
            log.exception("No se pudo compartir el CV")
            raise HTTPException(500, "No se pudo compartir el CV") from exc

    @portal.get("/notificaciones")
    def notificaciones(usuario: UsuarioPortal = Depends(sesion_autorizada),
                       db: Session = Depends(db_sesion)):
        avisos = db.query(NotificacionPortal).filter_by(usuario_id=usuario.id).order_by(
            NotificacionPortal.id.desc()).limit(100).all()
        return [{"id": a.id, "titulo": a.titulo, "mensaje": a.mensaje, "tipo": a.tipo,
                 "leida": bool(a.leida), "vacante_id": a.vacante_id,
                 "creada_en": a.creada_en.isoformat() if a.creada_en else None} for a in avisos]

    @portal.put("/notificaciones/{notificacion_id}/leida")
    def leer_notificacion(notificacion_id: int, usuario: UsuarioPortal = Depends(sesion_autorizada),
                         db: Session = Depends(db_sesion)):
        aviso = db.get(NotificacionPortal, notificacion_id)
        if aviso is None or aviso.usuario_id != usuario.id:
            raise HTTPException(404, "Notificación no encontrada")
        aviso.leida = True
        db.commit()
        return {"mensaje": "Notificación marcada como leída"}

    @portal.get("/entrevistas")
    def mis_entrevistas(usuario: UsuarioPortal = Depends(sesion_autorizada),
                       db: Session = Depends(db_sesion)):
        """Una cita solo es visible si pertenece al expediente y a una postulación del dueño."""
        p_list = db.query(PostulacionPortal).filter_by(usuario_id=usuario.id).all()
        respuesta = []
        for p in p_list:
            for link, e in db.query(database.EntrevistaVacante, database.Entrevista).join(
                database.Entrevista, database.Entrevista.id == database.EntrevistaVacante.entrevista_id
            ).filter(database.EntrevistaVacante.vacante_id == p.vacante_id,
                     database.Entrevista.candidato_id == p.candidato_id).all():
                vac = db.get(database.Vacante, p.vacante_id)
                respuesta.append({"id": e.id, "vacante_id": p.vacante_id,
                                  "vacante": vac.titulo if vac else "Vacante",
                                  "fecha": e.fecha, "hora": e.hora, "lugar": e.lugar,
                                  "estado": e.estado})
        return respuesta

    @portal.get("/postulaciones")
    def mis_postulaciones(usuario: UsuarioPortal = Depends(sesion_autorizada),
                         db: Session = Depends(db_sesion)):
        registros = db.query(PostulacionPortal).filter_by(usuario_id=usuario.id).order_by(
            PostulacionPortal.id.desc()
        ).all()
        resultados = []
        for p in registros:
            vac = db.get(database.Vacante, p.vacante_id)
            resultados.append({
                "id": p.id, "vacante_id": p.vacante_id,
                "vacante": vac.titulo if vac else "Vacante no disponible",
                "estado": _estado_visible(_etapa_actual(db, p)),
                "creada_en": p.creada_en.isoformat() if p.creada_en else None,
            })
        return resultados

    @portal.post("/vacantes/{vacante_id}/postularse", status_code=201)
    def postularse(vacante_id: int, usuario: UsuarioPortal = Depends(sesion_autorizada),
                  db: Session = Depends(db_sesion)):
        publicacion = db.get(PublicacionVacante, vacante_id)
        vacante = db.get(database.Vacante, vacante_id)
        if not vacante or not publicacion or not publicacion.publicada:
            raise HTTPException(404, "Esta vacante no está publicada")
        if db.query(PostulacionPortal).filter_by(usuario_id=usuario.id, vacante_id=vacante_id).first():
            raise HTTPException(409, "Ya tienes una postulación registrada para esta vacante")
        exp = db.get(ExpedienteCandidato, usuario.id)
        if not exp or len((exp.cv_texto or "").strip()) < 35:
            raise HTTPException(422, "Primero completa tu expediente y carga un CV legible")
        try:
            candidato = _asegurar_compartido(db, usuario, exp)
            p = PostulacionPortal(usuario_id=usuario.id, vacante_id=vacante_id,
                                  candidato_id=candidato.id, estado="En revisión")
            db.add(p)
            seguimiento = db.query(database.Seguimiento).filter_by(
                vacante_id=vacante_id, candidato_id=candidato.id).first()
            if seguimiento is None:
                db.add(database.Seguimiento(vacante_id=vacante_id, candidato_id=candidato.id, estado="En revisión"))
            else:
                seguimiento.estado = "En revisión"
            _nuevo_aviso(db, usuario.id, vacante_id, "Postulación recibida",
                         f"Recibimos tu postulación para {vacante.titulo}. Puedes consultar el seguimiento desde tu cuenta.",
                         "postulacion")
            db.commit()
            return {"mensaje": "Postulación enviada al reclutador", "postulacion_id": p.id}
        except HTTPException:
            db.rollback()
            raise
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(409, "La postulación ya existe o hay un conflicto de registros") from exc
        except SQLAlchemyError as exc:
            db.rollback()
            log.exception("No se pudo registrar la postulación")
            raise HTTPException(500, "No se pudo registrar la postulación") from exc

    @portal.post("/expediente/compartir-actualizacion")
    def compartir_cv_actualizado(usuario: UsuarioPortal = Depends(sesion_autorizada),
                                db: Session = Depends(db_sesion)):
        """Ruta anterior: conserva compatibilidad, ahora sirve también antes de postularse."""
        exp = db.get(ExpedienteCandidato, usuario.id)
        try:
            candidato = _asegurar_compartido(db, usuario, exp)
            db.commit()
        except HTTPException:
            db.rollback()
            raise
        except SQLAlchemyError as exc:
            db.rollback()
            log.exception("No fue posible compartir el CV actualizado")
            raise HTTPException(500, "No se pudo actualizar el CV compartido") from exc
        return {"mensaje": "CV compartido; se deben recalcular los puntajes anteriores",
                "candidato_id": candidato.id}

    @portal.post("/postulaciones/{postulacion_id}/retirar")
    def retirar(postulacion_id: int, usuario: UsuarioPortal = Depends(sesion_autorizada),
               db: Session = Depends(db_sesion)):
        p = db.get(PostulacionPortal, postulacion_id)
        if not p or p.usuario_id != usuario.id:
            raise HTTPException(404, "Postulación no encontrada")
        if p.estado == "Retirada":
            raise HTTPException(409, "La postulación ya fue retirada")
        etapa = _etapa_actual(db, p)
        if etapa in {"Aceptado", "Rechazado", "Descartado"}:
            raise HTTPException(409, "El proceso ya terminó; contacta al reclutador")
        try:
            p.estado = "Retirada"
            p.actualizada_en = ahora()
            seguimiento = db.query(database.Seguimiento).filter_by(
                candidato_id=p.candidato_id, vacante_id=p.vacante_id
            ).first()
            if seguimiento:
                seguimiento.estado = "Descartado"
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(500, "No se pudo retirar la postulación") from exc
        return {"mensaje": "Postulación retirada"}


def registrar_admin_oportunidades(app: FastAPI, exigir_administrador, motor=None):
    """Rutas ADMIN: X-API-Key obligatorio y sólo metadatos de usuarios del portal."""
    from servicios.portal_auth import UsuarioPortal
    from servicios.portal_expediente import ExpedienteCandidato

    motor = motor or database.engine
    # El API administrativo se registra antes de montar /portal, por lo que
    # estas tablas referenciadas deben existir en una instalación nueva.
    from servicios.portal_auth import SesionPortal
    Base.metadata.create_all(bind=motor, tables=[UsuarioPortal.__table__, SesionPortal.__table__, ExpedienteCandidato.__table__])
    Base.metadata.create_all(bind=motor, tables=TABLAS)
    router = APIRouter(prefix="/api/v1", dependencies=[Depends(exigir_administrador)])

    def db_sesion():
        with Session(motor) as db:
            yield db

    @router.get("/portal-candidatos")
    def usuarios_registrados(db: Session = Depends(db_sesion)):
        usuarios = db.query(UsuarioPortal).order_by(UsuarioPortal.id.desc()).all()
        return [{
            "id": u.id, "usuario": u.usuario, "nombre": u.nombre, "correo": u.correo,
            "activo": bool(u.activo),
            "cv_cargado": bool((exp := db.get(ExpedienteCandidato, u.id)) and exp.cv_texto),
            "expediente_administrativo_id": (
                vinc.candidato_id if (vinc := db.get(VinculoPortal, u.id)) else None
            ),
            "postulaciones": db.query(PostulacionPortal).filter_by(usuario_id=u.id).count(),
        } for u in usuarios]

    @router.post("/invitaciones/{vacante_id}/{candidato_id}")
    def invitar_a_postular(vacante_id: int, candidato_id: int, db: Session = Depends(db_sesion)):
        """Invita a un perfil compartido, sin afirmar que fue contratado ni revelar el score."""
        publicacion = db.get(PublicacionVacante, vacante_id)
        if not publicacion or not publicacion.publicada:
            raise HTTPException(409, "Primero publica la vacante para invitar candidatos")
        vinc = db.query(VinculoPortal).filter_by(candidato_id=candidato_id).first()
        candidato = db.get(database.Candidato, candidato_id)
        if not vinc or not candidato or len((candidato.texto_completo or "").strip()) < 35:
            raise HTTPException(404, "El expediente no está compartido desde el portal")
        if db.query(PostulacionPortal).filter_by(usuario_id=vinc.usuario_id,
                                                vacante_id=vacante_id).first():
            raise HTTPException(409, "Esta cuenta ya tiene una postulación para esa vacante")
        pendiente = db.query(NotificacionPortal).filter_by(usuario_id=vinc.usuario_id,
            vacante_id=vacante_id, tipo="invitacion", leida=False).first()
        if pendiente:
            raise HTTPException(409, "Ya existe una invitación sin leer para esa vacante")
        vac = db.get(database.Vacante, vacante_id)
        _nuevo_aviso(db, vinc.usuario_id, vacante_id, "Te invitaron a conocer una vacante",
                     f"El reclutador te invita a revisar la vacante {vac.titulo}. "
                     "Entra a Vacantes y postúlate si te interesa; esto no es una oferta de contratación.",
                     "invitacion")
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(500, "No se pudo enviar la invitación") from exc
        return {"mensaje": "Invitación disponible en la cuenta del candidato"}

    @router.get("/publicaciones")
    def publicaciones(db: Session = Depends(db_sesion)):
        estados = {p.vacante_id: bool(p.publicada) for p in db.query(PublicacionVacante).all()}
        return [{"vacante_id": v.id, "publicada": estados.get(v.id, False)}
                for v in db.query(database.Vacante).all()]

    @router.put("/publicaciones/{vacante_id}")
    def publicar(vacante_id: int, datos: PublicarBody, db: Session = Depends(db_sesion)):
        vac = db.get(database.Vacante, vacante_id)
        if vac is None:
            raise HTTPException(404, "Vacante no encontrada")
        if datos.publicada:
            if not (vac.titulo or "").strip() or len((vac.descripcion or "").strip()) < 25:
                raise HTTPException(422, "Completa el título y la descripción antes de publicar")
            # No publicar requisitos personales por error.
            from servicios.gemini_ia import limpiar_requisitos_de_vacante
            _, contiene = limpiar_requisitos_de_vacante(vac.descripcion)
            if contiene:
                raise HTTPException(422, "Revisa la descripción: incluye posibles requisitos de edad, sexo o apariencia")
        registro = db.get(PublicacionVacante, vacante_id)
        if registro is None:
            registro = PublicacionVacante(vacante_id=vacante_id)
            db.add(registro)
        registro.publicada = datos.publicada
        registro.actualizada_en = ahora()
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(500, "No se pudo guardar la publicación") from exc
        return {"mensaje": "Vacante publicada" if datos.publicada else "Vacante retirada del portal",
                "publicada": datos.publicada}

    @router.get("/postulaciones-admin")
    def postulaciones_admin(vacante_id: Optional[int] = None, db: Session = Depends(db_sesion)):
        query = db.query(PostulacionPortal)
        if vacante_id is not None:
            query = query.filter_by(vacante_id=vacante_id)
        items = query.order_by(PostulacionPortal.id.desc()).all()
        salida = []
        for p in items:
            usuario = db.get(UsuarioPortal, p.usuario_id)
            vac = db.get(database.Vacante, p.vacante_id)
            salida.append({"id": p.id, "vacante_id": p.vacante_id,
                           "vacante": vac.titulo if vac else "Vacante no disponible",
                           "candidato_id": p.candidato_id,
                           "nombre": usuario.nombre if usuario else "Cuenta no disponible",
                           "correo": usuario.correo if usuario else "",
                           "estado": _etapa_actual(db, p),
                           "creada_en": p.creada_en.isoformat() if p.creada_en else None})
        return salida

    @router.put("/postulaciones-admin/{postulacion_id}/estado")
    def cambiar_estado(postulacion_id: int, datos: EstadoBody, db: Session = Depends(db_sesion)):
        if datos.estado not in ESTADOS_ADMIN:
            raise HTTPException(422, "Estado no permitido")
        p = db.get(PostulacionPortal, postulacion_id)
        if p is None:
            raise HTTPException(404, "Postulación no encontrada")
        if p.estado == "Retirada":
            raise HTTPException(409, "No se puede reactivar una postulación retirada")
        s = db.query(database.Seguimiento).filter_by(vacante_id=p.vacante_id,
                                                     candidato_id=p.candidato_id).first()
        if s is None:
            s = database.Seguimiento(vacante_id=p.vacante_id, candidato_id=p.candidato_id)
            db.add(s)
        anterior = _etapa_actual(db, p)
        notificar_cambio_etapa(db, p.vacante_id, p.candidato_id, anterior, datos.estado)
        s.estado = datos.estado
        p.estado = datos.estado
        p.actualizada_en = ahora()
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(500, "No se pudo cambiar el estado") from exc
        return {"mensaje": "Estado actualizado", "estado": p.estado}

    app.include_router(router)

"""Expediente laboral individual para el portal de candidatos CurriculAi.

Rutas montadas exclusivamente en /portal, con la sesión del propio candidato.
No expone expedientes a terceros ni reutiliza X-API-Key administrativo.
La información de sexo y domicilio NO se manda al motor de ranking.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import Base

MAX_CV_BYTES = 8 * 1024 * 1024
EXTENSIONES = {'pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'webp'}
from servicios.portal_campos import CAMPOS, JORNADAS, MODALIDADES, NIVELES, SEXOS


def _ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExpedienteCandidato(Base):
    __tablename__ = 'portal_expedientes_laborales'
    usuario_id = Column(Integer, ForeignKey('portal_usuarios.id', ondelete='CASCADE'), primary_key=True)
    telefono = Column(String(30), nullable=False, default='')
    sexo = Column(String(40), nullable=False, default='')
    estado = Column(String(90), nullable=False, default='')
    municipio = Column(String(110), nullable=False, default='')
    domicilio_general = Column(String(180), nullable=False, default='')
    nivel_estudios = Column(String(55), nullable=False, default='')
    carrera = Column(String(180), nullable=False, default='')
    institucion = Column(String(180), nullable=False, default='')
    estudios_detalle = Column(Text, nullable=False, default='')
    certificaciones = Column(Text, nullable=False, default='')
    primer_empleo = Column(Boolean, nullable=False, default=False)
    anos_experiencia = Column(Integer, nullable=False, default=0)
    experiencia = Column(Text, nullable=False, default='')
    habilidades = Column(Text, nullable=False, default='')
    fortalezas = Column(Text, nullable=False, default='')
    idiomas = Column(Text, nullable=False, default='')
    resumen_profesional = Column(Text, nullable=False, default='')
    puesto_deseado = Column(String(150), nullable=False, default='')
    area_interes = Column(String(150), nullable=False, default='')
    zonas_preferidas = Column(String(250), nullable=False, default='')
    modalidad = Column(String(30), nullable=False, default='')
    jornada = Column(String(30), nullable=False, default='')
    disponibilidad = Column(String(100), nullable=False, default='')
    cv_nombre = Column(String(255), nullable=False, default='')
    cv_texto = Column(Text, nullable=False, default='')
    cv_actualizado = Column(DateTime, nullable=True)
    actualizado_en = Column(DateTime, nullable=False, default=_ahora)


class ExpedienteCambios(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    nombre: str = Field(min_length=2, max_length=100)
    telefono: str = Field(default='', max_length=30)
    sexo: str = Field(default='', max_length=40)
    estado: str = Field(default='', max_length=90)
    municipio: str = Field(default='', max_length=110)
    domicilio_general: str = Field(default='', max_length=180)
    nivel_estudios: str = Field(default='', max_length=55)
    carrera: str = Field(default='', max_length=180)
    institucion: str = Field(default='', max_length=180)
    estudios_detalle: str = Field(default='', max_length=2000)
    certificaciones: str = Field(default='', max_length=1500)
    primer_empleo: bool = False
    anos_experiencia: int = Field(default=0, ge=0, le=60)
    experiencia: str = Field(default='', max_length=4000)
    habilidades: str = Field(default='', max_length=2000)
    fortalezas: str = Field(default='', max_length=1500)
    idiomas: str = Field(default='', max_length=1000)
    resumen_profesional: str = Field(default='', max_length=1800)
    puesto_deseado: str = Field(default='', max_length=150)
    area_interes: str = Field(default='', max_length=150)
    zonas_preferidas: str = Field(default='', max_length=250)
    modalidad: str = Field(default='', max_length=30)
    jornada: str = Field(default='', max_length=30)
    disponibilidad: str = Field(default='', max_length=100)


class TextoCVEditado(BaseModel):
    texto: str = Field(min_length=20, max_length=15000)


class CVManualRequest(BaseModel):
    """Crear un CV desde los campos del propio perfil, sin subir archivos."""
    model_config = ConfigDict(extra='forbid')
    perfil: ExpedienteCambios
    reemplazar_cv: bool = False


def texto_cv_desde_perfil(perfil: ExpedienteCambios, correo: str) -> str:
    """Texto curricular verificable. Nunca incluye sexo ni domicilio detallado."""
    apartados = [f"Nombre: {perfil.nombre}", f"Correo: {correo}"]
    if perfil.telefono:
        apartados.append(f"Teléfono: {perfil.telefono}")
    zona = ", ".join(p for p in (perfil.municipio, perfil.estado) if p)
    if zona:
        apartados.append(f"Zona general: {zona}")
    campos = [
        ("Perfil profesional", perfil.resumen_profesional),
        ("Puesto deseado", perfil.puesto_deseado),
        ("Área de interés", perfil.area_interes),
        ("Nivel de estudios", perfil.nivel_estudios),
        ("Carrera o formación", perfil.carrera),
        ("Institución", perfil.institucion),
        ("Estudios y logros", perfil.estudios_detalle),
        ("Experiencia laboral", "Busco mi primer empleo" if perfil.primer_empleo else perfil.experiencia),
        ("Años de experiencia", "" if perfil.primer_empleo else str(perfil.anos_experiencia) if perfil.anos_experiencia else ""),
        ("Habilidades", perfil.habilidades),
        ("Fortalezas", perfil.fortalezas),
        ("Idiomas", perfil.idiomas),
        ("Cursos y certificaciones", perfil.certificaciones),
        ("Zonas donde puedo trabajar", perfil.zonas_preferidas),
        ("Modalidad", perfil.modalidad),
        ("Jornada", perfil.jornada),
        ("Disponibilidad", perfil.disponibilidad),
    ]
    for etiqueta, valor in campos:
        if str(valor or '').strip():
            apartados.append(f"{etiqueta}: {str(valor).strip()}")
    return "\n".join(apartados)[:15000]


def _validar_perfil(perfil: ExpedienteCambios) -> None:
    if perfil.sexo not in SEXOS:
        raise HTTPException(422, 'Selecciona una opción válida para el campo opcional de sexo')
    if perfil.nivel_estudios not in NIVELES:
        raise HTTPException(422, 'Selecciona un nivel de estudios válido')
    if perfil.modalidad not in MODALIDADES or perfil.jornada not in JORNADAS:
        raise HTTPException(422, 'Selecciona opciones válidas de modalidad y jornada')



def _avance(registro: dict) -> dict:
    """Solo cuenta datos laborales necesarios; nunca sexo ni domicilio exacto."""
    criterios = [
        ('Nombre completo', bool(registro.get('nombre'))),
        ('Teléfono de contacto', bool(registro.get('telefono'))),
        ('Estado', bool(registro.get('estado'))),
        ('Municipio o alcaldía', bool(registro.get('municipio'))),
        ('Nivel de estudios', bool(registro.get('nivel_estudios'))),
        ('Carrera o formación', bool(registro.get('carrera') or registro.get('estudios_detalle'))),
        ('Experiencia o primer empleo', bool(registro.get('experiencia') or registro.get('primer_empleo'))),
        ('Habilidades técnicas', bool(registro.get('habilidades'))),
        ('Fortalezas', bool(registro.get('fortalezas'))),
        ('Puesto que buscas', bool(registro.get('puesto_deseado'))),
        ('Zonas de trabajo', bool(registro.get('zonas_preferidas'))),
        ('Resumen profesional', bool(registro.get('resumen_profesional'))),
        ('Currículum preparado (creado o subido)', bool(registro.get('cv_cargado'))),
    ]
    listos = sum(int(valor) for _, valor in criterios)
    return {
        'porcentaje': round(100 * listos / len(criterios)),
        'completados': listos,
        'total': len(criterios),
        'pendientes': [nombre for nombre, hecho in criterios if not hecho],
    }


def _respuesta(expediente: Optional[ExpedienteCandidato], usuario):
    salida = {'usuario': usuario.usuario, 'nombre': usuario.nombre, 'correo': usuario.correo}
    for campo in CAMPOS:
        defecto = False if campo == 'primer_empleo' else 0 if campo == 'anos_experiencia' else ''
        salida[campo] = getattr(expediente, campo, defecto) if expediente else defecto
    salida['cv_nombre'] = expediente.cv_nombre if expediente else ''
    salida['cv_cargado'] = bool(expediente and expediente.cv_texto)
    salida['cv_actualizado'] = (expediente.cv_actualizado.isoformat()
                                  if expediente and expediente.cv_actualizado else None)
    salida['completitud'] = _avance(salida)
    return salida


def agregar_expediente(portal: FastAPI, motor, db_sesion, sesion_autorizada):
    """Añade una tabla nueva y rutas exclusivas del dueño de la sesión."""
    from servicios.portal_auth import UsuarioPortal

    if any(getattr(r, 'path', None) == '/expediente' for r in portal.routes):
        return
    Base.metadata.create_all(bind=motor, tables=[ExpedienteCandidato.__table__])

    def _obtener_o_crear(db: Session, usuario_id: int):
        exp = db.get(ExpedienteCandidato, usuario_id)
        if exp is None:
            exp = ExpedienteCandidato(usuario_id=usuario_id)
            db.add(exp)
            db.flush()
        return exp

    @portal.get('/expediente')
    def obtener(usuario: UsuarioPortal = Depends(sesion_autorizada), db: Session = Depends(db_sesion)):
        return _respuesta(db.get(ExpedienteCandidato, usuario.id), usuario)

    @portal.put('/expediente')
    def actualizar(datos: ExpedienteCambios, usuario: UsuarioPortal = Depends(sesion_autorizada),
                   db: Session = Depends(db_sesion)):
        _validar_perfil(datos)
        try:
            exp = _obtener_o_crear(db, usuario.id)
            usuario.nombre = datos.nombre.strip()
            for campo in CAMPOS:
                setattr(exp, campo, getattr(datos, campo))
            exp.actualizado_en = _ahora()
            db.commit()
            db.refresh(exp)
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(500, 'No fue posible guardar el expediente')
        return _respuesta(exp, usuario)

    @portal.post('/expediente/cv/manual')
    def crear_cv_manual(datos: CVManualRequest,
                        usuario: UsuarioPortal = Depends(sesion_autorizada),
                        db: Session = Depends(db_sesion)):
        """Guarda en una transacción el perfil y el CV redactado a mano.

        Una cuenta que ya compartió un CV debe compartir explícitamente
        la nueva versión. Mientras tanto, se retira el texto viejo del ranking.
        """
        perfil = datos.perfil
        _validar_perfil(perfil)
        evidencia = any((perfil.habilidades.strip(), perfil.experiencia.strip(),
                         perfil.estudios_detalle.strip(), perfil.carrera.strip(),
                         perfil.resumen_profesional.strip()))
        if not evidencia:
            raise HTTPException(422, 'Completa estudios, experiencia, resumen o habilidades para crear un CV útil')
        texto = texto_cv_desde_perfil(perfil, usuario.correo)
        if len(texto.strip()) < 35:
            raise HTTPException(422, 'Faltan datos para generar un currículum legible')
        try:
            exp = _obtener_o_crear(db, usuario.id)
            if exp.cv_texto and not datos.reemplazar_cv:
                raise HTTPException(409, 'Ya tienes un CV. Confirma que deseas sustituirlo por la versión creada manualmente')
            usuario.nombre = perfil.nombre.strip()
            for campo in CAMPOS:
                setattr(exp, campo, getattr(perfil, campo))
            exp.cv_nombre = 'CurriculAi_CV_creado_manualmente.txt'
            exp.cv_texto = texto
            exp.cv_actualizado = _ahora()
            exp.actualizado_en = _ahora()

            from servicios.portal_oportunidades import VinculoPortal
            import database
            vinculo = db.get(VinculoPortal, usuario.id)
            if vinculo:
                candidato = db.get(database.Candidato, vinculo.candidato_id)
                if candidato:
                    # No seguir evaluando un CV antiguo ni compartir una versión
                    # nueva sin que el dueño lo autorice explícitamente.
                    candidato.nombre_archivo = ''
                    candidato.texto_completo = ''
                    candidato.skills = ''
                    candidato.experiencia = ''
                    candidato.puntos_fuertes = ''
                    candidato.perfil_destacado = 'Perfil general'
                    db.query(database.Evaluacion).filter_by(candidato_id=candidato.id).delete(
                        synchronize_session=False)
            db.commit()
        except HTTPException:
            db.rollback()
            raise
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(500, 'No se pudo guardar el currículum manual')
        return {'mensaje': 'Tu CV manual y tu perfil se guardaron correctamente',
                'cv_nombre': exp.cv_nombre, 'caracteres': len(texto),
                'requiere_compartir': True}

    @portal.get('/expediente/cv')
    def ver_cv(usuario: UsuarioPortal = Depends(sesion_autorizada), db: Session = Depends(db_sesion)):
        exp = db.get(ExpedienteCandidato, usuario.id)
        return {'nombre': exp.cv_nombre if exp else '', 'texto': exp.cv_texto if exp else '',
                'actualizado': exp.cv_actualizado.isoformat() if exp and exp.cv_actualizado else None}

    @portal.post('/expediente/cv')
    async def reemplazar_cv(archivo: UploadFile = File(...), usuario: UsuarioPortal = Depends(sesion_autorizada),
                           db: Session = Depends(db_sesion)):
        nombre = (archivo.filename or '').replace('\\', '/').rsplit('/', 1)[-1].strip()
        ext = nombre.rsplit('.', 1)[-1].lower() if '.' in nombre else ''
        if not nombre or ext not in EXTENSIONES:
            raise HTTPException(422, 'Formato no válido: usa PDF, DOCX, TXT, JPG, PNG o WEBP')
        contenido = await archivo.read(MAX_CV_BYTES + 1)
        await archivo.close()
        if len(contenido) > MAX_CV_BYTES:
            raise HTTPException(413, 'El CV supera el límite de 8 MB')
        if not contenido:
            raise HTTPException(422, 'El archivo está vacío')
        try:
            from servicios.extractores_cv import extraer_texto_multiformato
            texto = extraer_texto_multiformato(nombre, contenido).strip()
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        except Exception:
            raise HTTPException(422, 'No se pudo extraer el texto del CV. Prueba PDF con texto o DOCX')
        if len(texto) < 25:
            raise HTTPException(422, 'El CV no contiene texto legible suficiente. Revisa el archivo o el OCR')
        try:
            exp = _obtener_o_crear(db, usuario.id)
            exp.cv_nombre = nombre[:255]
            exp.cv_texto = texto[:15000]
            exp.cv_actualizado = _ahora()
            exp.actualizado_en = _ahora()
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(500, 'No se pudo guardar el texto del CV')
        return {'mensaje': 'CV actualizado correctamente', 'cv_nombre': exp.cv_nombre,
                'caracteres_extraidos': len(exp.cv_texto)}

    @portal.put('/expediente/cv')
    def corregir_cv(datos: TextoCVEditado, usuario: UsuarioPortal = Depends(sesion_autorizada),
                   db: Session = Depends(db_sesion)):
        exp = db.get(ExpedienteCandidato, usuario.id)
        if not exp or not exp.cv_texto:
            raise HTTPException(404, 'Primero debes cargar un CV')
        if len(datos.texto.strip()) < 20:
            raise HTTPException(422, 'El texto corregido es demasiado breve')
        try:
            exp.cv_texto = datos.texto.strip()
            exp.cv_actualizado = _ahora()
            exp.actualizado_en = _ahora()
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(500, 'No se pudo corregir el texto del CV')
        return {'mensaje': 'Texto extraído actualizado correctamente'}

    @portal.delete('/expediente/cv')
    def quitar_cv(usuario: UsuarioPortal = Depends(sesion_autorizada), db: Session = Depends(db_sesion)):
        exp = db.get(ExpedienteCandidato, usuario.id)
        if exp:
            try:
                exp.cv_nombre = ''
                exp.cv_texto = ''
                exp.cv_actualizado = None
                exp.actualizado_en = _ahora()
                # No conservar un CV obsoleto en el pool cuando su dueño lo retira.
                # Si ya hubo postulaciones se mantiene el registro/auditoría, pero sin texto evaluable.
                from servicios.portal_oportunidades import VinculoPortal
                import database
                vinculo = db.get(VinculoPortal, usuario.id)
                if vinculo:
                    candidato = db.get(database.Candidato, vinculo.candidato_id)
                    if candidato:
                        candidato.nombre_archivo = ''
                        candidato.texto_completo = ''
                        candidato.skills = ''
                        candidato.experiencia = ''
                        candidato.puntos_fuertes = ''
                        candidato.perfil_destacado = 'Sin CV compartido'
                        db.query(database.Evaluacion).filter_by(candidato_id=candidato.id).delete(
                            synchronize_session=False)
                db.commit()
            except SQLAlchemyError:
                db.rollback()
                raise HTTPException(500, 'No se pudo retirar el CV')
        return {'mensaje': 'CV retirado del expediente'}

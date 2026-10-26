from fastapi import FastAPI, Depends, Form, File, UploadFile, HTTPException, Response
from fastapi.security import APIKeyHeader
import hmac
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import database
from embeddings import calcular_similitud_semantica_lote
from parser import generar_resumen_y_fit, extraer_skills
from servicios.perfil_laboral import texto_laboral_candidato, texto_laboral_vacante
from servicios.extractores_cv import extraer_texto_multiformato, limpiar_texto_para_db
import re
import json
import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

database.Base.metadata.create_all(bind=database.engine)

# --- SEGURIDAD DEL BACKEND (MVP ADMINISTRADOR) ---
# Todas las rutas operativas (GET, POST, PUT, DELETE) requieren la clave.
# Swagger documenta el encabezado mediante el esquema de seguridad de APIKeyHeader.
clave_encabezado = APIKeyHeader(name="X-API-Key", auto_error=False)


def exigir_administrador(clave: Optional[str] = Depends(clave_encabezado)):
    esperada = os.getenv("ADMIN_API_KEY", "").strip()
    if len(esperada) < 32:
        raise HTTPException(
            status_code=503,
            detail="Seguridad sin configurar: ejecuta python scripts/configurar_acceso.py",
        )
    if not clave or not hmac.compare_digest(clave, esperada):
        raise HTTPException(status_code=401, detail="Credenciales de API incorrectas")


app = FastAPI(
    title="CurriculAi API - Optimizador de Filtrado Curricular",
    version="3.8.0",
    dependencies=[Depends(exigir_administrador)],
)

# --- ESQUEMAS PYDANTIC ---
class VacanteResponse(BaseModel):
    id: int
    titulo: str
    descripcion: str

    model_config = ConfigDict(from_attributes=True)

class VacanteUpdate(BaseModel):
    titulo: str
    descripcion: str

class GenerarDescripcionRequest(BaseModel):
    titulo: str
    contexto: str = ""
    descripcion: str = ""


class MensajeWhatsAppCreate(BaseModel):
    """Validación explícita de la bitácora (compatible con el cliente anterior)."""
    candidato_id: Optional[int] = None
    entrevista_id: Optional[int] = None
    telefono: str = ""
    mensaje: str = ""
    estado: str = "Pendiente"
    proveedor: str = "UltraMsg"
    detalle: str = ""
    respuesta: Any = None

class EntrevistaCreate(BaseModel):
    vacante_id: Optional[int] = None
    candidato_id: int
    nombre: str
    puesto: str
    fecha: str
    hora: str
    lugar: Optional[str] = "Google Meet"

class EntrevistaEstadoUpdate(BaseModel):
    estado: str
    tipo_finalista: Optional[str] = "En capacitación"


# --- EXTRACTOR Y MOTOR DE ANÁLISIS DE CVS ---

def extraer_datos_cv_ia(file_bytes: bytes, texto_cv: str, filename: str) -> dict:
    api_key_gemini = os.getenv("GEMINI_API_KEY")
    if api_key_gemini:
        from servicios.gemini_ia import ErrorGemini, extraer_datos_cv_gemini
        try:
            return extraer_datos_cv_gemini(file_bytes, texto_cv, filename)
        except ErrorGemini as exc:
            # En la carga de CV se conserva el extractor local como respaldo;
            # la descripción de vacantes nunca simula una respuesta de IA.
            print(f"[Gemini] Extracción no disponible ({exc.status_code}); usando modo local.")

    # 2. Extractor local cuando el modelo generativo no está configurado.
    # No inventar habilidades ni calificar al candidato sin evidencia.
    texto_low = texto_cv.lower()

    emails = re.findall(r'[a-zA-Z0-9_%.+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', texto_cv)
    email = emails[0] if emails else "No contiene correo"

    telefonos = re.findall(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}', texto_cv)
    telefonos_validos = [t for t in telefonos if len(re.sub(r'\D', '', t)) in [10, 12]]
    telefono = telefonos_validos[0].strip() if telefonos_validos else "No contiene número"

    nombre_clean = filename.rsplit('.', 1)[0].replace("_", " ").replace("-", " ").title()
    match_nombre = re.search(r'(?:nombre(?:\s+candidato)?|candidato)\s*[:|\n\r\-]\s*([a-záéíóúñÁÉÍÓÚÑ\s]{3,40})', texto_cv, re.IGNORECASE)
    if match_nombre:
        posible_nombre = match_nombre.group(1).split('\n')[0].strip().title()
        if not any(k in posible_nombre.lower() for k in ["edad", "datos", "fecha"]):
            nombre_clean = posible_nombre

    puesto_sugerido = "Perfil Operativo"
    if any(k in texto_low for k in ["limpieza", "aseo", "intendencia"]): puesto_sugerido = "Limpieza"
    elif any(k in texto_low for k in ["chofer", "conductor", "operador"]): puesto_sugerido = "Chofer / Conductor"
    elif any(k in texto_low for k in ["almacen", "inventario", "montacargas"]): puesto_sugerido = "Auxiliar de Almacén"

    # El resumen local toma exclusivamente secciones profesionales identificadas.
    from servicios.perfil_laboral import limpiar_texto_laboral
    lineas = [l.strip() for l in limpiar_texto_laboral(texto_cv).splitlines() if len(l.strip()) > 15 and "<</" not in l]
    exp_resumen = " ".join(lineas[:4]) if lineas else ""
    
    return {
        "nombre": nombre_clean,
        "edad": "No especificada",
        "sexo": "No especificado",
        "email": email,
        "telefono": telefono,
        "perfil_destacado": puesto_sugerido,
        "desempeno": "Pendiente de evaluación",
        "experiencia": exp_resumen[:1000],
        "skills": ", ".join(extraer_skills(texto_cv)),
        "puntos_fuertes": "Sin evidencias suficientes para resumir fortalezas; revisar CV.",
    }


# --- ENDPOINTS ---

@app.post("/api/v1/analizar-cvs-masivo")
async def cargar_cvs_al_pool(files: List[UploadFile] = File(...), db: Session = Depends(database.get_db)):
    procesados = 0
    duplicados = 0
    errores = []
    detalles_error = []
    
    for f in files:
        try:
            contenido = await f.read()
            extension = (f.filename or "").rsplit(".", 1)[-1].lower()
            if extension not in {"pdf", "docx", "txt", "png", "jpg", "jpeg", "webp"}:
                raise ValueError("Formato no admitido: usa PDF, DOCX, TXT o imagen; convierte .doc a .docx")
            if len(contenido) > 15 * 1024 * 1024:
                raise ValueError("El archivo supera el límite de 15 MB")
            texto_cv = extraer_texto_multiformato(f.filename, contenido)
            if len(texto_cv.strip()) < 35:
                raise ValueError("No se pudo extraer suficiente texto. Prueba otro PDF o revisa OCR.")
            datos = extraer_datos_cv_ia(contenido, texto_cv, f.filename)
            
            # --- PREVENCIÓN DE DUPLICADOS (Punto 2.2.4) ---
            email_extraido = datos.get("email", "No contiene correo")[:100]
            
            if email_extraido != "No contiene correo":
                existente = db.query(database.Candidato).filter(database.Candidato.email == email_extraido).first()
                if existente:
                    duplicados += 1
                    continue # Saltamos este archivo porque ya existe
            
            experiencia_limpia = limpiar_texto_para_db(datos.get("experiencia", "Sin descripción detallada"))
            
            candidato = database.Candidato(
                nombre_archivo=f.filename[:255],
                nombre=datos.get("nombre", "Desconocido")[:100],
                edad="No especificada",
                sexo="No especificado",
                email=email_extraido,
                telefono=datos.get("telefono", "No contiene número")[:50],
                perfil_destacado=datos.get("perfil_destacado", "Perfil Operativo")[:100],
                desempeno="Pendiente de evaluación",
                experiencia=experiencia_limpia,
                skills=datos.get("skills") or "",
                puntos_fuertes=datos.get("puntos_fuertes") or "",
                texto_completo=texto_cv[:10000] if texto_cv else "Procesado visualmente",
            )
            
            db.add(candidato)
            db.commit() 
            procesados += 1
            
        except Exception as e:
            db.rollback() 
            error_msg = str(e)
            errores.append(f.filename)
            detalles_error.append(f"{f.filename}: {error_msg[:160]}")

    mensaje_final = f"¡{procesados} candidato(s) procesados y almacenados con éxito!"
    if duplicados > 0:
        mensaje_final += f" Se omitieron {duplicados} currículums ya registrados."

    if errores:
        return {
            "mensaje": f"{mensaje_final} Fallaron: {', '.join(errores)}",
            "detalles_tecnicos": detalles_error
        }
        
    return {"mensaje": mensaje_final}

@app.delete("/api/v1/limpiar-pool")
def limpiar_todos_los_candidatos(db: Session = Depends(database.get_db)):
    """Limpia todos los candidatos, no solo el último de una lista."""
    try:
        db.query(database.MensajeWhatsApp).filter(
            database.MensajeWhatsApp.candidato_id.isnot(None)
        ).update({"candidato_id": None}, synchronize_session=False)
        db.query(database.MensajeEntrevista).delete(synchronize_session=False)
        db.query(database.EntrevistaVacante).delete(synchronize_session=False)
        db.query(database.Seguimiento).delete(synchronize_session=False)
        for candidato in db.query(database.Candidato).all():
            db.delete(candidato)
        db.commit()
        return {"mensaje": "Pool completo eliminado; las bitácoras de WhatsApp se conservaron sin candidato"}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo limpiar el pool")


@app.get("/api/v1/candidatos")
def listar_candidatos_pool(db: Session = Depends(database.get_db)):
    candidatos = db.query(database.Candidato).all()
    return [
        {
            "id": c.id,
            "nombre_archivo": c.nombre_archivo,
            "nombre": c.nombre,
            "edad": c.edad,
            "sexo": c.sexo,
            "email": c.email,
            "telefono": c.telefono,
            "perfil_destacado": c.perfil_destacado,
            "desempeno": c.desempeno,
            "experiencia": c.experiencia,
            "skills": c.skills,
            "puntos_fuertes": c.puntos_fuertes,
            "texto_completo": c.texto_completo
        }
        for c in candidatos
    ]


@app.delete("/api/v1/candidatos/{candidato_id}")
def eliminar_candidato(candidato_id: int, db: Session = Depends(database.get_db)):
    """Elimina el expediente, sus evaluaciones y entrevista; conserva la bitácora de WhatsApp desvinculada."""
    candidato = db.get(database.Candidato, candidato_id)
    if candidato is None:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    try:
        db.query(database.MensajeWhatsApp).filter(
            database.MensajeWhatsApp.candidato_id == candidato_id
        ).update({"candidato_id": None}, synchronize_session=False)
        entrevista_ids = [e.id for e in db.query(database.Entrevista.id).filter_by(candidato_id=candidato_id).all()]
        if entrevista_ids:
            db.query(database.MensajeEntrevista).filter(database.MensajeEntrevista.entrevista_id.in_(entrevista_ids)).delete(synchronize_session=False)
            db.query(database.EntrevistaVacante).filter(database.EntrevistaVacante.entrevista_id.in_(entrevista_ids)).delete(synchronize_session=False)
        db.query(database.Seguimiento).filter_by(candidato_id=candidato_id).delete(synchronize_session=False)
        db.delete(candidato)
        db.commit()
        return {"mensaje": "Candidato y expediente eliminados correctamente"}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo eliminar el candidato")


@app.delete("/api/v1/candidatos/{candidato_id}/cv")
def eliminar_cv_candidato(candidato_id: int, db: Session = Depends(database.get_db)):
    """Quita el CV almacenado sin eliminar los datos de contacto del candidato."""
    candidato = db.get(database.Candidato, candidato_id)
    if candidato is None:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")
    try:
        candidato.nombre_archivo = None
        candidato.archivo_bytes = None
        candidato.texto_completo = ""
        # Los resultados anteriores ya no representan un CV vigente.
        for evaluacion in list(candidato.evaluaciones):
            db.delete(evaluacion)
        db.commit()
        return {"mensaje": "CV y evaluaciones eliminados; el candidato permanece registrado"}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo quitar el CV")


@app.post("/api/v1/generar-descripcion")
def generar_descripcion_puesto(req: GenerarDescripcionRequest):
    """Genera una descripción mediante Gemini; no presenta plantillas como IA."""
    if not req.titulo.strip():
        raise HTTPException(status_code=422, detail="Indica el título del puesto")
    from servicios.gemini_ia import ErrorGemini, generar_descripcion_puesto as crear_descripcion
    try:
        return crear_descripcion(req.titulo, req.contexto, req.descripcion)
    except ErrorGemini as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.get("/api/v1/vacantes", response_model=List[VacanteResponse])
def listar_vacantes(db: Session = Depends(database.get_db)):
    return db.query(database.Vacante).all()

@app.post("/api/v1/vacantes", response_model=VacanteResponse)
def crear_vacante(titulo: str = Form(...), descripcion: str = Form(...), db: Session = Depends(database.get_db)):
    vacante = database.Vacante(titulo=titulo, descripcion=descripcion)
    db.add(vacante)
    try:
        db.commit()
        db.refresh(vacante)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo crear la vacante") from exc
    return vacante

@app.put("/api/v1/vacantes/{vacante_id}", response_model=VacanteResponse)
def editar_vacante(vacante_id: int, req: VacanteUpdate, db: Session = Depends(database.get_db)):
    vacante = db.query(database.Vacante).filter(database.Vacante.id == vacante_id).first()
    if not vacante:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    if not req.titulo.strip() or not req.descripcion.strip():
        raise HTTPException(status_code=422, detail="El título y la descripción son obligatorios")
    vacante.titulo = req.titulo.strip()
    vacante.descripcion = req.descripcion.strip()
    try:
        db.commit()
        db.refresh(vacante)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo actualizar la vacante") from exc
    return vacante


@app.delete("/api/v1/vacantes/{vacante_id}")
def eliminar_vacante(vacante_id: int, db: Session = Depends(database.get_db)):
    vacante = db.query(database.Vacante).filter(database.Vacante.id == vacante_id).first()
    if not vacante:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    try:
        db.query(database.EntrevistaVacante).filter_by(vacante_id=vacante_id).delete(synchronize_session=False)
        db.query(database.Seguimiento).filter_by(vacante_id=vacante_id).delete(synchronize_session=False)
        db.delete(vacante)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo eliminar la vacante") from exc
    return {"mensaje": "Vacante eliminada"}
@app.get("/api/v1/ranking/{vacante_id}")
def obtener_ranking(vacante_id: int, db: Session = Depends(database.get_db)):
    try:
        evaluaciones = db.query(database.Evaluacion).filter(database.Evaluacion.vacante_id == vacante_id).order_by(database.Evaluacion.score_similitud.desc()).all()
        resultado = []
        
        for ev in evaluaciones:
            # Forzamos la búsqueda manual del candidato para evitar errores de relaciones en SQLAlchemy
            cand = db.query(database.Candidato).filter(database.Candidato.id == ev.candidato_id).first()
            if cand:
                resultado.append({
                    "candidato_id": cand.id,
                    "candidato_nombre": cand.nombre or "Desconocido",
                    "email": cand.email or "N/A",
                    "telefono": cand.telefono or "N/A",
                    "edad": cand.edad or "N/A",
                    "sexo": cand.sexo or "N/A",
                    "desempeno": cand.desempeno or "N/A",
                    "score_similitud": ev.score_similitud or 0.0,
                    "skills": cand.skills or "N/A",
                    "resumen": ev.resumen_ejecutivo or "N/A",
                    "justificacion": ev.justificacion_fit or "N/A"
                })
        return resultado
        
    except Exception as exc:
        # No fingir ausencia de resultados ante una falla de base de datos.
        # Nunca devolver detalles internos de SQL ni información personal al cliente.
        logger.exception("Falló la consulta del ranking de la vacante %s", vacante_id)
        raise HTTPException(status_code=500, detail="No se pudo consultar el ranking. Intenta nuevamente o revisa el backend.") from exc

@app.post("/api/v1/mensajes-whatsapp")
def registrar_mensaje_whatsapp(payload: MensajeWhatsAppCreate, db: Session = Depends(database.get_db)):
    payload = payload.model_dump()
    try:
        registro = database.MensajeWhatsApp(
            candidato_id=payload.get("candidato_id"),
            telefono=str(payload.get("telefono", "")),
            mensaje=str(payload.get("mensaje", "")),
            estado=str(payload.get("estado", "Pendiente")),
            proveedor=str(payload.get("proveedor", "UltraMsg")),
            detalle=str(payload.get("detalle", "")),
            respuesta_proveedor=json.dumps(payload.get("respuesta"), ensure_ascii=False, default=str),
        )
        db.add(registro)
        db.flush()
        entrevista_id = payload.get("entrevista_id")
        if entrevista_id is not None:
            entrevista = db.get(database.Entrevista, int(entrevista_id))
            if entrevista is None:
                raise HTTPException(status_code=404, detail="Entrevista no encontrada para registrar el mensaje")
            db.add(database.MensajeEntrevista(mensaje_id=registro.id, entrevista_id=entrevista.id))
        db.commit()
        db.refresh(registro)
        return {"id": registro.id, "estado": registro.estado, "creado_en": registro.creado_en.isoformat() if registro.creado_en else None}
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo registrar el mensaje")


@app.get("/api/v1/mensajes-whatsapp")
def listar_mensajes_whatsapp(limit: int = 100, db: Session = Depends(database.get_db)):
    limit = max(1, min(limit, 500))
    registros = db.query(database.MensajeWhatsApp).order_by(database.MensajeWhatsApp.id.desc()).limit(limit).all()
    relaciones = {m.mensaje_id: m.entrevista_id for m in db.query(database.MensajeEntrevista).filter(
        database.MensajeEntrevista.mensaje_id.in_([r.id for r in registros])
    ).all()} if registros else {}
    return [{
        "id": r.id, "candidato_id": r.candidato_id, "entrevista_id": relaciones.get(r.id),
        "telefono": r.telefono, "mensaje": r.mensaje, "estado": r.estado, "proveedor": r.proveedor,
        "detalle": r.detalle, "respuesta_proveedor": r.respuesta_proveedor,
        "creado_en": r.creado_en.isoformat() if r.creado_en else None,
    } for r in registros]


@app.get("/api/v1/entrevistas")
def listar_entrevistas(db: Session = Depends(database.get_db)):
    entrevistas = db.query(database.Entrevista).all()
    mapa = {v.entrevista_id: v.vacante_id for v in db.query(database.EntrevistaVacante).all()}
    return [{
        "id": e.id, "candidato_id": e.candidato_id, "vacante_id": mapa.get(e.id),
        "nombre": e.nombre, "puesto": e.puesto, "fecha": e.fecha, "hora": e.hora,
        "lugar": e.lugar, "estado": e.estado, "tipo_finalista": e.tipo_finalista,
    } for e in entrevistas]

@app.post("/api/v1/entrevistas")
def agendar_entrevista(req: EntrevistaCreate, db: Session = Depends(database.get_db)):
    nueva = database.Entrevista(
        candidato_id=req.candidato_id,
        nombre=req.nombre,
        puesto=req.puesto,
        fecha=req.fecha,
        hora=req.hora,
        lugar=req.lugar
    )
    if db.get(database.Candidato, req.candidato_id) is None:
        raise HTTPException(status_code=404, detail="Candidato inexistente")
    if req.vacante_id is not None and db.get(database.Vacante, req.vacante_id) is None:
        raise HTTPException(status_code=404, detail="Vacante inexistente")
    if db.query(database.Entrevista).filter_by(candidato_id=req.candidato_id).first():
        raise HTTPException(status_code=409, detail="Este candidato ya tiene una entrevista registrada")
    try:
        db.add(nueva)
        db.flush()
        if req.vacante_id is not None:
            db.add(database.EntrevistaVacante(entrevista_id=nueva.id, vacante_id=req.vacante_id))
            registro = db.query(database.Seguimiento).filter_by(vacante_id=req.vacante_id, candidato_id=req.candidato_id).first()
            if registro is None:
                registro = database.Seguimiento(vacante_id=req.vacante_id, candidato_id=req.candidato_id)
                db.add(registro)
            registro.estado = "Entrevista"
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo registrar la entrevista")
    return {"mensaje": "Entrevista guardada", "id": nueva.id}

@app.put("/api/v1/entrevistas/{entrevista_id}/estado")
def actualizar_estado_entrevista(entrevista_id: int, req: EntrevistaEstadoUpdate, db: Session = Depends(database.get_db)):
    entrevista = db.query(database.Entrevista).filter(database.Entrevista.id == entrevista_id).first()
    if not entrevista:
        raise HTTPException(status_code=404, detail="Entrevista no encontrada")
    if req.estado not in {"Programada", "Confirmada", "Realizada", "Cancelada", "No asistió", "En evaluación", "Finalista", "Aceptado", "Rechazado"}:
        raise HTTPException(status_code=422, detail="Estado de entrevista no permitido")
    entrevista.estado = req.estado
    entrevista.tipo_finalista = req.tipo_finalista or ""
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo actualizar el estado de la entrevista") from exc
    return {"mensaje": "Estado actualizado"}

@app.post("/api/v1/evaluar/{vacante_id}")
@app.post("/api/v1/ranking/{vacante_id}/evaluar")
def generar_ranking_vacante(vacante_id: int, db: Session = Depends(database.get_db)):
    """Calcula similitud semántica local y actualiza evaluaciones existentes."""
    vacante = db.get(database.Vacante, vacante_id)
    if vacante is None:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    descripcion = (vacante.descripcion or "").strip()
    if not descripcion:
        raise HTTPException(status_code=422, detail="La vacante necesita una descripción")
    texto_vacante = texto_laboral_vacante(vacante.titulo, descripcion)
    if len(texto_vacante.strip()) < 15:
        raise HTTPException(status_code=422, detail="La vacante debe contener requisitos laborales válidos")

    candidatos = db.query(database.Candidato).all()
    entradas = [(c, texto_laboral_candidato(c)) for c in candidatos]
    validos = [(c, texto) for c, texto in entradas if texto]
    omitidos = len(entradas) - len(validos)

    try:
        # Retira únicamente rankings obsoletos de esta vacante; no borra CV.
        ids_validos = {c.id for c, _ in validos}
        existentes = db.query(database.Evaluacion).filter_by(vacante_id=vacante_id).all()
        for evaluacion in existentes:
            if evaluacion.candidato_id not in ids_validos:
                db.delete(evaluacion)

        if not validos:
            db.commit()
            return {
                "mensaje": "No hay perfiles con experiencia o habilidades laborales suficientes para evaluar",
                "evaluados": 0, "omitidos_sin_perfil": omitidos,
                "omitidos_sin_texto": omitidos, "ranking": [],
            }

        scores = calcular_similitud_semantica_lote(
            texto_vacante, [texto for _, texto in validos]
        )
        if len(scores) != len(validos):
            raise ValueError("El motor devolvió un número incorrecto de puntuaciones")

        for (candidato, texto_profesional), score in zip(validos, scores):
            score = round(max(0.0, min(100.0, float(score))), 2)
            resumen, justificacion = generar_resumen_y_fit(texto_profesional, texto_vacante, score)
            evaluacion = db.query(database.Evaluacion).filter_by(
                vacante_id=vacante_id, candidato_id=candidato.id
            ).first()
            if evaluacion is None:
                evaluacion = database.Evaluacion(vacante_id=vacante_id, candidato_id=candidato.id)
                db.add(evaluacion)
            evaluacion.score_similitud = score
            evaluacion.resumen_ejecutivo = resumen
            evaluacion.justificacion_fit = justificacion
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Falló la evaluación semántica: {type(exc).__name__}") from exc
    return {
        "mensaje": "Similitud laboral calculada; resultados orientativos sujetos a revisión humana",
        "evaluados": len(validos),
        "omitidos_sin_perfil": omitidos,
        "omitidos_sin_texto": omitidos,  # Clave histórica para compatibilidad con interfaz.
        "ranking": obtener_ranking(vacante_id, db),
    }


# --- GESTIÓN DE ETAPAS, EDICIÓN Y CANCELACIÓN (CurriculAi 3.1) ---
ESTADOS_SEGUIMIENTO = {
    "En revisión", "Preseleccionado", "Descartado", "Entrevista",
    "Finalista", "Aceptado", "Rechazado",
}
ESTADOS_ENTREVISTA = {
    "Programada", "Confirmada", "Realizada", "Cancelada", "No asistió",
    "En evaluación", "Finalista", "Aceptado", "Rechazado",
}

class ActualizarSeguimiento(BaseModel):
    estado: str

class CandidatoUpdate(BaseModel):
    nombre: str
    email: str = ""
    telefono: str = ""
    perfil_destacado: str = ""
    experiencia: str = ""
    skills: str = ""

class EntrevistaUpdate(BaseModel):
    puesto: str
    fecha: str
    hora: str
    lugar: str = "Google Meet"

@app.get("/api/v1/seguimientos")
def listar_seguimientos(vacante_id: Optional[int] = None, db: Session = Depends(database.get_db)):
    q = db.query(database.Seguimiento)
    if vacante_id is not None:
        q = q.filter(database.Seguimiento.vacante_id == vacante_id)
    return [{"vacante_id": s.vacante_id, "candidato_id": s.candidato_id, "estado": s.estado}
            for s in q.all()]

@app.put("/api/v1/seguimientos/{vacante_id}/{candidato_id}")
def guardar_seguimiento(vacante_id: int, candidato_id: int, req: ActualizarSeguimiento,
                       db: Session = Depends(database.get_db)):
    if req.estado not in ESTADOS_SEGUIMIENTO:
        raise HTTPException(status_code=422, detail="Estado de seguimiento no permitido")
    if db.get(database.Vacante, vacante_id) is None or db.get(database.Candidato, candidato_id) is None:
        raise HTTPException(status_code=404, detail="Vacante o candidato inexistente")
    registro = db.query(database.Seguimiento).filter_by(vacante_id=vacante_id, candidato_id=candidato_id).first()
    if registro is None:
        registro = database.Seguimiento(vacante_id=vacante_id, candidato_id=candidato_id)
        db.add(registro)
    registro.estado = req.estado
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo guardar el seguimiento")
    return {"mensaje": "Estado guardado correctamente", "estado": registro.estado}

@app.put("/api/v1/candidatos/{candidato_id}")
def actualizar_candidato(candidato_id: int, req: CandidatoUpdate,
                         db: Session = Depends(database.get_db)):
    candidato = db.get(database.Candidato, candidato_id)
    if candidato is None:
        raise HTTPException(status_code=404, detail="Candidato inexistente")
    if not req.nombre.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    candidato.nombre = req.nombre.strip()[:100]
    candidato.email = req.email.strip()[:100]
    candidato.telefono = req.telefono.strip()[:50]
    candidato.perfil_destacado = req.perfil_destacado.strip()[:100]
    candidato.experiencia = req.experiencia.strip()[:5000]
    candidato.skills = req.skills.strip()[:1500]
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="No fue posible editar el candidato")
    return {"mensaje": "Candidato actualizado"}

@app.put("/api/v1/entrevistas/{entrevista_id}")
def editar_entrevista(entrevista_id: int, req: EntrevistaUpdate,
                      db: Session = Depends(database.get_db)):
    entrevista = db.get(database.Entrevista, entrevista_id)
    if entrevista is None:
        raise HTTPException(status_code=404, detail="Entrevista no encontrada")
    from datetime import date as fecha_tipo, time as hora_tipo
    try:
        fecha_tipo.fromisoformat(req.fecha)
        hora_tipo.fromisoformat(req.hora)
    except ValueError:
        raise HTTPException(status_code=422, detail="Fecha u hora inválida")
    if not req.puesto.strip() or not req.lugar.strip():
        raise HTTPException(status_code=422, detail="Puesto y lugar son obligatorios")
    entrevista.puesto = req.puesto.strip()[:200]
    entrevista.fecha = req.fecha
    entrevista.hora = req.hora
    entrevista.lugar = req.lugar.strip()[:500]
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo actualizar la entrevista") from exc
    return {"mensaje": "Entrevista actualizada"}

@app.delete("/api/v1/entrevistas/{entrevista_id}")
def borrar_entrevista(entrevista_id: int, db: Session = Depends(database.get_db)):
    entrevista = db.get(database.Entrevista, entrevista_id)
    if entrevista is None:
        raise HTTPException(status_code=404, detail="Entrevista no encontrada")
    vinculo = db.query(database.EntrevistaVacante).filter_by(entrevista_id=entrevista_id).first()
    if vinculo is not None:
        seguimiento = db.query(database.Seguimiento).filter_by(
            vacante_id=vinculo.vacante_id, candidato_id=entrevista.candidato_id
        ).first()
        if seguimiento is not None and seguimiento.estado in ("Entrevista", "Finalista", "Aceptado", "Rechazado"):
            seguimiento.estado = "En revisión"
    try:
        db.query(database.MensajeEntrevista).filter_by(entrevista_id=entrevista_id).delete(synchronize_session=False)
        db.query(database.EntrevistaVacante).filter_by(entrevista_id=entrevista_id).delete(synchronize_session=False)
        db.delete(entrevista)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo eliminar la entrevista") from exc
    return {"mensaje": "Entrevista eliminada; el candidato se conserva"}

@app.put("/api/v1/entrevistas/{entrevista_id}/decision")
def decidir_entrevista(entrevista_id: int, req: EntrevistaEstadoUpdate,
                      db: Session = Depends(database.get_db)):
    if req.estado not in ESTADOS_ENTREVISTA:
        raise HTTPException(status_code=422, detail="Estado de entrevista no permitido")
    entrevista = db.get(database.Entrevista, entrevista_id)
    if entrevista is None:
        raise HTTPException(status_code=404, detail="Entrevista no encontrada")
    entrevista.estado = req.estado
    # Sólo los finalistas o aceptados conservan esta etiqueta.
    entrevista.tipo_finalista = (req.tipo_finalista or "En evaluación") if req.estado in ("Finalista", "Aceptado") else ""
    vinculo = db.query(database.EntrevistaVacante).filter_by(entrevista_id=entrevista_id).first()
    if vinculo is not None:
        etapa = {
            "Finalista": "Finalista", "Aceptado": "Aceptado", "Rechazado": "Rechazado",
            "En evaluación": "En revisión", "Cancelada": "En revisión",
        }.get(req.estado)
        if etapa:
            seguimiento = db.query(database.Seguimiento).filter_by(vacante_id=vinculo.vacante_id, candidato_id=entrevista.candidato_id).first()
            if seguimiento is None:
                seguimiento = database.Seguimiento(vacante_id=vinculo.vacante_id, candidato_id=entrevista.candidato_id)
                db.add(seguimiento)
            seguimiento.estado = etapa
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="No se pudo guardar la decisión") from exc
    return {"mensaje": "Decisión guardada", "estado": entrevista.estado}

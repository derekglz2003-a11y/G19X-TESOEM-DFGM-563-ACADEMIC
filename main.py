from fastapi import FastAPI, Depends, Form, File, UploadFile, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import database
from embeddings import calcular_similitud_semantica_lote
from parser import generar_resumen_y_fit
import io
import re
import json
import os

from dotenv import load_dotenv
load_dotenv()

database.Base.metadata.create_all(bind=database.engine)

# --- ACTUALIZADO A CURRICULAI ---
app = FastAPI(title="CurriculAi API - Optimizador de Filtrado Curricular", version="2.0.0")

# --- ESQUEMAS PYDANTIC ---
class VacanteResponse(BaseModel):
    id: int
    titulo: str
    descripcion: str

    class Config:
        from_attributes = True

class VacanteUpdate(BaseModel):
    titulo: str
    descripcion: str

class GenerarDescripcionRequest(BaseModel):
    titulo: str
    contexto: str = ""
    descripcion: str = ""

class EntrevistaCreate(BaseModel):
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

def limpiar_texto_para_db(texto: str) -> str:
    """Filtro de Limpieza Extrema para evitar que Supabase/PostgreSQL colapse."""
    if not texto: return ""
    # 1. Eliminar Null Bytes (\x00) que rompen los INSERTS en PostgreSQL
    t = texto.replace('\x00', ' ')
    # 2. Eliminar bloques de código binario de PDF (ej. << /Type /Catalog >>)
    t = re.sub(r'<<.*?>>', '', t, flags=re.DOTALL)
    # 3. Eliminar rutas internas de PDF
    t = re.sub(r'/[A-Za-z0-9_]+', ' ', t)
    # 4. Limitar espacios y saltos de línea
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

def extraer_texto_multiformato(filename: str, file_bytes: bytes) -> str:
    ext = filename.split(".")[-1].lower()
    texto = ""

    if ext == "pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                t = page.extract_text()
                if t: 
                    texto += t + "\n"
        except Exception:
            pass

    elif ext in ["docx", "doc"]:
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            texto = "\n".join([p.text for p in doc.paragraphs if p.text])
        except Exception:
            pass

    elif ext in ["png", "jpg", "jpeg", "webp"]:
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(io.BytesIO(file_bytes))
            texto = pytesseract.image_to_string(img)
        except Exception:
            texto = f"Expediente en imagen: {filename}"

    # Aplicamos la limpieza extrema y limitamos a 15,000 caracteres por seguridad de la BD
    return limpiar_texto_para_db(texto)[:15000]


def extraer_datos_cv_ia(file_bytes: bytes, texto_cv: str, filename: str) -> dict:
    api_key_gemini = os.getenv("GEMINI_API_KEY")
    if api_key_gemini:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key_gemini)
            
            model = genai.GenerativeModel(
                'gemini-1.5-flash',
                generation_config={"response_mime_type": "application/json"}
            )

            ext = filename.split(".")[-1].lower()
            content = []
            
            if ext in ["pdf", "png", "jpg", "jpeg", "webp"]:
                mime_type = "application/pdf" if ext == "pdf" else f"image/{'jpeg' if ext == 'jpg' else ext}"
                content.append({
                    "mime_type": mime_type,
                    "data": file_bytes
                })
            else:
                content.append(f"Texto del Expediente:\n{texto_cv[:10000]}")

            prompt = """
            Eres un extractor de datos de CVs riguroso y exacto. Analiza el siguiente expediente y extrae los datos en JSON.

            REGLAS STRICTAS:
            - Si NO hay número de teléfono válido, coloca exactamente: "No contiene número".
            - Si NO hay correo electrónico, coloca exactamente: "No contiene correo".
            - Extrae el nombre real del candidato.
            - NUNCA extraigas código, números de serie, ni texto basura como '<</Type...'.

            Estructura JSON requerida:
            {
              "nombre": "Nombre completo",
              "edad": "Edad o 'No especificada'",
              "sexo": "Masculino / Femenino / No especificado",
              "email": "Correo o 'No contiene correo'",
              "telefono": "Teléfono a 10 dígitos o 'No contiene número'",
              "perfil_destacado": "Puesto o área detectada",
              "desempeno": "Alto Potencial / Calificado / Experimentado",
              "experiencia": "Resumen limpio de su experiencia laboral. Máximo 2 párrafos. Cero código basura.",
              "skills": "Habilidades clave separadas por coma",
              "puntos_fuertes": "Fortalezas reales (Usa viñetas •)"
            }
            """
            content.append(prompt)
            
            res = model.generate_content(content)
            return json.loads(res.text)
        except Exception as e:
            print(f"[Gemini API Warning] {e}. Usando extractor heurístico.")

    # 2. Extractor Heurístico (Totalmente blindado contra código basura)
    texto_low = texto_cv.lower()

    emails = re.findall(r'[a-zA-Z0-9_%.+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', texto_cv)
    email = emails[0] if emails else "No contiene correo"

    telefonos = re.findall(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}', texto_cv)
    telefonos_validos = [t for t in telefonos if len(re.sub(r'\D', '', t)) in [10, 12]]
    telefono = telefonos_validos[0].strip() if telefonos_validos else "No contiene número"

    edades = re.findall(r'(\d{2})\s*(?:años|anos|edad)', texto_cv, re.IGNORECASE)
    edad = f"{edades[0]}" if edades else "No especificada"

    sexo = "No especificado"
    if re.search(r'\b(masculino|hombre)\b', texto_low): 
        sexo = "Masculino"
    elif re.search(r'\b(femenino|mujer)\b', texto_low): 
        sexo = "Femenino"

    nombre_clean = filename.split('.')[0].replace("_", " ").replace("-", " ").title()
    match_nombre = re.search(r'(?:nombre(?:\s+candidato)?|candidato)\s*[:|\n\r\-]\s*([a-záéíóúñÁÉÍÓÚÑ\s]{3,40})', texto_cv, re.IGNORECASE)
    if match_nombre:
        posible_nombre = match_nombre.group(1).split('\n')[0].strip().title()
        if not any(k in posible_nombre.lower() for k in ["edad", "datos", "fecha"]):
            nombre_clean = posible_nombre

    puesto_sugerido = "Perfil Operativo"
    if any(k in texto_low for k in ["limpieza", "aseo", "intendencia"]): puesto_sugerido = "Limpieza"
    elif any(k in texto_low for k in ["chofer", "conductor", "operador"]): puesto_sugerido = "Chofer / Conductor"
    elif any(k in texto_low for k in ["almacen", "inventario", "montacargas"]): puesto_sugerido = "Auxiliar de Almacén"

    lineas = [l.strip() for l in texto_cv.split("\n") if len(l.strip())> 15 and "<</" not in l]
    exp_resumen = " ".join(lineas[:4]) if lineas else "Trayectoria no especificada en formato legible."
    
    return {
        "nombre": nombre_clean,
        "edad": edad,
        "sexo": sexo,
        "email": email,
        "telefono": telefono,
        "perfil_destacado": puesto_sugerido,
        "desempeno": "Alto Potencial / Calificado",
        "experiencia": exp_resumen[:300],
        "skills": "Compromiso, Responsabilidad, Adaptabilidad",
        "puntos_fuertes": f"• Experiencia en {puesto_sugerido}.\n• Disposición laboral."
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
            texto_cv = extraer_texto_multiformato(f.filename, contenido)
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
                edad=str(datos.get("edad", "No especificada"))[:50],
                sexo=datos.get("sexo", "No especificado")[:50],
                email=email_extraido,
                telefono=datos.get("telefono", "No contiene número")[:50],
                perfil_destacado=datos.get("perfil_destacado", "Perfil Operativo")[:100],
                desempeno=datos.get("desempeno", "Calificado")[:50],
                experiencia=experiencia_limpia,
                skills=datos.get("skills", "Adaptabilidad"),
                puntos_fuertes=datos.get("puntos_fuertes", "Disposición laboral"),
                texto_completo=texto_cv[:10000] if texto_cv else "Procesado visualmente",
            )
            
            db.add(candidato)
            db.commit() 
            procesados += 1
            
        except Exception as e:
            db.rollback() 
            error_msg = str(e)
            print(f"Error fatal guardando {f.filename} en Supabase: {error_msg}")
            errores.append(f.filename)
            detalles_error.append(error_msg)

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
    try:
        db.query(database.MensajeWhatsApp).filter(
            database.MensajeWhatsApp.candidato_id.isnot(None)
        ).update({"candidato_id": None}, synchronize_session=False)
        for candidato in db.query(database.Candidato).all():
            db.delete(candidato)
        db.commit()
        return {"mensaje": "Pool eliminado; se conservaron las bitácoras de WhatsApp sin vinculación"}
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
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="Configura GEMINI_API_KEY en .env")
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
        prompt = ("Redacta en español una descripción profesional de vacante con objetivo, "
                  "responsabilidades, requisitos y habilidades. No inventes sueldo, prestaciones "
                  "ni requisitos discriminatorios. Usa solo los datos suministrados. "
                  f"Puesto: {req.titulo[:150]}\nContexto: {req.contexto[:2000]}\n"
                  f"Descripción inicial: {req.descripcion[:3000]}")
        respuesta = model.generate_content(prompt)
        texto = (getattr(respuesta, "text", None) or "").strip()
        if not texto:
            raise ValueError("Gemini no devolvió contenido")
        return {"descripcion": texto}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"No fue posible generar la descripción con Gemini: {exc}") from exc

@app.get("/api/v1/vacantes", response_model=List[VacanteResponse])
def listar_vacantes(db: Session = Depends(database.get_db)):
    return db.query(database.Vacante).all()

@app.post("/api/v1/vacantes", response_model=VacanteResponse)
def crear_vacante(titulo: str = Form(...), descripcion: str = Form(...), db: Session = Depends(database.get_db)):
    vacante = database.Vacante(titulo=titulo, descripcion=descripcion)
    db.add(vacante)
    db.commit()
    db.refresh(vacante)
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
    db.commit()
    db.refresh(vacante)
    return vacante


@app.delete("/api/v1/vacantes/{vacante_id}")
def eliminar_vacante(vacante_id: int, db: Session = Depends(database.get_db)):
    vacante = db.query(database.Vacante).filter(database.Vacante.id == vacante_id).first()
    if not vacante:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    db.delete(vacante)
    db.commit()
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
        
    except Exception as e:
        print(f"🔴 ERROR AL OBTENER RANKING: {e}")
        return []

@app.post("/api/v1/mensajes-whatsapp")
def registrar_mensaje_whatsapp(payload: dict, db: Session = Depends(database.get_db)):
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
        db.commit()
        db.refresh(registro)
        return {"id": registro.id, "estado": registro.estado, "creado_en": registro.creado_en.isoformat() if registro.creado_en else None}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"No se pudo registrar el mensaje: {exc}")


@app.get("/api/v1/mensajes-whatsapp")
def listar_mensajes_whatsapp(limit: int = 100, db: Session = Depends(database.get_db)):
    limit = max(1, min(limit, 500))
    registros = db.query(database.MensajeWhatsApp).order_by(database.MensajeWhatsApp.id.desc()).limit(limit).all()
    return [{
        "id": r.id, "candidato_id": r.candidato_id, "telefono": r.telefono,
        "mensaje": r.mensaje, "estado": r.estado, "proveedor": r.proveedor,
        "detalle": r.detalle, "respuesta_proveedor": r.respuesta_proveedor,
        "creado_en": r.creado_en.isoformat() if r.creado_en else None,
    } for r in registros]


@app.get("/api/v1/entrevistas")
def listar_entrevistas(db: Session = Depends(database.get_db)):
    return db.query(database.Entrevista).all()

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
    db.add(nueva)
    db.commit()
    return {"mensaje": "Entrevista guardada"}

@app.put("/api/v1/entrevistas/{entrevista_id}/estado")
def actualizar_estado_entrevista(entrevista_id: int, req: EntrevistaEstadoUpdate, db: Session = Depends(database.get_db)):
    entrevista = db.query(database.Entrevista).filter(database.Entrevista.id == entrevista_id).first()
    if not entrevista:
        raise HTTPException(status_code=404, detail="Entrevista no encontrada")
    entrevista.estado = req.estado
    if req.tipo_finalista:
        entrevista.tipo_finalista = req.tipo_finalista
    db.commit()
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
    candidatos = db.query(database.Candidato).all()
    validos = [c for c in candidatos if (c.texto_completo or "").strip() and c.texto_completo != "Procesado visualmente"]
    if not validos:
        return {"mensaje": "No hay candidatos con texto de CV extraído para evaluar", "evaluados": 0, "ranking": []}
    try:
        scores = calcular_similitud_semantica_lote(
            f"{vacante.titulo or ''}. {descripcion}", [c.texto_completo for c in validos]
        )
        for candidato, score in zip(validos, scores):
            score = round(max(0.0, min(100.0, float(score))), 2)
            resumen, justificacion = generar_resumen_y_fit(candidato.texto_completo, descripcion, score)
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
        raise HTTPException(status_code=500, detail=f"Falló la evaluación semántica: {exc}") from exc
    return {"mensaje": "Evaluación semántica completada; resultados orientativos sujetos a revisión humana",
            "evaluados": len(validos), "omitidos_sin_texto": len(candidatos) - len(validos),
            "ranking": obtener_ranking(vacante_id, db)}

from fastapi import FastAPI, Depends, Form, File, UploadFile, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import database
import io
import re
import json
import os

from dotenv import load_dotenv
load_dotenv()

database.Base.metadata.create_all(bind=database.engine)

# --- ACTUALIZADO A CURRICULAI ---
app = FastAPI(title="CurriculAi API - Optimizador de Filtrado Curricular mediante inteligencia artificial", version="2.0.0")

# --- ESQUEMAS PYDANTIC ---
class VacanteResponse(BaseModel):
    id: int
    titulo: str
    descripcion: str

    class Config:
        from_attributes = True

class GenerarDescripcionRequest(BaseModel):
    titulo: str

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
        db.query(database.Evaluacion).delete()
        db.query(database.Candidato).delete()
        db.commit()
        return {"mensaje": "Base de datos reseteada. Todos los CVs han sido eliminados exitosamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al limpiar la BD: {str(e)}")

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
            "puntos_fuertes": c.puntos_fuertes
        }
        for c in candidatos
    ]

@app.post("/api/v1/generar-descripcion")
def generar_descripcion_puesto(req: GenerarDescripcionRequest):
    t = req.titulo.strip().title()
    desc = f"📌 OBJETIVO DEL PUESTO:\nBuscamos un/a {t} proactivo/a para sumarse a nuestro equipo.\n\n🎯 FUNCIONES Y RESPONSABILIDADES:\n• Planificar, ejecutar y supervisar las actividades clave del área de {t}.\n• Optimizar procesos y colaborar con equipos multidisciplinarios.\n\n💼 REQUISITOS:\n• Formación académica afín a {t}.\n• Experiencia previa comprobable.\n• Habilidades de resolución de problemas y trabajo en equipo."
    return {"descripcion": desc}

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
@app.delete("/api/v1/vacantes/{vacante_id}")
def eliminar_vacante(vacante_id: int, db: Session = Depends(database.get_db)):
    vacante = db.query(database.Vacante).filter(database.Vacante.id == vacante_id).first()
    if not vacante:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    db.delete(vacante)
    db.commit()
    return {"mensaje": "Vacante eliminada"}

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
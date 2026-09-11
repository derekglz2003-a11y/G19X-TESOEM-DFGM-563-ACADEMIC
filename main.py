# main.py
import re
from collections import Counter
from typing import List

from database import Candidato, Evaluacion, SessionLocal, Vacante
from embeddings import calcular_similitud_semantica_lote
from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from parser import (
    extraer_email,
    extraer_skills,
    extraer_telefono,
    extraer_texto_pdf,
    generar_resumen_y_fit,
)
from sqlalchemy.orm import Session

app = FastAPI(title="API REST Reclutamiento & IA", version="2.0.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def calcular_score_preciso(score_vectorial_raw: float, skills_cv: list, descripcion_vacante: str) -> float:
    """
    Transforma la similitud semántica cruda (0-100) en un puntaje preciso de negocio:
    1. Filtra la línea base de texto en español (32% de ruido).
    2. Aplica curva exponencial para separar candidatos.
    3. Penaliza perfiles que no compartan palabras clave/habilidades con la vacante.
    """
    UMBRAL_RUIDO = 32.0  # Nivel base de coincidencia gramatical por compartir idioma

    # Paso 1: Eliminar ruido base
    if score_vectorial_raw <= UMBRAL_RUIDO:
        return 0.0

    score_normalizado = (score_vectorial_raw - UMBRAL_RUIDO) / (100.0 - UMBRAL_RUIDO)

    # Paso 2: Curva exponencial (eleva la dispersión)
    score_calibrado = (score_normalizado ** 1.35) * 100.0

    # Paso 3: Penalización por discrepancia absoluta de habilidades
    palabras_vacante = set(re.findall(r'\b[a-zA-Za-áéíóúñÑ]{5,}\b', descripcion_vacante.lower()))
    stopwords = {"experiencia", "requerido", "solicita", "trabajo", "mínimo", "años", "conocimiento", "capacidad", "perfil", "vacante", "puesto", "empresa"}
    kw_vacante = palabras_vacante - stopwords

    skills_cv_lower = {s.lower() for s in skills_cv}
    coincidencias = kw_vacante.intersection(skills_cv_lower)

    # Si la vacante exige habilidades específicas y el CV no tiene ninguna
    if len(kw_vacante) >= 3 and len(coincidencias) == 0:
        score_calibrado *= 0.25  # Castigo severo del 75%

    return round(min(100.0, max(0.0, score_calibrado)), 1)


@app.get("/")
def status():
    return {"status": "online", "version": "2.0.0"}


@app.get("/api/v1/vacantes")
def listar_vacantes(db: Session = Depends(get_db)):
    return db.query(Vacante).order_by(Vacante.id.desc()).all()


@app.post("/api/v1/vacantes")
def crear_vacante(titulo: str = Form(...), descripcion: str = Form(...), db: Session = Depends(get_db)):
    v = Vacante(titulo=titulo, descripcion=descripcion)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@app.delete("/api/v1/vacantes/{vacante_id}")
def eliminar_vacante(vacante_id: int, db: Session = Depends(get_db)):
    vacante = db.query(Vacante).filter(Vacante.id == vacante_id).first()
    if not vacante:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    db.query(Evaluacion).filter(Evaluacion.vacante_id == vacante_id).delete()
    db.delete(vacante)
    db.commit()
    return {"status": "ok"}


@app.post("/api/v1/analizar-cvs/{vacante_id}")
async def analizar_cvs(
    vacante_id: int, 
    modo: str = "detallado",
    files: List[UploadFile] = File(...), 
    db: Session = Depends(get_db)
):
    vacante = db.query(Vacante).filter(Vacante.id == vacante_id).first()
    if not vacante:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    
    datos_candidatos = []
    textos_para_ia = []

    for file in files:
        bytes_data = await file.read()
        texto = extraer_texto_pdf(bytes_data)
        skills_list = extraer_skills(texto, vacante.descripcion)
        
        datos_candidatos.append({
            "nombre": file.filename,
            "email": extraer_email(texto),
            "telefono": extraer_telefono(texto),
            "skills_list": skills_list,
            "skills_str": ", ".join(skills_list),
            "texto": texto,
            "bytes": bytes_data
        })
        textos_para_ia.append(texto)

    scores_raw = calcular_similitud_semantica_lote(vacante.descripcion, textos_para_ia)

    for datos, score_raw in zip(datos_candidatos, scores_raw):
        # 1. Calibrar puntaje eliminando ruido y aplicando penalización por skills
        score_preciso = calcular_score_preciso(score_raw, datos["skills_list"], vacante.descripcion)

        cand = Candidato(
            nombre_archivo=datos["nombre"],
            email=datos["email"],
            telefono=datos["telefono"],
            texto_completo=datos["texto"],
            skills_detectadas=datos["skills_str"],
            pdf_bytes=datos["bytes"]
        )
        db.add(cand)
        db.commit()

        # 2. Generar síntesis basada en el score calibrado y modalidad solicitada
        resumen, fit = generar_resumen_y_fit(datos["texto"], vacante.descripcion, score_preciso, modo=modo)

        ev = Evaluacion(
            vacante_id=vacante.id,
            candidato_id=cand.id,
            score_similitud=score_preciso,
            resumen_ejecutivo=resumen,
            justificacion_fit=fit
        )
        db.add(ev)
        db.commit()

    return {"procesados": len(files)}


@app.get("/api/v1/ranking/{vacante_id}")
def obtener_ranking(vacante_id: int, db: Session = Depends(get_db)):
    evaluaciones = db.query(Evaluacion).filter(Evaluacion.vacante_id == vacante_id).order_by(Evaluacion.score_similitud.desc()).all()
    return [
        {
            "candidato_id": ev.candidato.id,
            "nombre_archivo": ev.candidato.nombre_archivo,
            "score_similitud": ev.score_similitud,
            "email": ev.candidato.email,
            "telefono": ev.candidato.telefono,
            "skills": ev.candidato.skills_detectadas,
            "resumen": ev.resumen_ejecutivo,
            "justificacion": ev.justificacion_fit,
            "extracto": ev.candidato.texto_completo[:400]
        }
        for ev in evaluaciones
    ]


@app.get("/api/v1/candidatos/{candidato_id}/pdf")
def descargar_pdf(candidato_id: int, db: Session = Depends(get_db)):
    cand = db.query(Candidato).filter(Candidato.id == candidato_id).first()
    if not cand or not cand.pdf_bytes:
        raise HTTPException(status_code=404, detail="Archivo PDF no disponible")
    return Response(content=cand.pdf_bytes, media_type="application/pdf")


@app.get("/api/v1/analytics/{vacante_id}")
def obtener_analitica(vacante_id: int, db: Session = Depends(get_db)):
    evals = db.query(Evaluacion).filter(Evaluacion.vacante_id == vacante_id).all()
    if not evals:
        return {"total": 0, "promedio": 0, "skills_frecuentes": {}, "distribucion": {}}

    total = len(evals)
    promedio = round(sum(e.score_similitud for e in evals) / total, 2)
    
    todas_skills = []
    for e in evals:
        if e.candidato.skills_detectadas:
            todas_skills.extend([s.strip() for s in e.candidato.skills_detectadas.split(",") if s.strip()])
            
    conteo_skills = dict(Counter(todas_skills).most_common(10))
    
    distribucion = {
        "Alto (>60%)": len([e for e in evals if e.score_similitud >= 60]),
        "Medio (25-59%)": len([e for e in evals if 25 <= e.score_similitud < 60]),
        "Bajo (<25%)": len([e for e in evals if e.score_similitud < 25])
    }
    
    return {
        "total": total,
        "promedio": promedio,
        "skills_frecuentes": conteo_skills,
        "distribucion": distribucion
    }
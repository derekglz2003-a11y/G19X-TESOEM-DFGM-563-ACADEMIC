"""Embeddings semánticos; único motor de similitud del proyecto."""
import os
from sentence_transformers import SentenceTransformer, util

_model = None
_model_name = None


def obtener_modelo():
    global _model, _model_name
    nombre = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2").strip()
    if _model is None or _model_name != nombre:
        _model = SentenceTransformer(nombre)
        _model_name = nombre
    return _model


def calcular_similitud_semantica_lote(texto_vacante: str, lista_textos_cv: list) -> list:
    if not lista_textos_cv:
        return []
    modelo = obtener_modelo()
    vector_vacante = modelo.encode(texto_vacante, convert_to_tensor=True)
    vectores_cvs = modelo.encode(lista_textos_cv, convert_to_tensor=True)
    scores = util.cos_sim(vector_vacante, vectores_cvs)[0]
    return [round(float(valor) * 100, 2) for valor in scores]

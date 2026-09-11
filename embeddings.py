from sentence_transformers import SentenceTransformer, util

_model = None

def obtener_modelo():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def calcular_similitud_semantica_lote(texto_vacante: str, lista_textos_cv: list) -> list:
    if not lista_textos_cv:
        return []
    model = obtener_modelo()
    emb_vacante = model.encode(texto_vacante, convert_to_tensor=True)
    emb_cvs = model.encode(lista_textos_cv, convert_to_tensor=True)
    scores = util.cos_sim(emb_vacante, emb_cvs)[0]
    return [round(float(score) * 100, 2) for score in scores]
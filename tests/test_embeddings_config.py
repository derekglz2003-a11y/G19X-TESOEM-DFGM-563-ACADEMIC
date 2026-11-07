
import embeddings

MODELO = "sentence-transformers/all-MiniLM-L6-v2"


def preparar_modelo_falso(monkeypatch):
    monkeypatch.setattr(embeddings, "_model", None)
    monkeypatch.setattr(embeddings, "_model_name", None)
    monkeypatch.setattr(
        embeddings,
        "SentenceTransformer",
        lambda nombre: nombre
    )


def test_modelo_predeterminado_variable_vacia(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_MODEL", "")
    preparar_modelo_falso(monkeypatch)

    assert embeddings.obtener_modelo() == MODELO


def test_modelo_predeterminado_variable_ausente(monkeypatch):
    monkeypatch.delenv("EMBEDDINGS_MODEL", raising=False)
    preparar_modelo_falso(monkeypatch)

    assert embeddings.obtener_modelo() == MODELO

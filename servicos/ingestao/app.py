"""
Servico 1 - INGESTAO: recebe documentos, gera embeddings e armazena.

JA PRONTO: indexacao em memoria e a rota de status.
TAREFA 1: persistir o indice em disco para nao perder ao reiniciar.

Rodar: uvicorn servicos.ingestao.app:app --port 8001
"""
from fastapi import FastAPI
from pydantic import BaseModel

from servicos.comum.embeddings import Vetorizador

app = FastAPI(title="Ingestao - C2.A2")

vetorizador = Vetorizador()
INDICE = []


class Documento(BaseModel):
    texto: str
    origem: str = "desconhecida"


@app.post("/indexar")
def indexar(docs: list[Documento]):
    textos = [d.texto for d in docs]
    vetorizador.ajustar([d["texto"] for d in INDICE] + textos or textos)
    INDICE.clear()
    # reindexa tudo com o vocabulario novo
    for d in docs:
        INDICE.append({"texto": d.texto, "origem": d.origem})
    for item in INDICE:
        item["vetor"] = vetorizador.vetorizar(item["texto"])
    return {"indexados": len(INDICE)}


@app.get("/indice")
def indice():
    """Consumido pelo servico de recuperacao."""
    return {"total": len(INDICE),
            "itens": [{"texto": i["texto"], "origem": i["origem"],
                       "vetor": i["vetor"]} for i in INDICE]}


@app.get("/saude")
def saude():
    return {"status": "ok", "documentos": len(INDICE)}

# TAREFA 1: persistir o indice (arquivo ou banco vetorial).

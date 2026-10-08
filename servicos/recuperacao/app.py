"""
Servico 2 - RECUPERACAO: dada uma pergunta, acha os trechos mais relevantes.

TAREFA 2: implementar a busca por similaridade.

Rodar: uvicorn servicos.recuperacao.app:app --port 8002
"""
import os

import requests
from fastapi import FastAPI
from pydantic import BaseModel

from servicos.comum.embeddings import Vetorizador, similaridade

app = FastAPI(title="Recuperacao - C2.A2")
URL_INGESTAO = os.getenv("URL_INGESTAO", "http://localhost:8001")


class Consulta(BaseModel):
    pergunta: str
    top_k: int = 3


@app.post("/buscar")
def buscar(consulta: Consulta):
    """Devolve os top_k trechos mais parecidos com a pergunta."""
    r = requests.get(f"{URL_INGESTAO}/indice", timeout=10)
    r.raise_for_status()
    itens = r.json()["itens"]

    if not itens:
        return {"resultados": []}

    # Cria um vetorizador com o mesmo vocabulario dos documentos.
    vetorizador = Vetorizador()
    textos = [item["texto"] for item in itens]
    vetorizador.ajustar(textos)

    # Transforma a pergunta em vetor.
    vetor_pergunta = vetorizador.vetorizar(consulta.pergunta)

    # Calcula a similaridade da pergunta com cada documento.
    resultados = []

    for item in itens:
        score = similaridade(vetor_pergunta, item["vetor"])

        resultados.append(
            {
                "texto": item["texto"],
                "origem": item["origem"],
                "score": score,
            }
        )

    # Ordena do mais parecido para o menos parecido.
    resultados.sort(key=lambda item: item["score"], reverse=True)

    # Retorna somente os top_k resultados.
    top_k = max(1, consulta.top_k)

    return {
        "resultados": resultados[:top_k]
    }


@app.get("/saude")
def saude():
    return {"status": "ok"}

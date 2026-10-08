"""
Servico 1 - INGESTAO: recebe documentos, gera embeddings e armazena.

TAREFA 1: persistir o indice em disco para nao perder ao reiniciar.

Rodar:
    uvicorn servicos.ingestao.app:app --port 8001
"""

import json
import os

from fastapi import FastAPI
from pydantic import BaseModel

from servicos.comum.embeddings import Vetorizador


app = FastAPI(title="Ingestao - C2.A2")

vetorizador = Vetorizador()

ARQUIVO_INDICE = os.getenv("ARQUIVO_INDICE", "indice.json")

INDICE = []


class Documento(BaseModel):
    texto: str
    origem: str = "desconhecida"


def salvar_indice():
    """Salva os documentos indexados em disco."""
    dados = [
        {
            "texto": item["texto"],
            "origem": item["origem"],
        }
        for item in INDICE
    ]

    with open(ARQUIVO_INDICE, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)


def carregar_indice():
    """Carrega o índice salvo e reconstrói os embeddings."""
    global INDICE

    if not os.path.exists(ARQUIVO_INDICE):
        return

    with open(ARQUIVO_INDICE, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    if not dados:
        INDICE = []
        return

    textos = [item["texto"] for item in dados]

    vetorizador.ajustar(textos)

    INDICE = []

    for item in dados:
        INDICE.append(
            {
                "texto": item["texto"],
                "origem": item["origem"],
                "vetor": vetorizador.vetorizar(item["texto"]),
            }
        )


carregar_indice()


@app.post("/indexar")
def indexar(docs: list[Documento]):
    textos = [d.texto for d in docs]

    documentos = [
        {
            "texto": d.texto,
            "origem": d.origem,
        }
        for d in docs
    ]

    # Mantem os documentos ja existentes e adiciona os novos.
    todos = [
        {
            "texto": item["texto"],
            "origem": item["origem"],
        }
        for item in INDICE
    ]

    todos.extend(documentos)

    if not todos:
        return {"indexados": 0}

    # Reconstrói o vocabulario com todos os documentos.
    vetorizador.ajustar([item["texto"] for item in todos])

    INDICE.clear()

    for item in todos:
        INDICE.append(
            {
                "texto": item["texto"],
                "origem": item["origem"],
                "vetor": vetorizador.vetorizar(item["texto"]),
            }
        )

    salvar_indice()

    return {"indexados": len(INDICE)}


@app.get("/indice")
def indice():
    """Consumido pelo servico de recuperacao."""
    return {
        "total": len(INDICE),
        "itens": [
            {
                "texto": item["texto"],
                "origem": item["origem"],
                "vetor": item["vetor"],
            }
            for item in INDICE
        ],
    }


@app.get("/saude")
def saude():
    return {
        "status": "ok",
        "documentos": len(INDICE),
    }

"""
Servico 3 - GERACAO: recebe perguntas, usa mensageria para recuperacao
e chama o LLM protegido por circuit breaker.

Rodar: uvicorn servicos.geracao.app:app --port 8003
"""

import json
import os
import time
import uuid

import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from servicos.comum.circuit_breaker import CircuitBreaker, CircuitoAberto
from servicos.comum.llm import gerar


app = FastAPI(title="Geracao - C2.A2")

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0"
)

FILA_PERGUNTAS = "fila:perguntas"

redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True
)

disjuntor = CircuitBreaker(
    limite_falhas=3,
    espera_segundos=20
)


class Pergunta(BaseModel):
    pergunta: str


def enviar_para_fila(pergunta: str, top_k: int = 3):
    """Envia uma pergunta para o worker através do Redis."""

    resposta_id = str(uuid.uuid4())

    tarefa = {
        "pergunta": pergunta,
        "top_k": top_k,
        "resposta_id": resposta_id
    }

    redis_client.rpush(
        FILA_PERGUNTAS,
        json.dumps(tarefa)
    )

    return resposta_id


def aguardar_resultado(resposta_id: str, timeout: int = 15):
    """Aguarda o resultado produzido pelo worker."""

    chave = f"resposta:{resposta_id}"
    inicio = time.time()

    while time.time() - inicio < timeout:
        resultado = redis_client.get(chave)

        if resultado:
            redis_client.delete(chave)
            return json.loads(resultado)

        time.sleep(0.2)

    raise TimeoutError(
        "Tempo limite aguardando resposta do worker."
    )


@app.post("/perguntar")
def perguntar(p: Pergunta):

    try:
        resposta_id = enviar_para_fila(
            p.pergunta,
            top_k=3
        )

        resultado = aguardar_resultado(
            resposta_id
        )

    except Exception as erro:
        raise HTTPException(
            status_code=503,
            detail=f"Falha na mensageria: {erro}"
        )

    if resultado["status"] != "ok":
        raise HTTPException(
            status_code=503,
            detail=resultado.get(
                "mensagem",
                "Falha no serviço de recuperação."
            )
        )

    contexto = [
        item["texto"]
        for item in resultado["resultados"]
    ]

    try:
        resposta = disjuntor.chamar(
            gerar,
            p.pergunta,
            contexto
        )

    except CircuitoAberto:
        raise HTTPException(
            status_code=503,
            detail=(
                "Serviço de LLM temporariamente indisponível: "
                "disjuntor aberto."
            )
        )

    return {
        "pergunta": p.pergunta,
        "resposta": resposta,
        "contexto": contexto
    }


@app.get("/saude")
def saude():
    return {
        "status": "ok",
        "disjuntor": disjuntor.estado
    }

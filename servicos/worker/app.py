"""
Worker de mensageria - C2.A2.

Consome tarefas da fila Redis e consulta o servico de recuperacao.
"""

import json
import os
import time
import uuid

import redis
import requests


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
URL_RECUPERACAO = os.getenv(
    "URL_RECUPERACAO",
    "http://localhost:8002"
)

FILA_PERGUNTAS = "fila:perguntas"
TIMEOUT_RECUPERACAO = 10

redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True
)


def processar_tarefa(tarefa):
    """Consulta a recuperacao e grava o resultado no Redis."""

    pergunta = tarefa["pergunta"]
    top_k = tarefa.get("top_k", 3)
    resposta_id = tarefa["resposta_id"]

    try:
        r = requests.post(
            f"{URL_RECUPERACAO}/buscar",
            json={
                "pergunta": pergunta,
                "top_k": top_k
            },
            timeout=TIMEOUT_RECUPERACAO,
        )

        r.raise_for_status()

        resultado = {
            "status": "ok",
            "resultados": r.json()["resultados"]
        }

    except Exception as erro:
        resultado = {
            "status": "erro",
            "mensagem": str(erro)
        }

    redis_client.set(
        f"resposta:{resposta_id}",
        json.dumps(resultado),
        ex=60,
    )


def executar():
    print("Worker iniciado. Aguardando tarefas...")

    while True:
        item = redis_client.blpop(
            FILA_PERGUNTAS,
            timeout=5
        )

        if item is None:
            continue

        _, payload = item

        try:
            tarefa = json.loads(payload)
            processar_tarefa(tarefa)
        except Exception as erro:
            print(f"Erro ao processar tarefa: {erro}")


if __name__ == "__main__":
    executar()

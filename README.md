# C2.A2 — RAG Distribuído em Microsserviços

Projeto desenvolvido para a disciplina **Sistemas Distribuídos e Computação em Nuvem**.

O objetivo deste projeto é implementar uma arquitetura de **RAG (Retrieval-Augmented Generation)** distribuída em microsserviços, utilizando persistência do índice, busca por similaridade, mensageria com Redis, processamento assíncrono por Worker e Circuit Breaker para proteção da chamada ao LLM.

## 1. Arquitetura

A aplicação é composta pelos seguintes componentes:

- Ingestão — responsável por receber e persistir os documentos utilizados pelo sistema.
- Recuperação — responsável por realizar a busca por similaridade utilizando TF-IDF e similaridade de cosseno.
- Geração — responsável por receber a pergunta, solicitar a recuperação dos documentos e gerar a resposta utilizando o contexto recuperado.
- Worker — responsável por consumir mensagens da fila Redis e realizar a comunicação com o serviço de recuperação.
- Redis — utilizado como mecanismo de mensageria e armazenamento temporário das respostas.
- Circuit Breaker — utilizado para proteger a comunicação com o serviço de LLM.
- Docker Compose — utilizado para executar todos os componentes da arquitetura de forma integrada.

### Diagrama da arquitetura

mermaid
flowchart LR
    C[Cliente] --> G[Geração :8003]
    G -->|RPUSH pergunta| R[(Redis)]
    R --> W[Worker]
    W -->|POST /buscar| REC[Recuperação :8002]
    REC -->|GET /indice| ING[Ingestão :8001]
    W -->|SET resposta:id| R
    G --> CB[Circuit Breaker]
    CB --> L[LLM]

### 2. FLuxo da Aplicacao
2. Fluxo da aplicação

O funcionamento da aplicação ocorre através de uma sequência de comunicação entre os microsserviços.

Primeiramente, o cliente envia uma pergunta para o serviço de Geração. O serviço cria um identificador para a solicitação e envia a pergunta para uma fila no Redis.

O Worker permanece aguardando novas mensagens nessa fila. Quando recebe uma pergunta, ele realiza uma solicitação para o serviço de Recuperação.

O serviço de Recuperação consulta o índice mantido pelo serviço de Ingestão. Os documentos são comparados com a pergunta utilizando TF-IDF e similaridade de cosseno.

Após identificar os documentos mais relevantes, o Worker armazena o resultado temporariamente no Redis. O serviço de Geração recupera esse resultado e utiliza os documentos encontrados como contexto para a geração da resposta.

Antes de realizar a chamada ao LLM, o serviço de Geração utiliza o Circuit Breaker para controlar possíveis falhas.

Finalmente, a resposta gerada é devolvida ao cliente.
Cliente
   |
   v
Geração
   |
   v
Redis - fila:perguntas
   |
   v
Worker
   |
   v
Recuperação
   |
   v
Ingestão
   |
   v
Índice persistido

Worker
   |
   v
Redis - resultado
   |
   v
Geração
   |
   v
Circuit Breaker
   |
   v
LLM
   |
   v
Resposta ao cliente

### 3. Serviço de Ingestão

O serviço de Ingestão é executado na porta 8001.

Sua principal função é receber os documentos utilizados pela aplicação e manter o índice de documentos.

O serviço possui o endpoint:

POST /indexar

O endpoint recebe uma lista de documentos contendo o texto e sua origem.

Exemplo:

[
  {
    "texto": "A computacao em nuvem permite executar recursos de processamento pela internet.",
    "origem": "aula1.txt"
  },
  {
    "texto": "Microsservicos dividem uma aplicacao em servicos independentes.",
    "origem": "aula2.txt"
  }
]

O índice é armazenado no arquivo:

dados/indice.json

O serviço também possui um endpoint de saúde:

GET /saude

Esse endpoint permite verificar se o serviço está funcionando e quantos documentos estão atualmente indexados.
### 4. Serviço de Recuperação

O serviço de Recuperação é executado na porta 8002.

Sua função é receber uma pergunta e encontrar os documentos mais semelhantes disponíveis no índice.

O endpoint utilizado é:

POST /buscar

Exemplo de requisição:

{
  "pergunta": "O que é computacao em nuvem?",
  "top_k": 2
}

O serviço realiza a vetorização dos documentos utilizando TF-IDF e calcula a similaridade de cosseno entre a pergunta e cada documento.

Os resultados são ordenados de acordo com o score de similaridade.

Dessa forma, os documentos mais relevantes são enviados para o serviço de Geração para serem utilizados como contexto.

5. Serviço de Geração

O serviço de Geração é executado na porta 8003.

Esse serviço é responsável por coordenar o processo de geração da resposta.

O endpoint principal é:

POST /perguntar

Exemplo:

{
  "pergunta": "O que é computacao em nuvem?"
}

Ao receber a pergunta, o serviço envia uma tarefa para a fila do Redis.

Depois disso, aguarda o processamento realizado pelo Worker.

Quando o resultado da recuperação é recebido, os documentos encontrados são utilizados como contexto para a geração da resposta.

O serviço então realiza a chamada ao LLM utilizando o Circuit Breaker e retorna a resposta final ao cliente.

### 6. Worker

O Worker é responsável pelo processamento assíncrono das solicitações.

Ele não possui uma porta HTTP própria.

O Worker permanece aguardando mensagens na fila:

fila:perguntas

Quando uma mensagem é recebida, o Worker:

Lê a pergunta enviada pelo serviço de Geração.
Envia a pergunta para o serviço de Recuperação.
Recebe os documentos mais relevantes.
Armazena o resultado temporariamente no Redis.
Permite que o serviço de Geração recupere o resultado.

Essa abordagem permite que a recuperação seja realizada por meio de mensageria, evitando uma chamada direta entre Geração e Recuperação.

### 7. Mensageria com Redis

O Redis foi utilizado como mecanismo de mensageria entre os componentes.

A fila utilizada é:

fila:perguntas

O serviço de Geração adiciona novas tarefas na fila utilizando RPUSH.

O Worker remove e processa as tarefas utilizando BLPOP.

Após realizar a recuperação dos documentos, o Worker armazena o resultado temporariamente em uma chave do Redis:

resposta:<id>

O serviço de Geração utiliza esse identificador para localizar o resultado correspondente à pergunta enviada.

Essa implementação demonstra comunicação assíncrona utilizando uma fila de mensagens.

### 8. Persistência do índice

Uma das funcionalidades implementadas no projeto foi a persistência do índice de documentos.

O índice é armazenado em:

dados/indice.json

No Docker Compose, o diretório local ./dados é montado no container utilizado pelo serviço de Ingestão.

Isso permite que os dados permaneçam armazenados mesmo quando o container é reiniciado.

Durante os testes, o serviço de Ingestão foi reiniciado utilizando:

docker compose restart ingestao

Após o reinício, os documentos anteriormente indexados continuaram disponíveis.

Esse teste confirmou o funcionamento da persistência do índice.

### 9. Busca por similaridade

A busca dos documentos utiliza TF-IDF.

O TF-IDF transforma os textos em representações numéricas que podem ser comparadas.

Depois da vetorização, é utilizada a similaridade de cosseno para determinar o grau de semelhança entre a pergunta e cada documento.

Os documentos são ordenados pelo score obtido.

Por exemplo, uma pergunta relacionada a computação em nuvem apresenta maior similaridade com o documento que contém informações sobre computação em nuvem do que com documentos sobre outros assuntos.

O mecanismo utilizado está implementado no arquivo:

servicos/comum/embeddings.py
### 10. Circuit Breaker

O serviço de Geração utiliza o padrão Circuit Breaker para proteger a comunicação com o LLM.

A configuração utilizada é:

Limite de falhas: 3
Tempo de espera: 20 segundos

Quando ocorrem três falhas consecutivas na chamada ao LLM, o Circuit Breaker muda seu estado para aberto.

Enquanto estiver aberto, novas chamadas ao serviço são recusadas temporariamente.

Esse mecanismo evita que a aplicação continue realizando chamadas para um serviço que esteja indisponível.

O estado do Circuit Breaker pode ser consultado através do endpoint:

GET /saude

Também foi realizado um teste simulando três falhas consecutivas. Após a terceira falha, o circuito foi aberto e a chamada seguinte foi recusada.

###  11. LLM

O projeto possui suporte à configuração de um LLM por meio de variáveis de ambiente.

As principais variáveis utilizadas são:

LLM_API_KEY
LLM_API_URL
LLM_MODELO
LLM_TIMEOUT

Durante os testes, a variável LLM_API_KEY não foi configurada.

Nesse cenário, o código-base utiliza um modo simulado, permitindo testar o funcionamento do RAG sem depender de uma API externa.

O modo simulado gera uma resposta utilizando a pergunta recebida e os documentos recuperados.

Nenhuma chave de API é armazenada diretamente no código-fonte.

### 12. Docker

A aplicação foi preparada para execução utilizando Docker e Docker Compose.

Cada serviço possui seu próprio Dockerfile.

A estrutura é:

servicos/
├── ingestao/
│   └── Dockerfile
├── recuperacao/
│   └── Dockerfile
├── geracao/
│   └── Dockerfile
└── worker/
    └── Dockerfile

O Redis utiliza a imagem:

redis:7-alpine

Toda a arquitetura pode ser iniciada com:

docker compose up -d --build

Para verificar o estado dos containers:

docker compose ps

Os principais containers utilizados são:

rag-ingestao
rag-recuperacao
rag-geracao
rag-worker
rag-redis

## 13. Execução e testes
Iniciar a aplicação
docker compose up -d --build
Verificar os containers
docker compose ps
Verificar o serviço de Ingestão
curl http://localhost:8001/saude
Verificar o serviço de Recuperação
curl http://localhost:8002/saude
Verificar o serviço de Geração
curl http://localhost:8003/saude
Indexar documentos
curl -X POST http://localhost:8001/indexar \
  -H "Content-Type: application/json" \
  -d '[
    {
      "texto": "A computacao em nuvem permite executar recursos de processamento pela internet.",
      "origem": "aula1.txt"
    },
    {
      "texto": "Microsservicos dividem uma aplicacao em servicos independentes.",
      "origem": "aula2.txt"
    },
    {
      "texto": "O Redis pode ser utilizado como mecanismo de mensageria entre servicos.",
      "origem": "aula3.txt"
    }
  ]'
Testar a recuperação
curl -X POST http://localhost:8002/buscar \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "O que é computacao em nuvem?",
    "top_k": 2
  }'
Testar o fluxo completo
curl -X POST http://localhost:8003/perguntar \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "O que é computacao em nuvem?"
  }'

O resultado final apresenta a pergunta, a resposta gerada e o contexto utilizado.

### 14. Validações realizadas

Durante o desenvolvimento foram realizados testes para verificar o funcionamento dos principais componentes.

Foram validados:

instalação das dependências;
funcionamento dos microsserviços;
persistência do índice;
indexação dos documentos;
busca por similaridade;
utilização de TF-IDF;
utilização da similaridade de cosseno;
funcionamento da fila Redis;
funcionamento do Worker;
comunicação entre Worker e Recuperação;
fluxo completo de RAG;
execução através do Docker Compose;
persistência após reinicialização do container;
funcionamento do modo simulado do LLM;
utilização de variáveis de ambiente;
funcionamento do Circuit Breaker após falhas consecutivas.
15. Estrutura do projeto
sd-2026-2-kit-c2a2/
│
├── documentos/
│
├── dados/
│   └── indice.json
│
├── servicos/
│   │
│   ├── comum/
│   │   ├── circuit_breaker.py
│   │   ├── embeddings.py
│   │   ├── llm.py
│   │   └── __init__.py
│   │
│   ├── ingestao/
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   └── __init__.py
│   │
│   ├── recuperacao/
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   └── __init__.py
│   │
│   ├── geracao/
│   │   ├── app.py
│   │   ├── Dockerfile
│   │   └── __init__.py
│   │
│   └── worker/
│       ├── app.py
│       ├── Dockerfile
│       └── __init__.py
│
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md

### 16. Tecnologias utilizadas
Python 3.12
FastAPI
Uvicorn
Redis
Docker
Docker Compose
NumPy
Scikit-learn
TF-IDF
Similaridade de cosseno
Circuit Breaker
Microsserviços
Mensageria assíncrona
JSON para persistência do índice

### 17. Conclusão

O projeto implementa uma arquitetura distribuída de RAG utilizando microsserviços independentes.

A separação entre os serviços de Ingestão, Recuperação e Geração permite organizar as responsabilidades da aplicação de forma independente.

A solução também implementa persistência do índice, busca por similaridade utilizando TF-IDF e similaridade de cosseno, comunicação assíncrona utilizando Redis, processamento por Worker e proteção contra falhas utilizando Circuit Breaker.

A utilização do Docker Compose permite executar os componentes da arquitetura de forma integrada e reproduzível.

O modo simulado do LLM possibilita validar o funcionamento do fluxo completo sem depender de uma API externa.

Com isso, o projeto demonstra os principais conceitos relacionados a microsserviços, sistemas distribuídos, mensageria, persistência, recuperação de informação, tolerância a falhas e computação em containers.

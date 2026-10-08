FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY servicos ./servicos
COPY documentos ./documentos

CMD ["uvicorn", "servicos.recuperacao.app:app", "--host", "0.0.0.0", "--port", "8002"]

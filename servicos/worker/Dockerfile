# =====================================================================
# Imagem Base Oficial do Python (Versao leve Slim)
# =====================================================================
FROM python:3.12-slim

# =====================================================================
# Diretorio de Trabalho dentro do Container
# =====================================================================
WORKDIR /app

# =====================================================================
# Instalacao de Dependencias (Copiado primeiro para otimizar o cache)
# =====================================================================
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# =====================================================================
# Copia do codigo-fonte e dos documentos do projeto
# =====================================================================
COPY servicos ./servicos
COPY documentos ./documentos

# =====================================================================
# Comando de Inicializacao do Worker de Mensageria
# =====================================================================
CMD ["python", "servicos/worker/app.py"]

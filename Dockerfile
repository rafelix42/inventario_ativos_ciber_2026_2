# Imagem da API de Inventário de Ativos de TI.
#
# Construir e executar (veja também docker-compose.yml):
#   docker build -t inventario-api .
#   docker run -p 8000:8000 -v ./data:/app/data -v ./logs:/app/logs inventario-api

FROM python:3.13-slim

# Não gera arquivos .pyc e mostra os logs na hora (sem buffer).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# As dependências são instaladas antes de copiar o código: assim o Docker
# reaproveita esta etapa (cache) quando só o código muda.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY main.py seed_dados_teste.py ./

# Por segurança, a API não roda como root. O UID 1000 costuma ser o do
# usuário principal do Linux, o que evita problemas de permissão nas pastas
# data/ e logs/ montadas do computador hospedeiro.
RUN useradd --uid 1000 --create-home inventario \
    && mkdir -p data logs \
    && chown inventario:inventario data logs
USER inventario

EXPOSE 8000

# O Docker consulta esta rota periodicamente; se ela parar de responder, o
# container aparece como "unhealthy" em 'docker ps'.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/saude')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

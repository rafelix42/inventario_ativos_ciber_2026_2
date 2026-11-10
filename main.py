"""Ponto de entrada da API de Inventário de Ativos de TI.

Lê as configurações das variáveis de ambiente, configura o logging e cria a
aplicação FastAPI. Toda a lógica fica organizada dentro do pacote 'app'.

Executar localmente:
    python3 main.py                 (http://127.0.0.1:8000/docs)
No container, o Dockerfile executa:
    uvicorn main:app --host 0.0.0.0 --port 8000

Variáveis de ambiente (todas opcionais):
    CAMINHO_DO_BANCO     arquivo SQLite (padrão: data/inventario.db)
    ORIGENS_PERMITIDAS   endereços do frontend separados por vírgula
                         (padrão: http://localhost:5173,http://localhost:3000)
    HOST / PORTA         usados só com 'python3 main.py'
"""

import os
from pathlib import Path
from typing import List

import uvicorn

from app.api.aplicacao import ORIGENS_PADRAO, criar_aplicacao
from app.logging_config import configurar_logging
from app.repositories.database import CAMINHO_PADRAO_DO_BANCO


def _ler_origens_permitidas() -> List[str]:
    texto = os.environ.get("ORIGENS_PERMITIDAS", ",".join(ORIGENS_PADRAO))
    return [origem.strip() for origem in texto.split(",") if origem.strip()]


configurar_logging()

app = criar_aplicacao(
    caminho_do_banco=Path(os.environ.get("CAMINHO_DO_BANCO", CAMINHO_PADRAO_DO_BANCO)),
    origens_permitidas=_ler_origens_permitidas(),
)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORTA", "8000")),
    )

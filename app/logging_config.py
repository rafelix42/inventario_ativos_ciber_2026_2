"""Configuração centralizada de logging da aplicação.

Toda ação relevante realizada pelo usuário (cadastro, edição, exclusão) e
toda tentativa inválida (campo obrigatório vazio, tipo incorreto, registro
não encontrado) é registrada em arquivo. Esses registros funcionam como
evidência verificável do que foi feito no sistema e quando.
"""

import logging
from pathlib import Path

CAMINHO_DA_PASTA_DE_LOGS = Path(__file__).resolve().parent.parent / "logs"
CAMINHO_DO_ARQUIVO_DE_LOG = CAMINHO_DA_PASTA_DE_LOGS / "auditoria.log"

FORMATO_DO_LOG = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configurar_logging() -> None:
    """Prepara os manipuladores de logging: tudo vai para o arquivo de
    auditoria; avisos e erros também aparecem no console.

    É seguro chamar esta função mais de uma vez: se o logging já tiver sido
    configurado, a chamada não faz nada (evita duplicar handlers e, com
    isso, duplicar cada linha registrada).
    """
    logger_raiz = logging.getLogger()
    if logger_raiz.handlers:
        return

    CAMINHO_DA_PASTA_DE_LOGS.mkdir(parents=True, exist_ok=True)

    manipulador_de_arquivo = logging.FileHandler(
        CAMINHO_DO_ARQUIVO_DE_LOG, encoding="utf-8"
    )
    manipulador_de_arquivo.setLevel(logging.INFO)

    manipulador_de_console = logging.StreamHandler()
    manipulador_de_console.setLevel(logging.WARNING)

    logging.basicConfig(
        level=logging.INFO,
        format=FORMATO_DO_LOG,
        handlers=[manipulador_de_arquivo, manipulador_de_console],
    )

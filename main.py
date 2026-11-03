"""Ponto de entrada da aplicação de Inventário de Ativos de TI.

Este arquivo monta as dependências (banco de dados, repositórios e
serviços) e inicia o menu no terminal. Toda a lógica da aplicação fica
organizada dentro do pacote 'app'.
"""

import logging

from app.cli.interface_texto import InterfaceDeTexto
from app.logging_config import configurar_logging
from app.repositories.database import ConexaoBancoDeDados
from app.servicos import criar_servicos

logger = logging.getLogger(__name__)


def iniciar_aplicacao() -> None:
    """Configura o logging, monta as dependências e inicia o menu no terminal."""
    configurar_logging()
    logger.info("Aplicação iniciada.")

    banco_de_dados = ConexaoBancoDeDados()
    servicos = criar_servicos(banco_de_dados)

    InterfaceDeTexto(
        servicos.equipamentos,
        servicos.vulnerabilidades,
        servicos.dependencias,
        servicos.analise_de_risco,
    ).executar()

    banco_de_dados.fechar()
    logger.info("Aplicação encerrada.")


if __name__ == "__main__":
    iniciar_aplicacao()

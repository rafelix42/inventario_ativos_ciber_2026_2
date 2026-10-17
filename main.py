"""Ponto de entrada da aplicação de Inventário de Ativos de TI.

Este arquivo monta as dependências (banco de dados, repositórios e
serviços) e inicia o menu no terminal. Toda a lógica da aplicação fica
organizada dentro do pacote 'app'.
"""

import logging

from app.cli.interface_texto import InterfaceDeTexto
from app.logging_config import configurar_logging
from app.repositories.equipamento_repository import EquipamentoRepository
from app.repositories.database import ConexaoBancoDeDados
from app.repositories.vulnerabilidade_repository import VulnerabilidadeRepository
from app.services.equipamento_service import EquipamentoService
from app.services.vulnerabilidade_service import VulnerabilidadeService

logger = logging.getLogger(__name__)


def iniciar_aplicacao() -> None:
    """Configura o logging, monta as dependências e inicia o menu no terminal."""
    configurar_logging()
    logger.info("Aplicação iniciada.")

    banco_de_dados = ConexaoBancoDeDados()
    servico_de_equipamentos = EquipamentoService(EquipamentoRepository(banco_de_dados))
    servico_de_vulnerabilidades = VulnerabilidadeService(
        VulnerabilidadeRepository(banco_de_dados)
    )

    InterfaceDeTexto(servico_de_equipamentos, servico_de_vulnerabilidades).executar()

    banco_de_dados.fechar()
    logger.info("Aplicação encerrada.")


if __name__ == "__main__":
    iniciar_aplicacao()

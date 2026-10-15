"""Ponto de entrada da aplicação de Inventário de Ativos de TI.

Este arquivo pergunta ao usuário se ele quer usar a interface gráfica ou o
terminal, monta as dependências (banco de dados, repositórios e serviços)
e inicia a interface escolhida. Toda a lógica da aplicação fica organizada
dentro do pacote 'app' — este arquivo só decide qual interface usar.
"""

import logging

from app.logging_config import configurar_logging
from app.repositories.ativo_repository import AtivoRepository
from app.repositories.database import ConexaoBancoDeDados
from app.repositories.vulnerabilidade_repository import VulnerabilidadeRepository
from app.services.ativo_service import AtivoService
from app.services.vulnerabilidade_service import VulnerabilidadeService

logger = logging.getLogger(__name__)


def escolher_modo_de_execucao() -> str:
    """Pergunta ao usuário se ele quer usar a interface gráfica ou o terminal.

    Repete a pergunta até receber uma resposta válida. Retorna 'grafica' ou
    'terminal'.
    """
    print("=== Inventário de Ativos de TI ===")
    print("1 - Terminal")
    print("2 - Interface gráfica")
    print("0 - Sair")

    while True:
        try:
            escolha = input("Como deseja executar a aplicação?: ").strip()
        except (EOFError, KeyboardInterrupt) as interrupcao:
            print("\nEntrada interrompida. Encerrando a aplicação.")
            raise SystemExit(0) from interrupcao

        if escolha == "1":
            return "terminal"
        if escolha == "2":
            return "grafica"
        if escolha == "0":
            print("\nEncerrando a aplicação.")
            raise SystemExit(0)
        print("Opção inválida. Digite 1 para interface gráfica ou 2 para terminal.")


def iniciar_aplicacao() -> None:
    """Configura o logging, monta as dependências e inicia a interface escolhida."""
    configurar_logging()
    logger.info("Aplicação iniciada.")

    modo_de_execucao = escolher_modo_de_execucao()
    logger.info("Modo de execução selecionado: %s", modo_de_execucao)

    banco_de_dados = ConexaoBancoDeDados()
    servico_de_ativos = AtivoService(AtivoRepository(banco_de_dados))
    servico_de_vulnerabilidades = VulnerabilidadeService(
        VulnerabilidadeRepository(banco_de_dados)
    )

    if modo_de_execucao == "grafica":
        # Importado somente aqui para que o modo terminal funcione mesmo em
        # ambientes sem tkinter instalado (por exemplo, um servidor sem
        # interface gráfica).
        # pylint: disable-next=import-outside-toplevel
        from app.ui.main_window import JanelaPrincipal

        janela_principal = JanelaPrincipal(
            servico_de_ativos, servico_de_vulnerabilidades
        )
        janela_principal.mainloop()
    else:
        # pylint: disable-next=import-outside-toplevel
        from app.cli.interface_texto import InterfaceDeTexto

        InterfaceDeTexto(servico_de_ativos, servico_de_vulnerabilidades).executar()

    banco_de_dados.fechar()
    logger.info("Aplicação encerrada.")


if __name__ == "__main__":
    iniciar_aplicacao()

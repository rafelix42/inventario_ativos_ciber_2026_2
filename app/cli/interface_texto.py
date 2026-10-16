"""Interface de texto: expõe todo o CRUD de ativos e vulnerabilidades por
um menu no terminal, para quando não há (ou não se quer usar) a interface
gráfica (RNF08).

Esta classe não conhece SQL nem regras de negócio: ela só lê dados do
teclado, chama os mesmos serviços usados pela interface gráfica
(AtivoService e VulnerabilidadeService) e imprime o resultado.
"""

from typing import Optional

from app.exceptions import (
    AtivoNaoEncontradoError,
    ErroDeValidacao,
    VulnerabilidadeNaoEncontradaError,
)
from app.models.ativo import Ativo
from app.models.enums import StatusVulnerabilidade, TipoAtivo, rotulo_amigavel
from app.models.vulnerabilidade import Vulnerabilidade
from app.services.ativo_service import AtivoService
from app.services.vulnerabilidade_service import VulnerabilidadeService


class InterfaceDeTexto:
    """Menu textual com todas as operações de CRUD de ativos e vulnerabilidades."""

    def __init__(
        self,
        servico_de_ativos: AtivoService,
        servico_de_vulnerabilidades: VulnerabilidadeService,
    ):
        self._servico_de_ativos = servico_de_ativos
        self._servico_de_vulnerabilidades = servico_de_vulnerabilidades

    def executar(self) -> None:
        """Laço principal do menu: roda até o usuário escolher sair."""
        while True:
            try:
                self._exibir_menu_principal()
                opcao = input("Escolha uma opção: ").strip()

                if opcao == "1":
                    self._cadastrar_ativo()
                elif opcao == "2":
                    self._buscar_ativo()
                elif opcao == "3":
                    self._listar_ativos()
                elif opcao == "4":
                    self._atualizar_ativo()
                elif opcao == "5":
                    self._excluir_ativo()
                elif opcao == "6":
                    self._gerenciar_vulnerabilidades()
                elif opcao == "0":
                    print("Encerrando a aplicação.")
                    return
                else:
                    print("Opção inválida. Tente novamente.\n")
            except (EOFError, KeyboardInterrupt):
                print("\nEntrada interrompida. Encerrando a aplicação.")
                return

    @staticmethod
    def _exibir_menu_principal() -> None:
        print("\n=== INVENTÁRIO DE ATIVOS DE TI ===")
        print("1 - Cadastrar ativo")
        print("2 - Buscar ativo (por ID ou nome)")
        print("3 - Listar todos os ativos")
        print("4 - Atualizar ativo")
        print("5 - Excluir ativo")
        print("6 - Gerenciar vulnerabilidades de um ativo")
        print("0 - Sair")

    # --- Ativos: Create -----------------------------------------------

    def _cadastrar_ativo(self) -> None:
        print("\n--- Novo ativo ---")
        nome = input("Nome/hostname: ")
        responsavel = input("Responsável: ")
        setor = input("Setor/localização: ")
        tipo = self._escolher_tipo_de_ativo()
        if tipo is None:
            return
        descricao = input("Descrição (opcional): ")

        try:
            ativo = self._servico_de_ativos.cadastrar(
                nome, responsavel, setor, tipo, descricao
            )
        except ErroDeValidacao as erro:
            print(f"Erro: {erro}")
            return

        print(f"Ativo '{ativo.nome}' cadastrado com sucesso (ID {ativo.id}).")

        deseja_cadastrar_vulnerabilidades = (
            input(
                "Deseja cadastrar vulnerabilidades iniciais para este ativo agora? "
                "(s/n): "
            )
            .strip()
            .lower()
        )
        if deseja_cadastrar_vulnerabilidades == "s":
            self._menu_de_vulnerabilidades(ativo)

    # --- Ativos: Read ---------------------------------------------------

    def _buscar_ativo(self) -> None:
        print("\n--- Buscar ativo ---")
        texto_buscado = input("Digite o ID ou parte do nome/hostname: ").strip()

        if texto_buscado.isdigit():
            try:
                ativo = self._servico_de_ativos.buscar_por_id(int(texto_buscado))
                self._exibir_ativo(ativo)
            except AtivoNaoEncontradoError as erro:
                print(f"Erro: {erro}")
            return

        ativos_encontrados = self._servico_de_ativos.buscar_por_nome(texto_buscado)
        if not ativos_encontrados:
            print("Nenhum ativo encontrado.")
            return
        for ativo in ativos_encontrados:
            self._exibir_ativo(ativo)

    def _listar_ativos(self) -> None:
        print("\n--- Ativos cadastrados ---")
        ativos = self._servico_de_ativos.listar_todos()
        if not ativos:
            print("Nenhum ativo cadastrado.")
            return
        for ativo in ativos:
            self._exibir_ativo(ativo)

    def _exibir_ativo(self, ativo: Ativo) -> None:
        quantidade_de_vulnerabilidades = len(
            self._servico_de_vulnerabilidades.listar_por_ativo(ativo.id)
        )
        print(
            f"[{ativo.id}] {ativo.nome} | Responsável: {ativo.responsavel} | "
            f"Setor: {ativo.setor} | Tipo: {rotulo_amigavel(ativo.tipo.name)} | "
            f"Vulnerabilidades: {quantidade_de_vulnerabilidades}"
        )
        if ativo.descricao:
            print(f"    Descrição: {ativo.descricao}")

    # --- Ativos: Update ---------------------------------------------------

    def _atualizar_ativo(self) -> None:
        print("\n--- Atualizar ativo ---")
        ativo = self._selecionar_ativo_por_id()
        if ativo is None:
            return

        print("Deixe em branco para manter o valor atual.")
        responsavel = (
            input(f"Responsável [{ativo.responsavel}]: ").strip() or ativo.responsavel
        )
        setor = input(f"Setor/localização [{ativo.setor}]: ").strip() or ativo.setor
        descricao = input(f"Descrição [{ativo.descricao}]: ").strip() or ativo.descricao

        tipo = ativo.tipo
        print(f"Tipo atual: {rotulo_amigavel(ativo.tipo.name)}")
        if input("Deseja alterar o tipo de ativo? (s/n): ").strip().lower() == "s":
            tipo_escolhido = self._escolher_tipo_de_ativo()
            if tipo_escolhido is None:
                return
            tipo = tipo_escolhido

        try:
            ativo_atualizado = self._servico_de_ativos.atualizar(
                ativo.id, responsavel, setor, tipo, descricao
            )
        except ErroDeValidacao as erro:
            print(f"Erro: {erro}")
            return

        print("Ativo atualizado com sucesso.")
        self._exibir_ativo(ativo_atualizado)

    # --- Ativos: Delete ---------------------------------------------------

    def _excluir_ativo(self) -> None:
        print("\n--- Excluir ativo ---")
        ativo = self._selecionar_ativo_por_id()
        if ativo is None:
            return

        confirmacao = (
            input(
                f"Tem certeza que deseja excluir o ativo '{ativo.nome}' "
                "e todas as suas "
                "vulnerabilidades? (s/n): "
            )
            .strip()
            .lower()
        )
        if confirmacao != "s":
            print("Operação cancelada.")
            return

        self._servico_de_ativos.excluir(ativo.id)
        self._servico_de_vulnerabilidades.esquecer_vulnerabilidades_do_ativo(ativo.id)
        print("Ativo excluído com sucesso.")

    # --- Vulnerabilidades ------------------------------------------------

    def _gerenciar_vulnerabilidades(self) -> None:
        print("\n--- Gerenciar vulnerabilidades de um ativo ---")
        ativo = self._selecionar_ativo_por_id()
        if ativo is None:
            return
        self._menu_de_vulnerabilidades(ativo)

    def _menu_de_vulnerabilidades(self, ativo: Ativo) -> None:
        while True:
            print(f"\n=== VULNERABILIDADES DE: {ativo.nome} (ID {ativo.id}) ===")
            print("1 - Listar vulnerabilidades")
            print("2 - Cadastrar vulnerabilidade")
            print("3 - Atualizar vulnerabilidade")
            print("4 - Excluir vulnerabilidade")
            print("0 - Voltar")
            opcao = input("Escolha uma opção: ").strip()

            if opcao == "1":
                self._listar_vulnerabilidades(ativo)
            elif opcao == "2":
                self._cadastrar_vulnerabilidade(ativo)
            elif opcao == "3":
                self._atualizar_vulnerabilidade(ativo)
            elif opcao == "4":
                self._excluir_vulnerabilidade(ativo)
            elif opcao == "0":
                return
            else:
                print("Opção inválida. Tente novamente.\n")

    def _listar_vulnerabilidades(self, ativo: Ativo) -> None:
        vulnerabilidades = self._servico_de_vulnerabilidades.listar_por_ativo(ativo.id)
        if not vulnerabilidades:
            print("Este ativo não possui nenhuma vulnerabilidade registrada.")
            return
        for vulnerabilidade in vulnerabilidades:
            print(
                f"[{vulnerabilidade.id}] {vulnerabilidade.descricao} | "
                f"Categoria: {vulnerabilidade.categoria} | "
                f"Nota CVSS: {vulnerabilidade.nota_cvss:.1f} | "
                f"Severidade: {rotulo_amigavel(vulnerabilidade.severidade.name)} | "
                f"Status: {rotulo_amigavel(vulnerabilidade.status.name)}"
            )

    def _cadastrar_vulnerabilidade(self, ativo: Ativo) -> None:
        print("\n--- Nova vulnerabilidade ---")
        descricao = input("Descrição: ")
        categoria = input("Categoria: ")
        nota_cvss = self._ler_nota_cvss()
        if nota_cvss is None:
            return
        status = self._escolher_status()
        if status is None:
            return

        try:
            vulnerabilidade = self._servico_de_vulnerabilidades.cadastrar(
                ativo.id, descricao, categoria, nota_cvss, status
            )
        except ErroDeValidacao as erro:
            print(f"Erro: {erro}")
            return

        print(
            f"Vulnerabilidade cadastrada com sucesso (ID {vulnerabilidade.id}, "
            f"severidade {rotulo_amigavel(vulnerabilidade.severidade.name)})."
        )

    def _atualizar_vulnerabilidade(self, ativo: Ativo) -> None:
        vulnerabilidade = self._selecionar_vulnerabilidade_por_id(ativo)
        if vulnerabilidade is None:
            return

        print("Deixe em branco para manter o valor atual.")
        descricao = (
            input(f"Descrição [{vulnerabilidade.descricao}]: ").strip()
            or vulnerabilidade.descricao
        )
        categoria = (
            input(f"Categoria [{vulnerabilidade.categoria}]: ").strip()
            or vulnerabilidade.categoria
        )

        nota_cvss = vulnerabilidade.nota_cvss
        texto_nota = input(f"Nota CVSS [{vulnerabilidade.nota_cvss:.1f}]: ").strip()
        if texto_nota:
            nota_convertida = self._converter_nota_cvss(texto_nota)
            if nota_convertida is None:
                return
            nota_cvss = nota_convertida

        status = vulnerabilidade.status
        print(f"Status atual: {rotulo_amigavel(vulnerabilidade.status.name)}")
        if input("Deseja alterar o status? (s/n): ").strip().lower() == "s":
            status_escolhido = self._escolher_status()
            if status_escolhido is None:
                return
            status = status_escolhido

        try:
            vulnerabilidade_atualizada = self._servico_de_vulnerabilidades.atualizar(
                vulnerabilidade.id, descricao, categoria, nota_cvss, status
            )
        except ErroDeValidacao as erro:
            print(f"Erro: {erro}")
            return

        print(
            "Vulnerabilidade atualizada com sucesso. Nova severidade: "
            f"{rotulo_amigavel(vulnerabilidade_atualizada.severidade.name)}."
        )

    def _excluir_vulnerabilidade(self, ativo: Ativo) -> None:
        vulnerabilidade = self._selecionar_vulnerabilidade_por_id(ativo)
        if vulnerabilidade is None:
            return

        confirmacao = (
            input("Tem certeza que deseja excluir esta vulnerabilidade? (s/n): ")
            .strip()
            .lower()
        )
        if confirmacao != "s":
            print("Operação cancelada.")
            return

        try:
            self._servico_de_vulnerabilidades.excluir(vulnerabilidade.id)
        except VulnerabilidadeNaoEncontradaError as erro:
            print(f"Erro: {erro}")
            return

        print("Vulnerabilidade excluída com sucesso.")

    # --- Utilitários de entrada -----------------------------------------

    def _selecionar_ativo_por_id(self) -> Optional[Ativo]:
        texto_id = input("Digite o ID do ativo: ").strip()
        if not texto_id.isdigit():
            print("Erro: informe um número de ID válido.")
            return None

        try:
            return self._servico_de_ativos.buscar_por_id(int(texto_id))
        except AtivoNaoEncontradoError as erro:
            print(f"Erro: {erro}")
            return None

    def _selecionar_vulnerabilidade_por_id(
        self, ativo: Ativo
    ) -> Optional[Vulnerabilidade]:
        vulnerabilidades = self._servico_de_vulnerabilidades.listar_por_ativo(ativo.id)
        if not vulnerabilidades:
            print("Este ativo não possui nenhuma vulnerabilidade registrada.")
            return None

        self._listar_vulnerabilidades(ativo)
        texto_id = input("Digite o ID da vulnerabilidade: ").strip()
        if not texto_id.isdigit():
            print("Erro: informe um número de ID válido.")
            return None

        vulnerabilidade_id = int(texto_id)
        vulnerabilidade = next(
            (v for v in vulnerabilidades if v.id == vulnerabilidade_id), None
        )
        if vulnerabilidade is None:
            print(
                f"Erro: nenhuma vulnerabilidade com ID {vulnerabilidade_id} "
                "para este ativo."
            )
        return vulnerabilidade

    @staticmethod
    def _escolher_tipo_de_ativo() -> Optional[TipoAtivo]:
        tipos_disponiveis = list(TipoAtivo)
        print("Tipos de ativo disponíveis:")
        for indice, tipo in enumerate(tipos_disponiveis, start=1):
            print(f"  {indice} - {rotulo_amigavel(tipo.name)}")

        escolha = input("Escolha o tipo (número): ").strip()
        if not escolha.isdigit() or not 1 <= int(escolha) <= len(tipos_disponiveis):
            print("Erro: opção de tipo inválida.")
            return None
        return tipos_disponiveis[int(escolha) - 1]

    @staticmethod
    def _escolher_status() -> Optional[StatusVulnerabilidade]:
        status_disponiveis = list(StatusVulnerabilidade)
        print("Status disponíveis:")
        for indice, status in enumerate(status_disponiveis, start=1):
            print(f"  {indice} - {rotulo_amigavel(status.name)}")

        escolha = input("Escolha o status (número): ").strip()
        if not escolha.isdigit() or not 1 <= int(escolha) <= len(status_disponiveis):
            print("Erro: opção de status inválida.")
            return None
        return status_disponiveis[int(escolha) - 1]

    def _ler_nota_cvss(self) -> Optional[float]:
        texto_nota = input("Nota CVSS (0.0 a 10.0): ").strip()
        return self._converter_nota_cvss(texto_nota)

    @staticmethod
    def _converter_nota_cvss(texto_nota: str) -> Optional[float]:
        try:
            return float(texto_nota.replace(",", "."))
        except ValueError:
            print("Erro: informe a nota CVSS como um número (ex.: 7.5).")
            return None

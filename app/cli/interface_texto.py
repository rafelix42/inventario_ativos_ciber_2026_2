"""Interface de texto: expõe todo o CRUD de equipamentos e vulnerabilidades por
um menu no terminal (RNF08).

Esta classe não conhece SQL nem regras de negócio: ela só lê dados do
teclado, chama os serviços da aplicação (EquipamentoService e
VulnerabilidadeService) e imprime o resultado.
"""

from typing import Optional, Type

from app.exceptions import (
    EquipamentoNaoEncontradoError,
    ErroDeValidacao,
    VulnerabilidadeNaoEncontradaError,
)
from app.models.enums import StatusVulnerabilidade, rotulo_amigavel
from app.models.equipamento import TIPOS_DE_EQUIPAMENTO, Equipamento
from app.models.vulnerabilidade import Vulnerabilidade
from app.services.equipamento_service import EquipamentoService
from app.services.vulnerabilidade_service import VulnerabilidadeService


class InterfaceDeTexto:
    """Menu textual com o CRUD completo de equipamentos e vulnerabilidades."""

    def __init__(
        self,
        servico_de_equipamentos: EquipamentoService,
        servico_de_vulnerabilidades: VulnerabilidadeService,
    ):
        self._servico_de_equipamentos = servico_de_equipamentos
        self._servico_de_vulnerabilidades = servico_de_vulnerabilidades

    def executar(self) -> None:
        """Laço principal do menu: roda até o usuário escolher sair."""
        while True:
            try:
                self._exibir_menu_principal()
                opcao = input("Escolha uma opção: ").strip()

                if opcao == "1":
                    self._cadastrar_equipamento()
                elif opcao == "2":
                    self._buscar_equipamento()
                elif opcao == "3":
                    self._listar_equipamentos()
                elif opcao == "4":
                    self._atualizar_equipamento()
                elif opcao == "5":
                    self._excluir_equipamento()
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
        print("1 - Cadastrar equipamento")
        print("2 - Buscar equipamento (por ID ou nome)")
        print("3 - Listar todos os equipamentos")
        print("4 - Atualizar equipamento")
        print("5 - Excluir equipamento")
        print("6 - Gerenciar vulnerabilidades de um equipamento")
        print("0 - Sair")

    # --- Equipamentos: Create -----------------------------------------------

    def _cadastrar_equipamento(self) -> None:
        print("\n--- Novo equipamento ---")
        nome = input("Nome/hostname: ")
        responsavel = input("Responsável: ")
        setor = input("Setor/localização: ")
        classe = self._escolher_classe_de_equipamento()
        if classe is None:
            return
        descricao = input("Descrição (opcional): ")

        try:
            equipamento = self._servico_de_equipamentos.cadastrar(
                nome, responsavel, setor, classe, descricao
            )
        except ErroDeValidacao as erro:
            print(f"Erro: {erro}")
            return

        print(
            f"Equipamento '{equipamento.nome}' cadastrado com sucesso "
            f"(ID {equipamento.id})."
        )

        deseja_cadastrar_vulnerabilidades = (
            input(
                "Deseja cadastrar vulnerabilidades iniciais para este "
                "equipamento agora? (s/n): "
            )
            .strip()
            .lower()
        )
        if deseja_cadastrar_vulnerabilidades == "s":
            self._menu_de_vulnerabilidades(equipamento)

    # --- Equipamentos: Read ---------------------------------------------------

    def _buscar_equipamento(self) -> None:
        print("\n--- Buscar equipamento ---")
        texto_buscado = input("Digite o ID ou parte do nome/hostname: ").strip()

        if texto_buscado.isdigit():
            try:
                equipamento = self._servico_de_equipamentos.buscar_por_id(
                    int(texto_buscado)
                )
                self._exibir_equipamento(equipamento)
            except EquipamentoNaoEncontradoError as erro:
                print(f"Erro: {erro}")
            return

        equipamentos_encontrados = self._servico_de_equipamentos.buscar_por_nome(
            texto_buscado
        )
        if not equipamentos_encontrados:
            print("Nenhum equipamento encontrado.")
            return
        for equipamento in equipamentos_encontrados:
            self._exibir_equipamento(equipamento)

    def _listar_equipamentos(self) -> None:
        print("\n--- Equipamentos cadastrados ---")
        equipamentos = self._servico_de_equipamentos.listar_todos()
        if not equipamentos:
            print("Nenhum equipamento cadastrado.")
            return
        for equipamento in equipamentos:
            self._exibir_equipamento(equipamento)

    def _exibir_equipamento(self, equipamento: Equipamento) -> None:
        quantidade_de_vulnerabilidades = len(
            self._servico_de_vulnerabilidades.listar_por_equipamento(equipamento.id)
        )
        print(
            f"[{equipamento.id}] {equipamento.nome} | "
            f"Responsável: {equipamento.responsavel} | "
            f"Setor: {equipamento.setor} | Tipo: {equipamento.ROTULO} | "
            f"Vulnerabilidades: {quantidade_de_vulnerabilidades}"
        )
        if equipamento.descricao:
            print(f"    Descrição: {equipamento.descricao}")

    # --- Equipamentos: Update ---------------------------------------------------

    def _atualizar_equipamento(self) -> None:
        print("\n--- Atualizar equipamento ---")
        equipamento = self._selecionar_equipamento_por_id()
        if equipamento is None:
            return

        print("Deixe em branco para manter o valor atual.")
        responsavel = (
            input(f"Responsável [{equipamento.responsavel}]: ").strip()
            or equipamento.responsavel
        )
        setor = (
            input(f"Setor/localização [{equipamento.setor}]: ").strip()
            or equipamento.setor
        )
        descricao = (
            input(f"Descrição [{equipamento.descricao}]: ").strip()
            or equipamento.descricao
        )

        classe = type(equipamento)
        print(f"Tipo atual: {equipamento.ROTULO}")
        if (
            input("Deseja alterar o tipo de equipamento? (s/n): ").strip().lower()
            == "s"
        ):
            classe_escolhida = self._escolher_classe_de_equipamento()
            if classe_escolhida is None:
                return
            classe = classe_escolhida

        try:
            equipamento_atualizado = self._servico_de_equipamentos.atualizar(
                equipamento.id, responsavel, setor, classe, descricao
            )
        except ErroDeValidacao as erro:
            print(f"Erro: {erro}")
            return

        print("Equipamento atualizado com sucesso.")
        self._exibir_equipamento(equipamento_atualizado)

    # --- Equipamentos: Delete ---------------------------------------------------

    def _excluir_equipamento(self) -> None:
        print("\n--- Excluir equipamento ---")
        equipamento = self._selecionar_equipamento_por_id()
        if equipamento is None:
            return

        confirmacao = (
            input(
                f"Tem certeza que deseja excluir o equipamento '{equipamento.nome}' "
                "e todas as suas "
                "vulnerabilidades? (s/n): "
            )
            .strip()
            .lower()
        )
        if confirmacao != "s":
            print("Operação cancelada.")
            return

        self._servico_de_equipamentos.excluir(equipamento.id)
        self._servico_de_vulnerabilidades.esquecer_vulnerabilidades_do_equipamento(
            equipamento.id
        )
        print("Equipamento excluído com sucesso.")

    # --- Vulnerabilidades ------------------------------------------------

    def _gerenciar_vulnerabilidades(self) -> None:
        print("\n--- Gerenciar vulnerabilidades de um equipamento ---")
        equipamento = self._selecionar_equipamento_por_id()
        if equipamento is None:
            return
        self._menu_de_vulnerabilidades(equipamento)

    def _menu_de_vulnerabilidades(self, equipamento: Equipamento) -> None:
        while True:
            print(
                f"\n=== VULNERABILIDADES DE: {equipamento.nome} "
                f"(ID {equipamento.id}) ==="
            )
            print("1 - Listar vulnerabilidades")
            print("2 - Cadastrar vulnerabilidade")
            print("3 - Atualizar vulnerabilidade")
            print("4 - Excluir vulnerabilidade")
            print("0 - Voltar")
            opcao = input("Escolha uma opção: ").strip()

            if opcao == "1":
                self._listar_vulnerabilidades(equipamento)
            elif opcao == "2":
                self._cadastrar_vulnerabilidade(equipamento)
            elif opcao == "3":
                self._atualizar_vulnerabilidade(equipamento)
            elif opcao == "4":
                self._excluir_vulnerabilidade(equipamento)
            elif opcao == "0":
                return
            else:
                print("Opção inválida. Tente novamente.\n")

    def _listar_vulnerabilidades(self, equipamento: Equipamento) -> None:
        vulnerabilidades = self._servico_de_vulnerabilidades.listar_por_equipamento(
            equipamento.id
        )
        if not vulnerabilidades:
            print("Este equipamento não possui nenhuma vulnerabilidade registrada.")
            return
        for vulnerabilidade in vulnerabilidades:
            print(
                f"[{vulnerabilidade.id}] {vulnerabilidade.descricao} | "
                f"Categoria: {vulnerabilidade.categoria} | "
                f"Nota CVSS: {vulnerabilidade.nota_cvss:.1f} | "
                f"Severidade: {rotulo_amigavel(vulnerabilidade.severidade.name)} | "
                f"Status: {rotulo_amigavel(vulnerabilidade.status.name)}"
            )

    def _cadastrar_vulnerabilidade(self, equipamento: Equipamento) -> None:
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
                equipamento.id, descricao, categoria, nota_cvss, status
            )
        except ErroDeValidacao as erro:
            print(f"Erro: {erro}")
            return

        print(
            f"Vulnerabilidade cadastrada com sucesso (ID {vulnerabilidade.id}, "
            f"severidade {rotulo_amigavel(vulnerabilidade.severidade.name)})."
        )

    def _atualizar_vulnerabilidade(self, equipamento: Equipamento) -> None:
        vulnerabilidade = self._selecionar_vulnerabilidade_por_id(equipamento)
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

    def _excluir_vulnerabilidade(self, equipamento: Equipamento) -> None:
        vulnerabilidade = self._selecionar_vulnerabilidade_por_id(equipamento)
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

    def _selecionar_equipamento_por_id(self) -> Optional[Equipamento]:
        texto_id = input("Digite o ID do equipamento: ").strip()
        if not texto_id.isdigit():
            print("Erro: informe um número de ID válido.")
            return None

        try:
            return self._servico_de_equipamentos.buscar_por_id(int(texto_id))
        except EquipamentoNaoEncontradoError as erro:
            print(f"Erro: {erro}")
            return None

    def _selecionar_vulnerabilidade_por_id(
        self, equipamento: Equipamento
    ) -> Optional[Vulnerabilidade]:
        vulnerabilidades = self._servico_de_vulnerabilidades.listar_por_equipamento(
            equipamento.id
        )
        if not vulnerabilidades:
            print("Este equipamento não possui nenhuma vulnerabilidade registrada.")
            return None

        self._listar_vulnerabilidades(equipamento)
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
                "para este equipamento."
            )
        return vulnerabilidade

    @staticmethod
    def _escolher_classe_de_equipamento() -> Optional[Type[Equipamento]]:
        classes_disponiveis = list(TIPOS_DE_EQUIPAMENTO.values())
        print("Tipos de equipamento disponíveis:")
        for indice, classe in enumerate(classes_disponiveis, start=1):
            print(f"  {indice} - {classe.ROTULO}")

        escolha = input("Escolha o tipo (número): ").strip()
        if not escolha.isdigit() or not 1 <= int(escolha) <= len(classes_disponiveis):
            print("Erro: opção de tipo inválida.")
            return None
        return classes_disponiveis[int(escolha) - 1]

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

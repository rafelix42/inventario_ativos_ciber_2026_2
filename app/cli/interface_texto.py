"""Interface de texto: expõe todo o CRUD de equipamentos e vulnerabilidades,
além da análise de risco, por um menu no terminal (RNF08).

Esta classe não conhece SQL nem regras de negócio: ela só lê dados do
teclado, chama os serviços da aplicação (EquipamentoService,
VulnerabilidadeService, DependenciaService e AnaliseDeRiscoService) e
imprime o resultado.
"""

from typing import List, Optional, Sequence, Type, TypeVar, Union

import numpy as np

from app.exceptions import (
    EquipamentoNaoEncontradoError,
    ErroDeValidacao,
    SistemaNaoInvertivelError,
    VulnerabilidadeNaoEncontradaError,
)
from app.models.enums import StatusVulnerabilidade, rotulo_amigavel
from app.models.equipamento import TIPOS_DE_EQUIPAMENTO, Equipamento
from app.models.vulnerabilidade import Vulnerabilidade
from app.services.analise_de_risco_service import AnaliseDeRiscoService
from app.services.dependencia_service import DependenciaService
from app.services.equipamento_service import EquipamentoService
from app.services.vulnerabilidade_service import VulnerabilidadeService

# Itens que podem ser escolhidos pelo ID em uma lista exibida ao usuário.
T = TypeVar("T", bound=Union[Equipamento, Vulnerabilidade])


class InterfaceDeTexto:
    """Menu textual com o CRUD completo de equipamentos e vulnerabilidades e
    com a análise de risco."""

    def __init__(
        self,
        servico_de_equipamentos: EquipamentoService,
        servico_de_vulnerabilidades: VulnerabilidadeService,
        servico_de_dependencias: DependenciaService,
        servico_de_analise_de_risco: AnaliseDeRiscoService,
    ):
        self._servico_de_equipamentos = servico_de_equipamentos
        self._servico_de_vulnerabilidades = servico_de_vulnerabilidades
        self._servico_de_dependencias = servico_de_dependencias
        self._servico_de_analise_de_risco = servico_de_analise_de_risco

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
                    self._gerenciar_vulnerabilidades_de_um_equipamento()
                elif opcao == "7":
                    self._menu_do_catalogo_de_vulnerabilidades()
                elif opcao == "8":
                    self._menu_de_analise_de_risco()
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
        print("7 - Catálogo de vulnerabilidades")
        print("8 - Análise de risco")
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
            input("Deseja atribuir vulnerabilidades a este equipamento agora? (s/n): ")
            .strip()
            .lower()
        )
        if deseja_cadastrar_vulnerabilidades == "s":
            self._menu_de_vulnerabilidades_do_equipamento(equipamento)

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

        exclusivas = self._servico_de_vulnerabilidades.listar_exclusivas_do_equipamento(
            equipamento.id
        )
        if exclusivas:
            print(
                f"Atenção: {len(exclusivas)} vulnerabilidade(s) afetam apenas este "
                "equipamento e também serão excluídas:"
            )
            for vulnerabilidade in exclusivas:
                self._exibir_vulnerabilidade(vulnerabilidade)

        confirmacao = (
            input(
                f"Tem certeza que deseja excluir o equipamento '{equipamento.nome}'? "
                "(s/n): "
            )
            .strip()
            .lower()
        )
        if confirmacao != "s":
            print("Operação cancelada.")
            return

        self._servico_de_equipamentos.excluir(equipamento.id)
        excluidas = (
            self._servico_de_vulnerabilidades.sincronizar_apos_exclusao_de_equipamento(
                equipamento.id
            )
        )
        print("Equipamento excluído com sucesso.")
        if excluidas:
            print(
                f"{len(excluidas)} vulnerabilidade(s) exclusiva(s) também excluída(s)."
            )

    # --- Vulnerabilidades de um equipamento ------------------------------

    def _gerenciar_vulnerabilidades_de_um_equipamento(self) -> None:
        print("\n--- Gerenciar vulnerabilidades de um equipamento ---")
        equipamento = self._selecionar_equipamento_por_id()
        if equipamento is None:
            return
        self._menu_de_vulnerabilidades_do_equipamento(equipamento)

    def _menu_de_vulnerabilidades_do_equipamento(
        self, equipamento: Equipamento
    ) -> None:
        while True:
            print(
                f"\n=== VULNERABILIDADES DE: {equipamento.nome} "
                f"(ID {equipamento.id}) ==="
            )
            print("1 - Listar vulnerabilidades do equipamento")
            print("2 - Atribuir vulnerabilidade (existente ou nova)")
            print("3 - Remover vulnerabilidade do equipamento")
            print("0 - Voltar")
            opcao = input("Escolha uma opção: ").strip()

            if opcao == "1":
                self._listar_vulnerabilidades_do_equipamento(equipamento)
            elif opcao == "2":
                self._atribuir_vulnerabilidade_ao_equipamento(equipamento)
            elif opcao == "3":
                self._remover_vulnerabilidade_do_equipamento(equipamento)
            elif opcao == "0":
                return
            else:
                print("Opção inválida. Tente novamente.\n")

    def _listar_vulnerabilidades_do_equipamento(self, equipamento: Equipamento) -> None:
        vulnerabilidades = self._servico_de_vulnerabilidades.listar_por_equipamento(
            equipamento.id
        )
        if not vulnerabilidades:
            print("Este equipamento não possui nenhuma vulnerabilidade registrada.")
            return
        for vulnerabilidade in vulnerabilidades:
            self._exibir_vulnerabilidade(vulnerabilidade)

    def _atribuir_vulnerabilidade_ao_equipamento(
        self, equipamento: Equipamento
    ) -> None:
        servico = self._servico_de_vulnerabilidades
        ids_ja_atribuidos = {
            vulnerabilidade.id
            for vulnerabilidade in servico.listar_por_equipamento(equipamento.id)
        }
        disponiveis = [
            vulnerabilidade
            for vulnerabilidade in servico.listar_todas()
            if vulnerabilidade.id not in ids_ja_atribuidos
        ]

        if disponiveis:
            print(
                "\nVulnerabilidades cadastradas que ainda não afetam este equipamento:"
            )
            for vulnerabilidade in disponiveis:
                self._exibir_vulnerabilidade(vulnerabilidade)
            escolha = (
                input(
                    "Digite o ID de uma vulnerabilidade da lista, "
                    "ou N para cadastrar uma nova: "
                )
                .strip()
                .lower()
            )
        else:
            print("Não há vulnerabilidades cadastradas disponíveis para atribuir.")
            resposta = input("Deseja cadastrar uma nova? (s/n): ").strip().lower()
            escolha = "n" if resposta == "s" else ""

        if escolha == "n":
            vulnerabilidade = self._cadastrar_vulnerabilidade()
        elif escolha.isdigit():
            vulnerabilidade = self._encontrar_por_id(disponiveis, int(escolha))
            if vulnerabilidade is None:
                print("Erro: informe um ID da lista.")
        else:
            print("Operação cancelada.")
            return
        if vulnerabilidade is None:
            return

        if self._associar(vulnerabilidade, equipamento):
            print(
                f"Vulnerabilidade '{vulnerabilidade.descricao}' atribuída ao "
                f"equipamento '{equipamento.nome}'."
            )

    def _remover_vulnerabilidade_do_equipamento(self, equipamento: Equipamento) -> None:
        vulnerabilidades = self._servico_de_vulnerabilidades.listar_por_equipamento(
            equipamento.id
        )
        if not vulnerabilidades:
            print("Este equipamento não possui nenhuma vulnerabilidade registrada.")
            return

        for vulnerabilidade in vulnerabilidades:
            self._exibir_vulnerabilidade(vulnerabilidade)
        vulnerabilidade = self._ler_id_da_lista(
            vulnerabilidades, "Digite o ID da vulnerabilidade a remover: "
        )
        if vulnerabilidade is None:
            return

        if self._desassociar(vulnerabilidade, equipamento):
            print(
                "Vulnerabilidade removida do equipamento. "
                "Ela continua cadastrada no catálogo."
            )

    # --- Catálogo de vulnerabilidades ----------------------------------

    def _menu_do_catalogo_de_vulnerabilidades(self) -> None:
        while True:
            print("\n=== CATÁLOGO DE VULNERABILIDADES ===")
            print("1 - Listar vulnerabilidades")
            print("2 - Cadastrar vulnerabilidade")
            print("3 - Atualizar vulnerabilidade")
            print("4 - Excluir vulnerabilidade")
            print("5 - Equipamentos afetados por uma vulnerabilidade")
            print("0 - Voltar")
            opcao = input("Escolha uma opção: ").strip()

            if opcao == "1":
                self._listar_todas_as_vulnerabilidades()
            elif opcao == "2":
                vulnerabilidade = self._cadastrar_vulnerabilidade()
                if vulnerabilidade is not None:
                    self._oferecer_gerenciar_equipamentos_afetados(vulnerabilidade)
            elif opcao == "3":
                self._atualizar_vulnerabilidade()
            elif opcao == "4":
                self._excluir_vulnerabilidade()
            elif opcao == "5":
                vulnerabilidade = self._selecionar_vulnerabilidade_do_catalogo()
                if vulnerabilidade is not None:
                    self._menu_de_equipamentos_afetados(vulnerabilidade)
            elif opcao == "0":
                return
            else:
                print("Opção inválida. Tente novamente.\n")

    def _listar_todas_as_vulnerabilidades(self) -> bool:
        vulnerabilidades = self._servico_de_vulnerabilidades.listar_todas()
        if not vulnerabilidades:
            print("Nenhuma vulnerabilidade cadastrada.")
            return False
        for vulnerabilidade in vulnerabilidades:
            self._exibir_vulnerabilidade(vulnerabilidade)
        return True

    def _exibir_vulnerabilidade(self, vulnerabilidade: Vulnerabilidade) -> None:
        quantidade_de_equipamentos = len(
            self._servico_de_vulnerabilidades.listar_ids_de_equipamentos_afetados(
                vulnerabilidade.id
            )
        )
        print(
            f"[{vulnerabilidade.id}] {vulnerabilidade.descricao} | "
            f"Categoria: {vulnerabilidade.categoria} | "
            f"Nota CVSS: {vulnerabilidade.nota_cvss:.1f} | "
            f"Severidade: {rotulo_amigavel(vulnerabilidade.severidade.name)} | "
            f"Status: {rotulo_amigavel(vulnerabilidade.status.name)} | "
            f"Equipamentos afetados: {quantidade_de_equipamentos}"
        )

    def _cadastrar_vulnerabilidade(self) -> Optional[Vulnerabilidade]:
        print("\n--- Nova vulnerabilidade ---")
        descricao = input("Descrição: ")
        categoria = input("Categoria: ")
        nota_cvss = self._ler_nota_cvss()
        if nota_cvss is None:
            return None
        status = self._escolher_status()
        if status is None:
            return None

        try:
            vulnerabilidade = self._servico_de_vulnerabilidades.cadastrar(
                descricao, categoria, nota_cvss, status
            )
        except ErroDeValidacao as erro:
            print(f"Erro: {erro}")
            return None

        print(
            f"Vulnerabilidade cadastrada com sucesso (ID {vulnerabilidade.id}, "
            f"severidade {rotulo_amigavel(vulnerabilidade.severidade.name)})."
        )
        return vulnerabilidade

    def _atualizar_vulnerabilidade(self) -> None:
        vulnerabilidade = self._selecionar_vulnerabilidade_do_catalogo()
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
        self._oferecer_gerenciar_equipamentos_afetados(vulnerabilidade_atualizada)

    def _excluir_vulnerabilidade(self) -> None:
        vulnerabilidade = self._selecionar_vulnerabilidade_do_catalogo()
        if vulnerabilidade is None:
            return

        quantidade_de_equipamentos = len(
            self._servico_de_vulnerabilidades.listar_ids_de_equipamentos_afetados(
                vulnerabilidade.id
            )
        )
        confirmacao = (
            input(
                "Tem certeza que deseja excluir esta vulnerabilidade? Ela será "
                f"removida de {quantidade_de_equipamentos} equipamento(s). (s/n): "
            )
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

    # --- Equipamentos afetados por uma vulnerabilidade -------------------

    def _oferecer_gerenciar_equipamentos_afetados(
        self, vulnerabilidade: Vulnerabilidade
    ) -> None:
        resposta = (
            input(
                "Deseja listar ou atribuir equipamentos afetados por esta "
                "vulnerabilidade? (s/n): "
            )
            .strip()
            .lower()
        )
        if resposta == "s":
            self._menu_de_equipamentos_afetados(vulnerabilidade)

    def _menu_de_equipamentos_afetados(self, vulnerabilidade: Vulnerabilidade) -> None:
        while True:
            print(
                f"\n=== EQUIPAMENTOS AFETADOS POR: {vulnerabilidade.descricao} "
                f"(ID {vulnerabilidade.id}) ==="
            )
            print("1 - Listar equipamentos afetados")
            print("2 - Atribuir equipamento")
            print("3 - Remover equipamento")
            print("0 - Voltar")
            opcao = input("Escolha uma opção: ").strip()

            if opcao == "1":
                self._listar_equipamentos_afetados(vulnerabilidade)
            elif opcao == "2":
                self._atribuir_equipamento_a_vulnerabilidade(vulnerabilidade)
            elif opcao == "3":
                self._remover_equipamento_da_vulnerabilidade(vulnerabilidade)
            elif opcao == "0":
                return
            else:
                print("Opção inválida. Tente novamente.\n")

    def _equipamentos_afetados(
        self, vulnerabilidade: Vulnerabilidade
    ) -> List[Equipamento]:
        return [
            self._servico_de_equipamentos.buscar_por_id(equipamento_id)
            for equipamento_id in (
                self._servico_de_vulnerabilidades.listar_ids_de_equipamentos_afetados(
                    vulnerabilidade.id
                )
            )
        ]

    def _listar_equipamentos_afetados(self, vulnerabilidade: Vulnerabilidade) -> None:
        equipamentos = self._equipamentos_afetados(vulnerabilidade)
        if not equipamentos:
            print("Esta vulnerabilidade não afeta nenhum equipamento.")
            return
        for equipamento in equipamentos:
            self._exibir_equipamento(equipamento)

    def _atribuir_equipamento_a_vulnerabilidade(
        self, vulnerabilidade: Vulnerabilidade
    ) -> None:
        ids_afetados = {
            equipamento.id
            for equipamento in self._equipamentos_afetados(vulnerabilidade)
        }
        disponiveis = [
            equipamento
            for equipamento in self._servico_de_equipamentos.listar_todos()
            if equipamento.id not in ids_afetados
        ]
        if not disponiveis:
            print("Não há equipamentos disponíveis para atribuir.")
            return

        print("\nEquipamentos que ainda não são afetados por esta vulnerabilidade:")
        for equipamento in disponiveis:
            self._exibir_equipamento(equipamento)
        equipamento = self._ler_id_da_lista(
            disponiveis, "Digite o ID do equipamento a atribuir: "
        )
        if equipamento is None:
            return

        if self._associar(vulnerabilidade, equipamento):
            print(
                f"Equipamento '{equipamento.nome}' atribuído à vulnerabilidade "
                f"'{vulnerabilidade.descricao}'."
            )

    def _remover_equipamento_da_vulnerabilidade(
        self, vulnerabilidade: Vulnerabilidade
    ) -> None:
        equipamentos = self._equipamentos_afetados(vulnerabilidade)
        if not equipamentos:
            print("Esta vulnerabilidade não afeta nenhum equipamento.")
            return

        for equipamento in equipamentos:
            self._exibir_equipamento(equipamento)
        equipamento = self._ler_id_da_lista(
            equipamentos, "Digite o ID do equipamento a remover: "
        )
        if equipamento is None:
            return

        if self._desassociar(vulnerabilidade, equipamento):
            print("Equipamento removido da vulnerabilidade.")

    # --- Análise de risco -----------------------------------------------

    def _menu_de_analise_de_risco(self) -> None:
        while True:
            print("\n=== ANÁLISE DE RISCO ===")
            print("1 - Calcular risco próprio e risco efetivo dos equipamentos")
            print("2 - Exibir matrizes do modelo (M, v, f e A)")
            print("3 - Listar dependências entre equipamentos")
            print("4 - Cadastrar ou alterar dependência")
            print("5 - Remover dependência")
            print("0 - Voltar")
            opcao = input("Escolha uma opção: ").strip()

            if opcao == "1":
                self._exibir_riscos()
            elif opcao == "2":
                self._exibir_matrizes_do_modelo()
            elif opcao == "3":
                self._listar_dependencias()
            elif opcao == "4":
                self._salvar_dependencia()
            elif opcao == "5":
                self._remover_dependencia()
            elif opcao == "0":
                return
            else:
                print("Opção inválida. Tente novamente.\n")

    def _exibir_riscos(self) -> None:
        try:
            resultado = self._servico_de_analise_de_risco.calcular()
        except SistemaNaoInvertivelError as erro:
            print(f"Erro: {erro}")
            return

        if not resultado.riscos:
            print("Nenhum equipamento cadastrado.")
            return

        print("\n--- Risco dos equipamentos (do maior para o menor risco efetivo) ---")
        print(
            f"det(I - A) = {resultado.determinante:.4f} | "
            f"número de condição = {resultado.numero_de_condicao:.4f}"
        )
        print(
            f"{'ID':>4}  {'Nome':<28} {'Tipo':<20} {'Exposição':>9} "
            f"{'Próprio':>9} {'Herdado':>9} {'Efetivo':>9}"
        )
        riscos_ordenados = sorted(
            resultado.riscos, key=lambda risco: risco.risco_efetivo, reverse=True
        )
        for risco in riscos_ordenados:
            equipamento = risco.equipamento
            print(
                f"{equipamento.id:>4}  {equipamento.nome[:28]:<28} "
                f"{equipamento.ROTULO:<20} {equipamento.FATOR_DE_EXPOSICAO:>9.2f} "
                f"{risco.risco_proprio:>9.2f} {risco.risco_herdado:>9.2f} "
                f"{risco.risco_efetivo:>9.2f}"
            )

    def _exibir_matrizes_do_modelo(self) -> None:
        modelo = self._servico_de_analise_de_risco.montar_modelo()
        if not modelo.equipamentos:
            print("Nenhum equipamento cadastrado.")
            return

        rotulos_das_linhas = [f"E{e.id}" for e in modelo.equipamentos]
        rotulos_das_colunas = [f"V{v.id}" for v in modelo.vulnerabilidades]

        print("\nLinhas = equipamentos (E<id>); colunas = vulnerabilidades (V<id>).")
        print("\nM - matriz de incidência (1 = equipamento afetado):")
        self._imprimir_matriz(
            modelo.matriz_de_incidencia, rotulos_das_linhas, rotulos_das_colunas
        )
        print("\nv - vetor de severidade (nota CVSS de cada vulnerabilidade):")
        self._imprimir_matriz(
            modelo.vetor_de_severidade.reshape(1, -1), ["v"], rotulos_das_colunas
        )
        print("\nf - vetor de exposição (fator do tipo de cada equipamento):")
        self._imprimir_matriz(
            modelo.vetor_de_exposicao.reshape(1, -1), ["f"], rotulos_das_linhas
        )
        print("\nA - matriz de dependências (linha depende da coluna):")
        self._imprimir_matriz(
            modelo.matriz_de_dependencias, rotulos_das_linhas, rotulos_das_linhas
        )

    @staticmethod
    def _imprimir_matriz(
        matriz: np.ndarray,
        rotulos_das_linhas: List[str],
        rotulos_das_colunas: List[str],
    ) -> None:
        if matriz.size == 0:
            print("    (vazia)")
            return
        print("      " + "".join(f"{rotulo:>7}" for rotulo in rotulos_das_colunas))
        for rotulo, linha in zip(rotulos_das_linhas, matriz):
            print(f"{rotulo:>6}" + "".join(f"{valor:>7.2f}" for valor in linha))

    def _listar_dependencias(self) -> bool:
        dependencias = self._servico_de_dependencias.listar_todas()
        if not dependencias:
            print("Nenhuma dependência cadastrada.")
            return False
        for dependencia in dependencias:
            equipamento = self._servico_de_equipamentos.buscar_por_id(
                dependencia.equipamento_id
            )
            depende_de = self._servico_de_equipamentos.buscar_por_id(
                dependencia.depende_de_id
            )
            print(
                f"[{equipamento.id}] {equipamento.nome} depende de "
                f"[{depende_de.id}] {depende_de.nome} | "
                f"Fator: {dependencia.fator:.2f}"
            )
        return True

    def _salvar_dependencia(self) -> None:
        print("\n--- Cadastrar ou alterar dependência ---")
        print("Equipamento que DEPENDE de outro:")
        equipamento = self._selecionar_equipamento_por_id()
        if equipamento is None:
            return
        print(
            "Soma atual dos fatores deste equipamento: "
            f"{self._servico_de_dependencias.soma_dos_fatores(equipamento.id):.2f} "
            "(a soma deve ficar menor que 1)."
        )
        print("Equipamento do qual ele depende:")
        depende_de = self._selecionar_equipamento_por_id()
        if depende_de is None:
            return
        fator = self._ler_fator_de_dependencia()
        if fator is None:
            return

        try:
            self._servico_de_dependencias.salvar(equipamento.id, depende_de.id, fator)
        except (ErroDeValidacao, EquipamentoNaoEncontradoError) as erro:
            print(f"Erro: {erro}")
            return

        print(
            f"Dependência salva: '{equipamento.nome}' herda {fator:.0%} do risco "
            f"de '{depende_de.nome}'."
        )

    def _remover_dependencia(self) -> None:
        print("\n--- Remover dependência ---")
        if not self._listar_dependencias():
            return
        texto_equipamento = input("ID do equipamento que depende: ").strip()
        texto_depende_de = input("ID do equipamento do qual ele depende: ").strip()
        if not (texto_equipamento.isdigit() and texto_depende_de.isdigit()):
            print("Erro: informe números de ID válidos.")
            return

        try:
            self._servico_de_dependencias.excluir(
                int(texto_equipamento), int(texto_depende_de)
            )
        except ErroDeValidacao as erro:
            print(f"Erro: {erro}")
            return

        print("Dependência removida com sucesso.")

    @staticmethod
    def _ler_fator_de_dependencia() -> Optional[float]:
        texto_fator = input("Fator de dependência (0 a 0.99, ex.: 0.3): ").strip()
        try:
            return float(texto_fator.replace(",", "."))
        except ValueError:
            print("Erro: informe o fator como um número (ex.: 0.3).")
            return None

    # --- Associações -------------------------------------------------------

    def _associar(
        self, vulnerabilidade: Vulnerabilidade, equipamento: Equipamento
    ) -> bool:
        try:
            self._servico_de_vulnerabilidades.associar(
                vulnerabilidade.id, equipamento.id
            )
        except (
            ErroDeValidacao,
            EquipamentoNaoEncontradoError,
            VulnerabilidadeNaoEncontradaError,
        ) as erro:
            print(f"Erro: {erro}")
            return False
        return True

    def _desassociar(
        self, vulnerabilidade: Vulnerabilidade, equipamento: Equipamento
    ) -> bool:
        try:
            self._servico_de_vulnerabilidades.desassociar(
                vulnerabilidade.id, equipamento.id
            )
        except (ErroDeValidacao, VulnerabilidadeNaoEncontradaError) as erro:
            print(f"Erro: {erro}")
            return False
        return True

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

    def _selecionar_vulnerabilidade_do_catalogo(self) -> Optional[Vulnerabilidade]:
        if not self._listar_todas_as_vulnerabilidades():
            return None
        return self._ler_id_da_lista(
            self._servico_de_vulnerabilidades.listar_todas(),
            "Digite o ID da vulnerabilidade: ",
        )

    @classmethod
    def _ler_id_da_lista(cls, itens: Sequence[T], mensagem: str) -> Optional[T]:
        texto_id = input(mensagem).strip()
        if not texto_id.isdigit():
            print("Erro: informe um número de ID válido.")
            return None
        item = cls._encontrar_por_id(itens, int(texto_id))
        if item is None:
            print("Erro: informe um ID da lista.")
        return item

    @staticmethod
    def _encontrar_por_id(itens: Sequence[T], id_procurado: int) -> Optional[T]:
        return next((item for item in itens if item.id == id_procurado), None)

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

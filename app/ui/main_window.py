"""Janela principal da aplicação: lista os ativos e dá acesso às demais telas."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from app.exceptions import AtivoNaoEncontradoError
from app.models.ativo import Ativo
from app.models.enums import rotulo_amigavel
from app.services.ativo_service import AtivoService
from app.services.vulnerabilidade_service import VulnerabilidadeService
from app.ui.ativo_form import JanelaFormularioAtivo
from app.ui.componentes import criar_tabela
from app.ui.vulnerabilidade_window import JanelaVulnerabilidades

COLUNAS_DA_TABELA = (
    ("id", "ID", 50),
    ("nome", "Nome / Hostname", 180),
    ("responsavel", "Responsável", 150),
    ("setor", "Setor / Localização", 150),
    ("tipo", "Tipo", 140),
    ("vulnerabilidades", "Vulnerabilidades", 110),
)


class JanelaPrincipal(tk.Tk):
    """Tela inicial do sistema: exibe o inventário de ativos e o menu de ações.

    Esta classe atua como "controladora" da interface: ela não conhece
    detalhes de SQL nem de validação, apenas chama os serviços e atualiza
    os componentes visuais de acordo com o resultado.
    """

    def __init__(
        self,
        servico_de_ativos: AtivoService,
        servico_de_vulnerabilidades: VulnerabilidadeService,
    ):
        super().__init__()
        self._servico_de_ativos = servico_de_ativos
        self._servico_de_vulnerabilidades = servico_de_vulnerabilidades

        self.title("Inventário de Ativos de TI")
        self.geometry("920x480")
        self.minsize(760, 420)

        self._construir_widgets()
        self._atualizar_tabela_de_ativos(self._servico_de_ativos.listar_todos())

    def _construir_widgets(self) -> None:
        quadro = ttk.Frame(self, padding=10)
        quadro.pack(fill="both", expand=True)

        quadro_de_busca = ttk.Frame(quadro)
        quadro_de_busca.pack(fill="x", pady=(0, 10))
        ttk.Label(quadro_de_busca, text="Buscar por ID ou nome/hostname:").pack(
            side="left"
        )
        self._campo_de_busca = ttk.Entry(quadro_de_busca, width=30)
        self._campo_de_busca.pack(side="left", padx=8)
        self._campo_de_busca.bind("<Return>", lambda evento: self._buscar_ativos())
        ttk.Button(quadro_de_busca, text="Buscar", command=self._buscar_ativos).pack(
            side="left"
        )
        ttk.Button(
            quadro_de_busca, text="Limpar busca", command=self._limpar_busca
        ).pack(side="left", padx=8)

        self._tabela = criar_tabela(quadro, COLUNAS_DA_TABELA)

        quadro_de_botoes = ttk.Frame(quadro)
        quadro_de_botoes.pack(fill="x", pady=(10, 0))
        ttk.Button(
            quadro_de_botoes,
            text="Novo Ativo",
            command=self._abrir_formulario_novo_ativo,
        ).pack(side="left", padx=5)
        ttk.Button(
            quadro_de_botoes,
            text="Editar Ativo",
            command=self._abrir_formulario_editar_ativo,
        ).pack(side="left", padx=5)
        ttk.Button(
            quadro_de_botoes,
            text="Excluir Ativo",
            command=self._excluir_ativo_selecionado,
        ).pack(side="left", padx=5)
        ttk.Button(
            quadro_de_botoes,
            text="Vulnerabilidades",
            command=self._abrir_janela_de_vulnerabilidades,
        ).pack(side="left", padx=5)

    def _atualizar_tabela_de_ativos(self, ativos: list[Ativo]) -> None:
        self._tabela.delete(*self._tabela.get_children())
        for ativo in ativos:
            quantidade_de_vulnerabilidades = len(
                self._servico_de_vulnerabilidades.listar_por_ativo(ativo.id)
            )
            self._tabela.insert(
                "",
                "end",
                iid=str(ativo.id),
                values=(
                    ativo.id,
                    ativo.nome,
                    ativo.responsavel,
                    ativo.setor,
                    rotulo_amigavel(ativo.tipo.name),
                    quantidade_de_vulnerabilidades,
                ),
            )

    def _ativo_selecionado(self) -> Optional[Ativo]:
        selecao = self._tabela.selection()
        if not selecao:
            messagebox.showwarning("Nenhuma seleção", "Selecione um ativo na tabela.")
            return None

        ativo_id = int(selecao[0])
        try:
            return self._servico_de_ativos.buscar_por_id(ativo_id)
        except AtivoNaoEncontradoError as erro:
            messagebox.showerror("Erro", str(erro))
            return None

    def _buscar_ativos(self) -> None:
        texto_buscado = self._campo_de_busca.get().strip()

        if texto_buscado.isdigit():
            try:
                ativo_encontrado = self._servico_de_ativos.buscar_por_id(
                    int(texto_buscado)
                )
                self._atualizar_tabela_de_ativos([ativo_encontrado])
                return
            except AtivoNaoEncontradoError:
                self._atualizar_tabela_de_ativos([])
                return

        ativos_encontrados = self._servico_de_ativos.buscar_por_nome(texto_buscado)
        self._atualizar_tabela_de_ativos(ativos_encontrados)

    def _limpar_busca(self) -> None:
        self._campo_de_busca.delete(0, "end")
        self._atualizar_tabela_de_ativos(self._servico_de_ativos.listar_todos())

    def _abrir_formulario_novo_ativo(self) -> None:
        JanelaFormularioAtivo(
            janela_pai=self,
            servico_de_ativos=self._servico_de_ativos,
            ao_salvar_com_sucesso=self._ao_salvar_ativo,
        )

    def _abrir_formulario_editar_ativo(self) -> None:
        ativo = self._ativo_selecionado()
        if ativo is None:
            return

        JanelaFormularioAtivo(
            janela_pai=self,
            servico_de_ativos=self._servico_de_ativos,
            ao_salvar_com_sucesso=self._ao_salvar_ativo,
            ativo_para_editar=ativo,
        )

    def _ao_salvar_ativo(self, ativo_salvo: Ativo, ativo_recem_criado: bool) -> None:
        self._atualizar_tabela_de_ativos(self._servico_de_ativos.listar_todos())

        if ativo_recem_criado:
            deseja_cadastrar_vulnerabilidades = messagebox.askyesno(
                "Vulnerabilidades iniciais",
                f"Ativo '{ativo_salvo.nome}' cadastrado com sucesso!\n\n"
                "Deseja cadastrar vulnerabilidades para este ativo agora?",
            )
            if deseja_cadastrar_vulnerabilidades:
                self._abrir_janela_de_vulnerabilidades_para(ativo_salvo)

    def _excluir_ativo_selecionado(self) -> None:
        ativo = self._ativo_selecionado()
        if ativo is None:
            return

        confirmou = messagebox.askyesno(
            "Confirmar exclusão",
            f"Deseja realmente excluir o ativo '{ativo.nome}'?\n"
            "Todas as vulnerabilidades associadas a ele também serão excluídas.",
        )
        if not confirmou:
            return

        self._servico_de_ativos.excluir(ativo.id)
        self._servico_de_vulnerabilidades.esquecer_vulnerabilidades_do_ativo(ativo.id)
        self._atualizar_tabela_de_ativos(self._servico_de_ativos.listar_todos())

    def _abrir_janela_de_vulnerabilidades(self) -> None:
        ativo = self._ativo_selecionado()
        if ativo is None:
            return
        self._abrir_janela_de_vulnerabilidades_para(ativo)

    def _abrir_janela_de_vulnerabilidades_para(self, ativo: Ativo) -> None:
        janela = JanelaVulnerabilidades(
            janela_pai=self,
            servico_de_vulnerabilidades=self._servico_de_vulnerabilidades,
            ativo=ativo,
        )
        # Aguarda o fechamento da janela de vulnerabilidades antes de
        # continuar, para então atualizar a contagem exibida na tabela.
        self.wait_window(janela)
        self._atualizar_tabela_de_ativos(self._servico_de_ativos.listar_todos())

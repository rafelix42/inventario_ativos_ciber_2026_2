"""Janela que lista, cadastra, edita e exclui as vulnerabilidades de um ativo."""

import tkinter as tk
from tkinter import messagebox, ttk

from app.exceptions import VulnerabilidadeNaoEncontradaError
from app.models.ativo import Ativo
from app.models.enums import rotulo_amigavel
from app.services.vulnerabilidade_service import VulnerabilidadeService
from app.ui.componentes import criar_tabela
from app.ui.vulnerabilidade_form import JanelaFormularioVulnerabilidade

COLUNAS_DA_TABELA = (
    ("id", "ID", 40),
    ("descricao", "Descrição", 200),
    ("categoria", "Categoria", 110),
    ("nota_cvss", "Nota CVSS", 80),
    ("severidade", "Severidade", 100),
    ("status", "Status", 130),
)


class JanelaVulnerabilidades(tk.Toplevel):
    """Mostra as vulnerabilidades associadas a um ativo específico.

    Atende ao requisito de deixar explícito quando o ativo não possui
    nenhuma vulnerabilidade cadastrada (uma mensagem é exibida acima da
    tabela nesse caso).
    """

    def __init__(
        self,
        janela_pai: tk.Widget,
        servico_de_vulnerabilidades: VulnerabilidadeService,
        ativo: Ativo,
    ):
        super().__init__(janela_pai)
        self._servico_de_vulnerabilidades = servico_de_vulnerabilidades
        self._ativo = ativo

        self.title(f"Vulnerabilidades de: {ativo.nome}")
        self.geometry("640x380")
        self.transient(janela_pai)

        self._construir_widgets()
        self._atualizar_tabela()

        self.grab_set()
        self.focus_set()

    def _construir_widgets(self) -> None:
        quadro = ttk.Frame(self, padding=10)
        quadro.pack(fill="both", expand=True)

        self._rotulo_de_situacao = ttk.Label(quadro, text="", foreground="#555555")
        self._rotulo_de_situacao.pack(fill="x", pady=(0, 8))

        self._tabela = criar_tabela(quadro, COLUNAS_DA_TABELA)

        quadro_de_botoes = ttk.Frame(quadro)
        quadro_de_botoes.pack(fill="x", pady=(10, 0))
        ttk.Button(
            quadro_de_botoes, text="Nova", command=self._abrir_formulario_nova
        ).pack(side="left", padx=5)
        ttk.Button(
            quadro_de_botoes, text="Editar", command=self._abrir_formulario_editar
        ).pack(side="left", padx=5)
        ttk.Button(
            quadro_de_botoes, text="Excluir", command=self._excluir_selecionada
        ).pack(side="left", padx=5)
        ttk.Button(quadro_de_botoes, text="Fechar", command=self.destroy).pack(
            side="right", padx=5
        )

    def _atualizar_tabela(self) -> None:
        self._tabela.delete(*self._tabela.get_children())
        vulnerabilidades = self._servico_de_vulnerabilidades.listar_por_ativo(
            self._ativo.id
        )

        if not vulnerabilidades:
            self._rotulo_de_situacao.configure(
                text="Este ativo não possui nenhuma vulnerabilidade registrada."
            )
            return

        self._rotulo_de_situacao.configure(
            text=f"{len(vulnerabilidades)} vulnerabilidade(s) registrada(s)."
        )
        for vulnerabilidade in vulnerabilidades:
            self._tabela.insert(
                "",
                "end",
                iid=str(vulnerabilidade.id),
                values=(
                    vulnerabilidade.id,
                    vulnerabilidade.descricao,
                    vulnerabilidade.categoria,
                    f"{vulnerabilidade.nota_cvss:.1f}",
                    rotulo_amigavel(vulnerabilidade.severidade.name),
                    rotulo_amigavel(vulnerabilidade.status.name),
                ),
            )

    def _vulnerabilidade_id_selecionada(self):
        selecao = self._tabela.selection()
        if not selecao:
            messagebox.showwarning(
                "Nenhuma seleção",
                "Selecione uma vulnerabilidade na tabela.",
                parent=self,
            )
            return None
        return int(selecao[0])

    def _abrir_formulario_nova(self) -> None:
        JanelaFormularioVulnerabilidade(
            janela_pai=self,
            servico_de_vulnerabilidades=self._servico_de_vulnerabilidades,
            ativo_id=self._ativo.id,
            ao_salvar_com_sucesso=self._atualizar_tabela,
        )

    def _abrir_formulario_editar(self) -> None:
        vulnerabilidade_id = self._vulnerabilidade_id_selecionada()
        if vulnerabilidade_id is None:
            return

        vulnerabilidade = next(
            v
            for v in self._servico_de_vulnerabilidades.listar_por_ativo(self._ativo.id)
            if v.id == vulnerabilidade_id
        )
        JanelaFormularioVulnerabilidade(
            janela_pai=self,
            servico_de_vulnerabilidades=self._servico_de_vulnerabilidades,
            ativo_id=self._ativo.id,
            ao_salvar_com_sucesso=self._atualizar_tabela,
            vulnerabilidade_para_editar=vulnerabilidade,
        )

    def _excluir_selecionada(self) -> None:
        vulnerabilidade_id = self._vulnerabilidade_id_selecionada()
        if vulnerabilidade_id is None:
            return

        confirmou = messagebox.askyesno(
            "Confirmar exclusão",
            "Deseja realmente excluir esta vulnerabilidade?",
            parent=self,
        )
        if not confirmou:
            return

        try:
            self._servico_de_vulnerabilidades.excluir(vulnerabilidade_id)
        except VulnerabilidadeNaoEncontradaError as erro:
            messagebox.showerror("Erro", str(erro), parent=self)
            return

        self._atualizar_tabela()

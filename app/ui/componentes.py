"""Componentes reutilizados pelas janelas da interface gráfica."""

import tkinter as tk
from tkinter import ttk


def criar_tabela(
    quadro: ttk.Frame, colunas: tuple[tuple[str, str, int], ...]
) -> ttk.Treeview:
    """Cria e posiciona uma tabela com as colunas (identificador, título, largura)."""
    tabela = ttk.Treeview(
        quadro, columns=[coluna for coluna, _, _ in colunas], show="headings"
    )
    for coluna, titulo, largura in colunas:
        tabela.heading(coluna, text=titulo)
        tabela.column(coluna, width=largura, anchor="w")
    tabela.pack(fill="both", expand=True)
    return tabela


class FormularioModal(tk.Toplevel):
    """Base dos formulários de cadastro/edição exibidos como janela modal.

    As subclasses chamam 'super().__init__', guardam seus próprios atributos
    e, por fim, chamam '_exibir()', que monta a janela usando os métodos
    '_construir_campos', '_preencher_campos_se_estiver_editando' e '_salvar'.
    """

    LINHA_DOS_BOTOES = 5

    def __init__(self, janela_pai: tk.Widget, titulo: str):
        super().__init__(janela_pai)
        self.title(titulo)
        self.resizable(False, False)
        self.transient(janela_pai)

    def _exibir(self) -> None:
        quadro = ttk.Frame(self, padding=15)
        quadro.grid(row=0, column=0, sticky="nsew")

        self._construir_campos(quadro)

        quadro_de_botoes = ttk.Frame(quadro)
        quadro_de_botoes.grid(
            row=self.LINHA_DOS_BOTOES, column=0, columnspan=2, pady=(15, 0)
        )
        ttk.Button(quadro_de_botoes, text="Salvar", command=self._salvar).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(quadro_de_botoes, text="Cancelar", command=self.destroy).grid(
            row=0, column=1, padx=5
        )

        self._preencher_campos_se_estiver_editando()

        self.grab_set()
        self.focus_set()

    def _construir_campos(self, quadro: ttk.Frame) -> None:
        raise NotImplementedError

    def _preencher_campos_se_estiver_editando(self) -> None:
        raise NotImplementedError

    def _salvar(self) -> None:
        raise NotImplementedError

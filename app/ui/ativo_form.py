"""Janela (formulário) usada para cadastrar ou editar um ativo de TI."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from app.exceptions import ErroDeValidacao
from app.models.ativo import Ativo
from app.models.enums import TipoAtivo, rotulo_amigavel
from app.services.ativo_service import AtivoService
from app.ui.componentes import FormularioModal


class JanelaFormularioAtivo(FormularioModal):
    """Formulário para cadastro ou edição de um ativo de TI.

    Quando 'ativo_para_editar' é None, o formulário funciona no modo de
    cadastro. Quando recebe um Ativo já existente, funciona no modo de
    edição, com os campos preenchidos e o nome bloqueado para alteração.
    """

    def __init__(
        self,
        janela_pai: tk.Widget,
        servico_de_ativos: AtivoService,
        ao_salvar_com_sucesso: Callable[[Ativo, bool], None],
        ativo_para_editar: Optional[Ativo] = None,
    ):
        super().__init__(
            janela_pai, "Editar Ativo" if ativo_para_editar else "Novo Ativo"
        )
        self._servico_de_ativos = servico_de_ativos
        self._ao_salvar_com_sucesso = ao_salvar_com_sucesso
        self._ativo_para_editar = ativo_para_editar
        self._rotulos_por_tipo = {
            rotulo_amigavel(tipo.name): tipo for tipo in TipoAtivo
        }

        self._exibir()

    def _construir_campos(self, quadro: ttk.Frame) -> None:
        ttk.Label(quadro, text="Nome / Hostname:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self._campo_nome = ttk.Entry(quadro, width=35)
        self._campo_nome.grid(row=0, column=1, pady=4)

        ttk.Label(quadro, text="Responsável:").grid(row=1, column=0, sticky="w", pady=4)
        self._campo_responsavel = ttk.Entry(quadro, width=35)
        self._campo_responsavel.grid(row=1, column=1, pady=4)

        ttk.Label(quadro, text="Setor / Localização:").grid(
            row=2, column=0, sticky="w", pady=4
        )
        self._campo_setor = ttk.Entry(quadro, width=35)
        self._campo_setor.grid(row=2, column=1, pady=4)

        ttk.Label(quadro, text="Tipo de Ativo:").grid(
            row=3, column=0, sticky="w", pady=4
        )
        self._campo_tipo = ttk.Combobox(
            quadro,
            values=list(self._rotulos_por_tipo.keys()),
            state="readonly",
            width=33,
        )
        self._campo_tipo.grid(row=3, column=1, pady=4)

        ttk.Label(quadro, text="Descrição:").grid(row=4, column=0, sticky="nw", pady=4)
        self._campo_descricao = tk.Text(quadro, width=27, height=4)
        self._campo_descricao.grid(row=4, column=1, pady=4)

        if self._ativo_para_editar is not None:
            # O nome não é editável para não invalidar buscas já realizadas
            # por quem estiver usando o identificador único do ativo.
            self._campo_nome.configure(state="disabled")

    def _preencher_campos_se_estiver_editando(self) -> None:
        if self._ativo_para_editar is None:
            self._campo_tipo.current(0)
            return

        ativo = self._ativo_para_editar
        self._campo_nome.insert(0, ativo.nome)
        self._campo_responsavel.insert(0, ativo.responsavel)
        self._campo_setor.insert(0, ativo.setor)
        self._campo_descricao.insert("1.0", ativo.descricao)
        self._campo_tipo.set(rotulo_amigavel(ativo.tipo.name))

    def _salvar(self) -> None:
        tipo_selecionado = self._rotulos_por_tipo.get(self._campo_tipo.get())
        descricao_informada = self._campo_descricao.get("1.0", "end").strip()
        esta_criando_um_novo_ativo = self._ativo_para_editar is None

        try:
            if esta_criando_um_novo_ativo:
                ativo_salvo = self._servico_de_ativos.cadastrar(
                    nome=self._campo_nome.get(),
                    responsavel=self._campo_responsavel.get(),
                    setor=self._campo_setor.get(),
                    tipo=tipo_selecionado,
                    descricao=descricao_informada,
                )
            else:
                ativo_salvo = self._servico_de_ativos.atualizar(
                    ativo_id=self._ativo_para_editar.id,
                    responsavel=self._campo_responsavel.get(),
                    setor=self._campo_setor.get(),
                    tipo=tipo_selecionado,
                    descricao=descricao_informada,
                )
        except ErroDeValidacao as erro:
            messagebox.showerror("Dados inválidos", str(erro), parent=self)
            return

        self._ao_salvar_com_sucesso(ativo_salvo, esta_criando_um_novo_ativo)
        self.destroy()

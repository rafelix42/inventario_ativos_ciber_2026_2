"""Janela (formulário) usada para cadastrar ou editar uma vulnerabilidade."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from app.exceptions import ErroDeValidacao
from app.models.enums import Severidade, StatusVulnerabilidade, rotulo_amigavel
from app.models.vulnerabilidade import Vulnerabilidade
from app.services.vulnerabilidade_service import VulnerabilidadeService
from app.ui.componentes import FormularioModal


class JanelaFormularioVulnerabilidade(FormularioModal):
    """Formulário para cadastro ou edição de uma vulnerabilidade de um ativo.

    Quando 'vulnerabilidade_para_editar' é None, o formulário cadastra uma
    vulnerabilidade nova para o ativo indicado por 'ativo_id'. Caso
    contrário, edita a vulnerabilidade recebida.

    O usuário não escolhe a severidade diretamente: ele informa uma nota
    CVSS (0.0 a 10.0) e a severidade correspondente (Nenhuma/Baixa/Média/
    Alta/Crítica) é calculada e exibida automaticamente como prévia.
    """

    def __init__(
        self,
        janela_pai: tk.Widget,
        servico_de_vulnerabilidades: VulnerabilidadeService,
        ativo_id: int,
        ao_salvar_com_sucesso: Callable[[], None],
        vulnerabilidade_para_editar: Optional[Vulnerabilidade] = None,
    ):
        super().__init__(
            janela_pai,
            (
                "Editar Vulnerabilidade"
                if vulnerabilidade_para_editar
                else "Nova Vulnerabilidade"
            ),
        )
        self._servico_de_vulnerabilidades = servico_de_vulnerabilidades
        self._ativo_id = ativo_id
        self._ao_salvar_com_sucesso = ao_salvar_com_sucesso
        self._vulnerabilidade_para_editar = vulnerabilidade_para_editar

        self._rotulos_por_status = {
            rotulo_amigavel(status.name): status for status in StatusVulnerabilidade
        }

        self._exibir()

    def _construir_campos(self, quadro: ttk.Frame) -> None:
        ttk.Label(quadro, text="Descrição:").grid(row=0, column=0, sticky="w", pady=4)
        self._campo_descricao = ttk.Entry(quadro, width=40)
        self._campo_descricao.grid(row=0, column=1, pady=4)

        ttk.Label(quadro, text="Categoria:").grid(row=1, column=0, sticky="w", pady=4)
        self._campo_categoria = ttk.Entry(quadro, width=40)
        self._campo_categoria.grid(row=1, column=1, pady=4)

        ttk.Label(quadro, text="Nota CVSS (0.0 a 10.0):").grid(
            row=2, column=0, sticky="w", pady=4
        )
        self._campo_nota_cvss = ttk.Entry(quadro, width=40)
        self._campo_nota_cvss.grid(row=2, column=1, pady=4)
        self._campo_nota_cvss.bind(
            "<KeyRelease>", lambda evento: self._atualizar_previa_da_severidade()
        )

        self._rotulo_severidade_calculada = ttk.Label(
            quadro, text="Severidade: -", foreground="#555555"
        )
        self._rotulo_severidade_calculada.grid(row=3, column=1, sticky="w")

        ttk.Label(quadro, text="Status:").grid(row=4, column=0, sticky="w", pady=4)
        self._campo_status = ttk.Combobox(
            quadro,
            values=list(self._rotulos_por_status.keys()),
            state="readonly",
            width=38,
        )
        self._campo_status.grid(row=4, column=1, pady=4)

    def _preencher_campos_se_estiver_editando(self) -> None:
        if self._vulnerabilidade_para_editar is None:
            self._campo_status.current(0)
            return

        vulnerabilidade = self._vulnerabilidade_para_editar
        self._campo_descricao.insert(0, vulnerabilidade.descricao)
        self._campo_categoria.insert(0, vulnerabilidade.categoria)
        self._campo_nota_cvss.insert(0, f"{vulnerabilidade.nota_cvss:.1f}")
        self._campo_status.set(rotulo_amigavel(vulnerabilidade.status.name))
        self._atualizar_previa_da_severidade()

    def _ler_nota_cvss_informada(self) -> Optional[float]:
        """Converte o texto do campo em número, aceitando vírgula ou ponto decimal.

        Retorna None quando o texto não representa um número válido.
        """
        texto_informado = self._campo_nota_cvss.get().strip().replace(",", ".")
        try:
            return float(texto_informado)
        except ValueError:
            return None

    def _atualizar_previa_da_severidade(self) -> None:
        nota_cvss = self._ler_nota_cvss_informada()
        if nota_cvss is None or not 0.0 <= nota_cvss <= 10.0:
            self._rotulo_severidade_calculada.configure(text="Severidade: -")
            return

        severidade = Severidade.a_partir_da_nota_cvss(nota_cvss)
        self._rotulo_severidade_calculada.configure(
            text=f"Severidade: {rotulo_amigavel(severidade.name)}"
        )

    def _salvar(self) -> None:
        nota_cvss = self._ler_nota_cvss_informada()
        if nota_cvss is None:
            messagebox.showerror(
                "Dados inválidos",
                "Informe a nota CVSS como um número entre 0.0 e 10.0.",
                parent=self,
            )
            return

        status_selecionado = self._rotulos_por_status.get(self._campo_status.get())

        try:
            if self._vulnerabilidade_para_editar is None:
                self._servico_de_vulnerabilidades.cadastrar(
                    ativo_id=self._ativo_id,
                    descricao=self._campo_descricao.get(),
                    categoria=self._campo_categoria.get(),
                    nota_cvss=nota_cvss,
                    status=status_selecionado,
                )
            else:
                self._servico_de_vulnerabilidades.atualizar(
                    vulnerabilidade_id=self._vulnerabilidade_para_editar.id,
                    descricao=self._campo_descricao.get(),
                    categoria=self._campo_categoria.get(),
                    nota_cvss=nota_cvss,
                    status=status_selecionado,
                )
        except ErroDeValidacao as erro:
            messagebox.showerror("Dados inválidos", str(erro), parent=self)
            return

        self._ao_salvar_com_sucesso()
        self.destroy()

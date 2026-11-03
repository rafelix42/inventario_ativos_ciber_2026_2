"""Repositório responsável pelas operações da tabela 'dependencias'."""

import sqlite3
from typing import List

from app.models.dependencia import Dependencia
from app.repositories.database import ConexaoBancoDeDados


class DependenciaRepository:
    """Traduz operações sobre dependências entre equipamentos em comandos SQL."""

    def __init__(self, banco_de_dados: ConexaoBancoDeDados):
        self._conexao = banco_de_dados.conexao

    def salvar(self, dependencia: Dependencia) -> None:
        """Cadastra a dependência ou, se o par de equipamentos já existir,
        substitui o fator pelo novo valor."""
        self._conexao.execute(
            """
            INSERT INTO dependencias (equipamento_id, depende_de_id, fator)
            VALUES (?, ?, ?)
            ON CONFLICT (equipamento_id, depende_de_id)
            DO UPDATE SET fator = excluded.fator
            """,
            (dependencia.equipamento_id, dependencia.depende_de_id, dependencia.fator),
        )
        self._conexao.commit()

    def excluir(self, equipamento_id: int, depende_de_id: int) -> None:
        """Remove a dependência entre os dois equipamentos."""
        self._conexao.execute(
            "DELETE FROM dependencias WHERE equipamento_id = ? AND depende_de_id = ?",
            (equipamento_id, depende_de_id),
        )
        self._conexao.commit()

    def listar_todas(self) -> List[Dependencia]:
        """Retorna todas as dependências, ordenadas pelos ids dos equipamentos."""
        linhas = self._conexao.execute(
            "SELECT * FROM dependencias ORDER BY equipamento_id, depende_de_id"
        ).fetchall()
        return [self._converter_linha_em_dependencia(linha) for linha in linhas]

    @staticmethod
    def _converter_linha_em_dependencia(linha: sqlite3.Row) -> Dependencia:
        return Dependencia(
            equipamento_id=linha["equipamento_id"],
            depende_de_id=linha["depende_de_id"],
            fator=linha["fator"],
        )

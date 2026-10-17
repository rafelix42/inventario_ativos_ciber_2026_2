"""Repositório responsável pelas operações de CRUD da tabela 'vulnerabilidades'."""

import sqlite3
from typing import List, Optional

from app.models.enums import StatusVulnerabilidade
from app.models.vulnerabilidade import Vulnerabilidade
from app.repositories.database import ConexaoBancoDeDados


class VulnerabilidadeRepository:
    """Traduz operações de CRUD de Vulnerabilidade em comandos SQL no SQLite."""

    def __init__(self, banco_de_dados: ConexaoBancoDeDados):
        self._conexao = banco_de_dados.conexao

    def inserir(self, vulnerabilidade: Vulnerabilidade) -> Vulnerabilidade:
        """Insere uma nova vulnerabilidade e preenche o 'id' gerado pelo banco."""
        cursor = self._conexao.execute(
            """
            INSERT INTO vulnerabilidades
                (equipamento_id, descricao, categoria, nota_cvss, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                vulnerabilidade.equipamento_id,
                vulnerabilidade.descricao,
                vulnerabilidade.categoria,
                vulnerabilidade.nota_cvss,
                vulnerabilidade.status.name,
            ),
        )
        self._conexao.commit()
        vulnerabilidade.id = cursor.lastrowid
        return vulnerabilidade

    def atualizar(self, vulnerabilidade: Vulnerabilidade) -> None:
        """Grava as alterações de uma vulnerabilidade já existente."""
        self._conexao.execute(
            """
            UPDATE vulnerabilidades
            SET descricao = ?, categoria = ?, nota_cvss = ?, status = ?
            WHERE id = ?
            """,
            (
                vulnerabilidade.descricao,
                vulnerabilidade.categoria,
                vulnerabilidade.nota_cvss,
                vulnerabilidade.status.name,
                vulnerabilidade.id,
            ),
        )
        self._conexao.commit()

    def excluir(self, vulnerabilidade_id: int) -> None:
        """Remove a vulnerabilidade com o ID informado."""
        self._conexao.execute(
            "DELETE FROM vulnerabilidades WHERE id = ?", (vulnerabilidade_id,)
        )
        self._conexao.commit()

    def buscar_por_id(self, vulnerabilidade_id: int) -> Optional[Vulnerabilidade]:
        """Retorna a vulnerabilidade com o ID informado, ou None se não existir."""
        linha = self._conexao.execute(
            "SELECT * FROM vulnerabilidades WHERE id = ?", (vulnerabilidade_id,)
        ).fetchone()
        return self._converter_linha_em_vulnerabilidade(linha) if linha else None

    def listar_por_equipamento(self, equipamento_id: int) -> List[Vulnerabilidade]:
        """Retorna as vulnerabilidades de um equipamento, ordenadas por ID."""
        linhas = self._conexao.execute(
            "SELECT * FROM vulnerabilidades WHERE equipamento_id = ? ORDER BY id",
            (equipamento_id,),
        ).fetchall()
        return [self._converter_linha_em_vulnerabilidade(linha) for linha in linhas]

    def listar_todas(self) -> List[Vulnerabilidade]:
        """Retorna todas as vulnerabilidades, ordenadas por ID."""
        linhas = self._conexao.execute(
            "SELECT * FROM vulnerabilidades ORDER BY id"
        ).fetchall()
        return [self._converter_linha_em_vulnerabilidade(linha) for linha in linhas]

    @staticmethod
    def _converter_linha_em_vulnerabilidade(linha: sqlite3.Row) -> Vulnerabilidade:
        return Vulnerabilidade(
            id=linha["id"],
            equipamento_id=linha["equipamento_id"],
            descricao=linha["descricao"],
            categoria=linha["categoria"],
            nota_cvss=linha["nota_cvss"],
            status=StatusVulnerabilidade[linha["status"]],
        )

"""Repositório responsável pelas operações de CRUD da tabela 'vulnerabilidades'
e pelas associações entre vulnerabilidades e equipamentos."""

import sqlite3
from typing import List, Optional, Tuple

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
            INSERT INTO vulnerabilidades (descricao, categoria, nota_cvss, status)
            VALUES (?, ?, ?, ?)
            """,
            (
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
        """Remove a vulnerabilidade com o ID informado. As associações com
        equipamentos são removidas pelo banco (ON DELETE CASCADE)."""
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

    def listar_todas(self) -> List[Vulnerabilidade]:
        """Retorna todas as vulnerabilidades, ordenadas por ID."""
        linhas = self._conexao.execute(
            "SELECT * FROM vulnerabilidades ORDER BY id"
        ).fetchall()
        return [self._converter_linha_em_vulnerabilidade(linha) for linha in linhas]

    def listar_por_equipamento(self, equipamento_id: int) -> List[Vulnerabilidade]:
        """Retorna as vulnerabilidades que afetam um equipamento, ordenadas por ID."""
        linhas = self._conexao.execute(
            """
            SELECT v.* FROM vulnerabilidades v
            JOIN equipamento_vulnerabilidade ev ON ev.vulnerabilidade_id = v.id
            WHERE ev.equipamento_id = ?
            ORDER BY v.id
            """,
            (equipamento_id,),
        ).fetchall()
        return [self._converter_linha_em_vulnerabilidade(linha) for linha in linhas]

    # --- Associações com equipamentos -----------------------------------

    def associar(self, equipamento_id: int, vulnerabilidade_id: int) -> None:
        """Registra que a vulnerabilidade afeta o equipamento.

        Levanta sqlite3.IntegrityError se o equipamento ou a vulnerabilidade
        não existirem, ou se a associação já estiver cadastrada.
        """
        self._conexao.execute(
            """
            INSERT INTO equipamento_vulnerabilidade (equipamento_id, vulnerabilidade_id)
            VALUES (?, ?)
            """,
            (equipamento_id, vulnerabilidade_id),
        )
        self._conexao.commit()

    def desassociar(self, equipamento_id: int, vulnerabilidade_id: int) -> None:
        """Remove a associação entre a vulnerabilidade e o equipamento."""
        self._conexao.execute(
            """
            DELETE FROM equipamento_vulnerabilidade
            WHERE equipamento_id = ? AND vulnerabilidade_id = ?
            """,
            (equipamento_id, vulnerabilidade_id),
        )
        self._conexao.commit()

    def listar_associacoes(self) -> List[Tuple[int, int]]:
        """Retorna todos os pares (equipamento_id, vulnerabilidade_id)."""
        linhas = self._conexao.execute(
            "SELECT equipamento_id, vulnerabilidade_id FROM equipamento_vulnerabilidade"
        ).fetchall()
        return [
            (linha["equipamento_id"], linha["vulnerabilidade_id"]) for linha in linhas
        ]

    @staticmethod
    def _converter_linha_em_vulnerabilidade(linha: sqlite3.Row) -> Vulnerabilidade:
        return Vulnerabilidade(
            id=linha["id"],
            descricao=linha["descricao"],
            categoria=linha["categoria"],
            nota_cvss=linha["nota_cvss"],
            status=StatusVulnerabilidade[linha["status"]],
        )

"""Repositório responsável pelas operações de CRUD da tabela 'ativos'."""

import sqlite3
from typing import List, Optional

from app.models.ativo import Ativo
from app.models.enums import TipoAtivo
from app.repositories.database import ConexaoBancoDeDados


class AtivoRepository:
    """Traduz operações de CRUD de Ativo em comandos SQL no SQLite."""

    def __init__(self, banco_de_dados: ConexaoBancoDeDados):
        self._conexao = banco_de_dados.conexao

    def inserir(self, ativo: Ativo) -> Ativo:
        """Insere um novo ativo e preenche o 'id' gerado pelo banco."""
        cursor = self._conexao.execute(
            """
            INSERT INTO ativos (nome, responsavel, setor, tipo, descricao)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                ativo.nome,
                ativo.responsavel,
                ativo.setor,
                ativo.tipo.name,
                ativo.descricao,
            ),
        )
        self._conexao.commit()
        ativo.id = cursor.lastrowid
        return ativo

    def atualizar(self, ativo: Ativo) -> None:
        """Grava as alterações de um ativo já existente."""
        self._conexao.execute(
            """
            UPDATE ativos
            SET nome = ?, responsavel = ?, setor = ?, tipo = ?, descricao = ?
            WHERE id = ?
            """,
            (
                ativo.nome,
                ativo.responsavel,
                ativo.setor,
                ativo.tipo.name,
                ativo.descricao,
                ativo.id,
            ),
        )
        self._conexao.commit()

    def excluir(self, ativo_id: int) -> None:
        """Remove um ativo. As vulnerabilidades associadas são removidas
        automaticamente pelo banco (ON DELETE CASCADE)."""
        self._conexao.execute("DELETE FROM ativos WHERE id = ?", (ativo_id,))
        self._conexao.commit()

    def buscar_por_id(self, ativo_id: int) -> Optional[Ativo]:
        """Retorna o ativo com o ID informado, ou None se não existir."""
        linha = self._conexao.execute(
            "SELECT * FROM ativos WHERE id = ?", (ativo_id,)
        ).fetchone()
        return self._converter_linha_em_ativo(linha) if linha else None

    def listar_todos(self) -> List[Ativo]:
        """Retorna todos os ativos, ordenados por ID."""
        linhas = self._conexao.execute("SELECT * FROM ativos ORDER BY id").fetchall()
        return [self._converter_linha_em_ativo(linha) for linha in linhas]

    @staticmethod
    def _converter_linha_em_ativo(linha: sqlite3.Row) -> Ativo:
        return Ativo(
            id=linha["id"],
            nome=linha["nome"],
            responsavel=linha["responsavel"],
            setor=linha["setor"],
            tipo=TipoAtivo[linha["tipo"]],
            descricao=linha["descricao"] or "",
        )

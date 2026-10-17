"""Repositório responsável pelas operações de CRUD da tabela 'equipamentos'."""

import sqlite3
from typing import List, Optional

from app.models.equipamento import TIPOS_DE_EQUIPAMENTO, Equipamento
from app.repositories.database import ConexaoBancoDeDados


class EquipamentoRepository:
    """Traduz operações de CRUD de Equipamento em comandos SQL no SQLite.

    Todas as subclasses de Equipamento ficam na mesma tabela. A coluna
    'classe' guarda o nome da subclasse (ex.: 'Servidor'), usado para
    recriar o objeto com a classe certa ao ler o registro do banco.
    """

    def __init__(self, banco_de_dados: ConexaoBancoDeDados):
        self._conexao = banco_de_dados.conexao

    def inserir(self, equipamento: Equipamento) -> Equipamento:
        """Insere um novo equipamento e preenche o 'id' gerado pelo banco."""
        cursor = self._conexao.execute(
            """
            INSERT INTO equipamentos (nome, responsavel, setor, classe, descricao)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                equipamento.nome,
                equipamento.responsavel,
                equipamento.setor,
                type(equipamento).__name__,
                equipamento.descricao,
            ),
        )
        self._conexao.commit()
        equipamento.id = cursor.lastrowid
        return equipamento

    def atualizar(self, equipamento: Equipamento) -> None:
        """Grava as alterações de um equipamento já existente."""
        self._conexao.execute(
            """
            UPDATE equipamentos
            SET nome = ?, responsavel = ?, setor = ?, classe = ?, descricao = ?
            WHERE id = ?
            """,
            (
                equipamento.nome,
                equipamento.responsavel,
                equipamento.setor,
                type(equipamento).__name__,
                equipamento.descricao,
                equipamento.id,
            ),
        )
        self._conexao.commit()

    def excluir(self, equipamento_id: int) -> None:
        """Remove um equipamento. As vulnerabilidades associadas são removidas
        automaticamente pelo banco (ON DELETE CASCADE)."""
        self._conexao.execute(
            "DELETE FROM equipamentos WHERE id = ?", (equipamento_id,)
        )
        self._conexao.commit()

    def buscar_por_id(self, equipamento_id: int) -> Optional[Equipamento]:
        """Retorna o equipamento com o ID informado, ou None se não existir."""
        linha = self._conexao.execute(
            "SELECT * FROM equipamentos WHERE id = ?", (equipamento_id,)
        ).fetchone()
        return self._converter_linha_em_equipamento(linha) if linha else None

    def listar_todos(self) -> List[Equipamento]:
        """Retorna todos os equipamentos, ordenados por ID."""
        linhas = self._conexao.execute(
            "SELECT * FROM equipamentos ORDER BY id"
        ).fetchall()
        return [self._converter_linha_em_equipamento(linha) for linha in linhas]

    @staticmethod
    def _converter_linha_em_equipamento(linha: sqlite3.Row) -> Equipamento:
        classe = TIPOS_DE_EQUIPAMENTO[linha["classe"]]
        return classe(
            id=linha["id"],
            nome=linha["nome"],
            responsavel=linha["responsavel"],
            setor=linha["setor"],
            descricao=linha["descricao"] or "",
        )

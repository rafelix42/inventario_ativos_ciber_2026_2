"""Configuração e criação da conexão com o banco de dados SQLite."""

import sqlite3
from pathlib import Path

# Caminho para o arquivo do banco de dados: pasta 'data' na raiz do projeto.
CAMINHO_PADRAO_DO_BANCO = (
    Path(__file__).resolve().parent.parent.parent / "data" / "inventario.db"
)


class ConexaoBancoDeDados:
    """Abre a conexão SQLite e garante que as tabelas necessárias existam.

    Centralizar essa lógica em uma única classe evita que cada repositório
    precise se preocupar com a criação das tabelas ou com detalhes de
    configuração do SQLite (como habilitar chaves estrangeiras).
    """

    def __init__(self, caminho_do_banco: Path = CAMINHO_PADRAO_DO_BANCO):
        caminho_do_banco.parent.mkdir(parents=True, exist_ok=True)

        self._conexao = sqlite3.connect(caminho_do_banco)
        self._conexao.row_factory = sqlite3.Row
        self._conexao.execute("PRAGMA foreign_keys = ON")

        self._criar_tabelas_se_nao_existirem()

    @property
    def conexao(self) -> sqlite3.Connection:
        """Retorna a conexão ativa, usada pelos repositórios para consultas."""
        return self._conexao

    def _criar_tabelas_se_nao_existirem(self) -> None:
        self._conexao.execute("""
            CREATE TABLE IF NOT EXISTS equipamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                responsavel TEXT NOT NULL,
                setor TEXT NOT NULL,
                classe TEXT NOT NULL,
                descricao TEXT
            )
            """)
        self._conexao.execute("""
            CREATE TABLE IF NOT EXISTS vulnerabilidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipamento_id INTEGER NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT NOT NULL,
                nota_cvss REAL NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (equipamento_id) REFERENCES equipamentos (id)
                    ON DELETE CASCADE
            )
            """)
        self._conexao.commit()

    def fechar(self) -> None:
        """Encerra a conexão com o banco de dados."""
        self._conexao.close()

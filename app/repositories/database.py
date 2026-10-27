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
        precisa_migrar = self._vulnerabilidades_estao_no_formato_antigo()
        if precisa_migrar:
            self._conexao.execute(
                "ALTER TABLE vulnerabilidades RENAME TO vulnerabilidades_antigas"
            )

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
                descricao TEXT NOT NULL,
                categoria TEXT NOT NULL,
                nota_cvss REAL NOT NULL,
                status TEXT NOT NULL
            )
            """)
        # Tabela de associação: uma vulnerabilidade pode afetar vários
        # equipamentos, e um equipamento pode ter várias vulnerabilidades.
        self._conexao.execute("""
            CREATE TABLE IF NOT EXISTS equipamento_vulnerabilidade (
                equipamento_id INTEGER NOT NULL,
                vulnerabilidade_id INTEGER NOT NULL,
                PRIMARY KEY (equipamento_id, vulnerabilidade_id),
                FOREIGN KEY (equipamento_id) REFERENCES equipamentos (id)
                    ON DELETE CASCADE,
                FOREIGN KEY (vulnerabilidade_id) REFERENCES vulnerabilidades (id)
                    ON DELETE CASCADE
            )
            """)
        # Ao excluir um equipamento, as vulnerabilidades que só afetavam ele
        # são excluídas junto. As que também afetam outros equipamentos (ou
        # que nunca foram associadas a ele) continuam cadastradas.
        self._conexao.execute("""
            CREATE TRIGGER IF NOT EXISTS excluir_vulnerabilidades_orfas
            BEFORE DELETE ON equipamentos
            BEGIN
                DELETE FROM vulnerabilidades
                WHERE id IN (
                    SELECT vulnerabilidade_id FROM equipamento_vulnerabilidade
                    WHERE equipamento_id = OLD.id
                )
                AND id NOT IN (
                    SELECT vulnerabilidade_id FROM equipamento_vulnerabilidade
                    WHERE equipamento_id <> OLD.id
                );
            END
            """)

        if precisa_migrar:
            self._migrar_vulnerabilidades_do_formato_antigo()
        self._conexao.commit()

    def _vulnerabilidades_estao_no_formato_antigo(self) -> bool:
        """Indica se o banco ainda usa o formato em que cada vulnerabilidade
        pertencia a um único equipamento (coluna 'equipamento_id')."""
        colunas = {
            linha["name"]
            for linha in self._conexao.execute("PRAGMA table_info(vulnerabilidades)")
        }
        return "equipamento_id" in colunas

    def _migrar_vulnerabilidades_do_formato_antigo(self) -> None:
        """Copia as vulnerabilidades do formato antigo para o novo, mantendo os
        mesmos ids, e transforma o 'equipamento_id' de cada uma em uma linha
        da tabela de associação."""
        self._conexao.execute("""
            INSERT INTO vulnerabilidades (id, descricao, categoria, nota_cvss, status)
            SELECT id, descricao, categoria, nota_cvss, status
            FROM vulnerabilidades_antigas
            """)
        self._conexao.execute("""
            INSERT INTO equipamento_vulnerabilidade (equipamento_id, vulnerabilidade_id)
            SELECT equipamento_id, id FROM vulnerabilidades_antigas
            """)
        self._conexao.execute("DROP TABLE vulnerabilidades_antigas")

    def fechar(self) -> None:
        """Encerra a conexão com o banco de dados."""
        self._conexao.close()

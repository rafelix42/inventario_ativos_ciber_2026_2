"""Testes da migração do banco de dados do formato antigo (cada
vulnerabilidade pertencia a um único equipamento) para o formato com
associações entre vulnerabilidades e equipamentos."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.repositories.database import ConexaoBancoDeDados


class TestMigracaoDoFormatoAntigo(unittest.TestCase):
    """Abre um banco no formato antigo e confere se os dados são preservados."""

    def setUp(self) -> None:
        # pylint: disable-next=consider-using-with
        self._diretorio_temporario = tempfile.TemporaryDirectory()
        self.caminho = Path(self._diretorio_temporario.name) / "antigo.db"

        conexao = sqlite3.connect(self.caminho)
        conexao.executescript("""
            CREATE TABLE equipamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT, responsavel TEXT, setor TEXT, classe TEXT, descricao TEXT
            );
            CREATE TABLE vulnerabilidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipamento_id INTEGER NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT NOT NULL,
                nota_cvss REAL NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (equipamento_id) REFERENCES equipamentos (id)
                    ON DELETE CASCADE
            );
            INSERT INTO equipamentos (nome, responsavel, setor, classe)
                VALUES ('Servidor A', 'Fulano', 'TI', 'Servidor'),
                       ('Servidor B', 'Fulano', 'TI', 'Servidor');
            INSERT INTO vulnerabilidades
                (equipamento_id, descricao, categoria, nota_cvss, status)
                VALUES (1, 'Senha fraca', 'Autenticação', 7.5, 'ABERTA'),
                       (2, 'Porta aberta', 'Rede', 5.0, 'CORRIGIDA');
            """)
        conexao.close()

    def tearDown(self) -> None:
        self._diretorio_temporario.cleanup()

    def test_migracao_preserva_vulnerabilidades_e_cria_associacoes(self):
        banco = ConexaoBancoDeDados(self.caminho)
        try:
            colunas = [
                linha["name"]
                for linha in banco.conexao.execute(
                    "PRAGMA table_info(vulnerabilidades)"
                )
            ]
            vulnerabilidades = banco.conexao.execute(
                "SELECT id, descricao FROM vulnerabilidades ORDER BY id"
            ).fetchall()
            associacoes = banco.conexao.execute(
                "SELECT equipamento_id, vulnerabilidade_id "
                "FROM equipamento_vulnerabilidade ORDER BY vulnerabilidade_id"
            ).fetchall()
        finally:
            banco.fechar()

        self.assertNotIn("equipamento_id", colunas)
        self.assertEqual(
            [tuple(linha) for linha in vulnerabilidades],
            [(1, "Senha fraca"), (2, "Porta aberta")],
        )
        self.assertEqual([tuple(linha) for linha in associacoes], [(1, 1), (2, 2)])

    def test_banco_migrado_pode_ser_reaberto(self):
        ConexaoBancoDeDados(self.caminho).fechar()

        banco = ConexaoBancoDeDados(self.caminho)
        try:
            total = banco.conexao.execute(
                "SELECT COUNT(*) FROM vulnerabilidades"
            ).fetchone()[0]
        finally:
            banco.fechar()

        self.assertEqual(total, 2)

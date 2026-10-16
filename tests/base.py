"""Classe base para testes que precisam de um banco de dados SQLite isolado.

Cada teste que herda de 'CasoDeTesteComBancoTemporario' recebe um banco de
dados novo, criado em um diretório temporário. O banco é apagado
automaticamente ao final do teste, garantindo que os testes não interfiram
uns nos outros nem no banco de dados real da aplicação (data/inventario.db).
"""

import tempfile
import unittest
from pathlib import Path

from app.repositories.database import ConexaoBancoDeDados


class CasoDeTesteComBancoTemporario(unittest.TestCase):
    """Cria e destrói um banco SQLite temporário para cada método de teste."""

    def setUp(self) -> None:
        # Não dá para usar 'with' aqui: o diretório precisa existir até o
        # tearDown, onde é removido explicitamente.
        # pylint: disable-next=consider-using-with
        self._diretorio_temporario = tempfile.TemporaryDirectory()
        caminho_do_banco_de_teste = Path(self._diretorio_temporario.name) / "teste.db"
        self.banco = ConexaoBancoDeDados(caminho_do_banco_de_teste)

    def tearDown(self) -> None:
        self.banco.fechar()
        self._diretorio_temporario.cleanup()

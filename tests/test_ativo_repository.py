"""Testes da camada de persistência (SQLite) para o CRUD de ativos."""

from app.models.ativo import Ativo
from app.models.enums import TipoAtivo
from app.repositories.ativo_repository import AtivoRepository
from tests.base import CasoDeTesteComBancoTemporario


class TestAtivoRepository(CasoDeTesteComBancoTemporario):
    """Testes de persistência de ativos no SQLite."""

    def setUp(self) -> None:
        super().setUp()
        self.repositorio = AtivoRepository(self.banco)

    def _criar_ativo_de_exemplo(self, nome: str = "Servidor-01") -> Ativo:
        ativo = Ativo(
            nome=nome,
            responsavel="Fulano de Tal",
            setor="TI",
            tipo=TipoAtivo.SERVIDOR,
            descricao="Ativo criado para teste automatizado.",
        )
        return self.repositorio.inserir(ativo)

    # --- Create -----------------------------------------------------

    def test_inserir_gera_id_autoincrementado(self):
        ativo = self._criar_ativo_de_exemplo()

        self.assertIsNotNone(ativo.id)
        self.assertEqual(ativo.id, 1)

    # --- Read ---------------------------------------------------------

    def test_buscar_por_id_retorna_ativo_inserido(self):
        ativo_inserido = self._criar_ativo_de_exemplo()

        ativo_encontrado = self.repositorio.buscar_por_id(ativo_inserido.id)

        self.assertIsNotNone(ativo_encontrado)
        self.assertEqual(ativo_encontrado.nome, "Servidor-01")
        self.assertEqual(ativo_encontrado.tipo, TipoAtivo.SERVIDOR)

    def test_buscar_por_id_inexistente_retorna_none(self):
        self.assertIsNone(self.repositorio.buscar_por_id(999))

    def test_listar_todos_retorna_ativos_ordenados_por_id(self):
        primeiro_ativo = self._criar_ativo_de_exemplo("Servidor-01")
        segundo_ativo = self._criar_ativo_de_exemplo("Servidor-02")

        ativos_cadastrados = self.repositorio.listar_todos()

        self.assertEqual(
            [ativo.id for ativo in ativos_cadastrados],
            [primeiro_ativo.id, segundo_ativo.id],
        )

    # --- Update ---------------------------------------------------------

    def test_atualizar_persiste_alteracoes_no_banco(self):
        ativo = self._criar_ativo_de_exemplo()
        ativo.responsavel = "Ciclana"
        ativo.setor = "Financeiro"
        ativo.tipo = TipoAtivo.FIREWALL

        self.repositorio.atualizar(ativo)
        ativo_atualizado = self.repositorio.buscar_por_id(ativo.id)

        self.assertEqual(ativo_atualizado.responsavel, "Ciclana")
        self.assertEqual(ativo_atualizado.setor, "Financeiro")
        self.assertEqual(ativo_atualizado.tipo, TipoAtivo.FIREWALL)

    # --- Delete ---------------------------------------------------------

    def test_excluir_remove_ativo_do_banco(self):
        ativo = self._criar_ativo_de_exemplo()

        self.repositorio.excluir(ativo.id)

        self.assertIsNone(self.repositorio.buscar_por_id(ativo.id))

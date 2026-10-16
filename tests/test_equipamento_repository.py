"""Testes da camada de persistência (SQLite) para o CRUD de equipamentos."""

from app.models.equipamento import Equipamento, Firewall, Servidor
from app.repositories.equipamento_repository import EquipamentoRepository
from tests.base import CasoDeTesteComBancoTemporario


class TestEquipamentoRepository(CasoDeTesteComBancoTemporario):
    """Testes de persistência de equipamentos no SQLite."""

    def setUp(self) -> None:
        super().setUp()
        self.repositorio = EquipamentoRepository(self.banco)

    def _criar_equipamento_de_exemplo(self, nome: str = "Servidor-01") -> Equipamento:
        equipamento = Servidor(
            nome=nome,
            responsavel="Fulano de Tal",
            setor="TI",
            descricao="Equipamento criado para teste automatizado.",
        )
        return self.repositorio.inserir(equipamento)

    # --- Create -----------------------------------------------------

    def test_inserir_gera_id_autoincrementado(self):
        equipamento = self._criar_equipamento_de_exemplo()

        self.assertIsNotNone(equipamento.id)
        self.assertEqual(equipamento.id, 1)

    # --- Read ---------------------------------------------------------

    def test_buscar_por_id_retorna_equipamento_inserido(self):
        equipamento_inserido = self._criar_equipamento_de_exemplo()

        equipamento_encontrado = self.repositorio.buscar_por_id(equipamento_inserido.id)

        self.assertIsNotNone(equipamento_encontrado)
        self.assertEqual(equipamento_encontrado.nome, "Servidor-01")
        self.assertIsInstance(equipamento_encontrado, Servidor)

    def test_buscar_por_id_inexistente_retorna_none(self):
        self.assertIsNone(self.repositorio.buscar_por_id(999))

    def test_listar_todos_retorna_equipamentos_ordenados_por_id(self):
        primeiro_equipamento = self._criar_equipamento_de_exemplo("Servidor-01")
        segundo_equipamento = self._criar_equipamento_de_exemplo("Servidor-02")

        equipamentos_cadastrados = self.repositorio.listar_todos()

        self.assertEqual(
            [equipamento.id for equipamento in equipamentos_cadastrados],
            [primeiro_equipamento.id, segundo_equipamento.id],
        )

    # --- Update ---------------------------------------------------------

    def test_atualizar_persiste_alteracoes_no_banco(self):
        equipamento = self._criar_equipamento_de_exemplo()
        equipamento.responsavel = "Ciclana"
        equipamento.setor = "Financeiro"

        self.repositorio.atualizar(equipamento)
        equipamento_atualizado = self.repositorio.buscar_por_id(equipamento.id)

        self.assertEqual(equipamento_atualizado.responsavel, "Ciclana")
        self.assertEqual(equipamento_atualizado.setor, "Financeiro")

    def test_atualizar_com_outra_subclasse_troca_a_classe_gravada(self):
        equipamento = self._criar_equipamento_de_exemplo()
        como_firewall = Firewall(
            id=equipamento.id,
            nome=equipamento.nome,
            responsavel=equipamento.responsavel,
            setor=equipamento.setor,
        )

        self.repositorio.atualizar(como_firewall)

        self.assertIsInstance(self.repositorio.buscar_por_id(equipamento.id), Firewall)

    # --- Delete ---------------------------------------------------------

    def test_excluir_remove_equipamento_do_banco(self):
        equipamento = self._criar_equipamento_de_exemplo()

        self.repositorio.excluir(equipamento.id)

        self.assertIsNone(self.repositorio.buscar_por_id(equipamento.id))

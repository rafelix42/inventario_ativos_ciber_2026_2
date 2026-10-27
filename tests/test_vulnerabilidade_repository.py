"""Testes da camada de persistência (SQLite) para o CRUD de vulnerabilidades
e para as associações entre vulnerabilidades e equipamentos."""

import sqlite3

from app.models.enums import Severidade, StatusVulnerabilidade
from app.models.equipamento import Servidor
from app.models.vulnerabilidade import Vulnerabilidade
from app.repositories.equipamento_repository import EquipamentoRepository
from app.repositories.vulnerabilidade_repository import VulnerabilidadeRepository
from tests.base import CasoDeTesteComBancoTemporario


class TestVulnerabilidadeRepository(CasoDeTesteComBancoTemporario):
    """Testes de persistência de vulnerabilidades no SQLite."""

    def setUp(self) -> None:
        super().setUp()
        self.repositorio_de_equipamentos = EquipamentoRepository(self.banco)
        self.repositorio = VulnerabilidadeRepository(self.banco)
        self.equipamento = self._criar_equipamento_de_exemplo("Servidor-01")
        self.outro_equipamento = self._criar_equipamento_de_exemplo("Servidor-02")

    def _criar_equipamento_de_exemplo(self, nome: str) -> Servidor:
        return self.repositorio_de_equipamentos.inserir(
            Servidor(nome=nome, responsavel="Fulano de Tal", setor="TI")
        )

    def _criar_vulnerabilidade_de_exemplo(
        self, descricao: str = "Senha fraca", nota_cvss: float = 7.5
    ) -> Vulnerabilidade:
        vulnerabilidade = Vulnerabilidade(
            descricao=descricao,
            categoria="Autenticação",
            nota_cvss=nota_cvss,
            status=StatusVulnerabilidade.ABERTA,
        )
        return self.repositorio.inserir(vulnerabilidade)

    # --- Create -----------------------------------------------------

    def test_inserir_gera_id_autoincrementado(self):
        vulnerabilidade = self._criar_vulnerabilidade_de_exemplo()

        self.assertIsNotNone(vulnerabilidade.id)

    # --- Read ---------------------------------------------------------

    def test_buscar_por_id_retorna_vulnerabilidade_inserida(self):
        vulnerabilidade = self._criar_vulnerabilidade_de_exemplo(nota_cvss=7.5)

        encontrada = self.repositorio.buscar_por_id(vulnerabilidade.id)

        self.assertEqual(encontrada.descricao, "Senha fraca")
        self.assertEqual(encontrada.nota_cvss, 7.5)
        self.assertEqual(encontrada.severidade, Severidade.ALTA)
        self.assertEqual(encontrada.status, StatusVulnerabilidade.ABERTA)

    def test_buscar_por_id_inexistente_retorna_none(self):
        self.assertIsNone(self.repositorio.buscar_por_id(999))

    def test_listar_todas_inclui_vulnerabilidades_sem_equipamento(self):
        vulnerabilidade = self._criar_vulnerabilidade_de_exemplo()

        self.assertEqual(self.repositorio.listar_todas(), [vulnerabilidade])

    # --- Update ---------------------------------------------------------

    def test_atualizar_persiste_alteracoes_no_banco(self):
        vulnerabilidade = self._criar_vulnerabilidade_de_exemplo(nota_cvss=7.5)
        vulnerabilidade.status = StatusVulnerabilidade.CORRIGIDA
        vulnerabilidade.nota_cvss = 2.0

        self.repositorio.atualizar(vulnerabilidade)
        vulnerabilidade_atualizada = self.repositorio.buscar_por_id(vulnerabilidade.id)

        self.assertEqual(
            vulnerabilidade_atualizada.status, StatusVulnerabilidade.CORRIGIDA
        )
        self.assertEqual(vulnerabilidade_atualizada.nota_cvss, 2.0)
        self.assertEqual(vulnerabilidade_atualizada.severidade, Severidade.BAIXA)

    # --- Delete ---------------------------------------------------------

    def test_excluir_remove_vulnerabilidade_e_suas_associacoes(self):
        vulnerabilidade = self._criar_vulnerabilidade_de_exemplo()
        self.repositorio.associar(self.equipamento.id, vulnerabilidade.id)

        self.repositorio.excluir(vulnerabilidade.id)

        self.assertIsNone(self.repositorio.buscar_por_id(vulnerabilidade.id))
        self.assertEqual(self.repositorio.listar_associacoes(), [])

    # --- Associações -----------------------------------------------

    def test_listar_por_equipamento_retorna_apenas_vulnerabilidades_associadas(self):
        do_primeiro = self._criar_vulnerabilidade_de_exemplo("Do primeiro")
        do_segundo = self._criar_vulnerabilidade_de_exemplo("Do segundo")
        self.repositorio.associar(self.equipamento.id, do_primeiro.id)
        self.repositorio.associar(self.outro_equipamento.id, do_segundo.id)

        self.assertEqual(
            self.repositorio.listar_por_equipamento(self.equipamento.id), [do_primeiro]
        )

    def test_listar_por_equipamento_sem_vulnerabilidades_retorna_lista_vazia(self):
        self.assertEqual(
            self.repositorio.listar_por_equipamento(self.equipamento.id), []
        )

    def test_mesma_vulnerabilidade_pode_ser_associada_a_varios_equipamentos(self):
        vulnerabilidade = self._criar_vulnerabilidade_de_exemplo()

        self.repositorio.associar(self.equipamento.id, vulnerabilidade.id)
        self.repositorio.associar(self.outro_equipamento.id, vulnerabilidade.id)

        self.assertEqual(
            sorted(self.repositorio.listar_associacoes()),
            [
                (self.equipamento.id, vulnerabilidade.id),
                (self.outro_equipamento.id, vulnerabilidade.id),
            ],
        )

    def test_associacao_duplicada_levanta_integrity_error(self):
        vulnerabilidade = self._criar_vulnerabilidade_de_exemplo()
        self.repositorio.associar(self.equipamento.id, vulnerabilidade.id)

        with self.assertRaises(sqlite3.IntegrityError):
            self.repositorio.associar(self.equipamento.id, vulnerabilidade.id)

    def test_desassociar_mantem_a_vulnerabilidade(self):
        vulnerabilidade = self._criar_vulnerabilidade_de_exemplo()
        self.repositorio.associar(self.equipamento.id, vulnerabilidade.id)

        self.repositorio.desassociar(self.equipamento.id, vulnerabilidade.id)

        self.assertEqual(self.repositorio.listar_associacoes(), [])
        self.assertIsNotNone(self.repositorio.buscar_por_id(vulnerabilidade.id))

    # --- Exclusão de equipamento (trigger do banco) ---------------

    def test_excluir_equipamento_exclui_apenas_vulnerabilidades_exclusivas(self):
        exclusiva = self._criar_vulnerabilidade_de_exemplo("Exclusiva")
        compartilhada = self._criar_vulnerabilidade_de_exemplo("Compartilhada")
        avulsa = self._criar_vulnerabilidade_de_exemplo("Sem equipamento")
        self.repositorio.associar(self.equipamento.id, exclusiva.id)
        self.repositorio.associar(self.equipamento.id, compartilhada.id)
        self.repositorio.associar(self.outro_equipamento.id, compartilhada.id)

        self.repositorio_de_equipamentos.excluir(self.equipamento.id)

        self.assertIsNone(self.repositorio.buscar_por_id(exclusiva.id))
        self.assertEqual(self.repositorio.listar_todas(), [compartilhada, avulsa])
        self.assertEqual(
            self.repositorio.listar_associacoes(),
            [(self.outro_equipamento.id, compartilhada.id)],
        )

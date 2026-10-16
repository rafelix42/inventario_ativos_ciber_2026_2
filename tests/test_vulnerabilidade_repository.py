"""Testes da camada de persistência (SQLite) para o CRUD de vulnerabilidades."""

from typing import Optional

from app.models.ativo import Ativo
from app.models.enums import Severidade, StatusVulnerabilidade, TipoAtivo
from app.models.vulnerabilidade import Vulnerabilidade
from app.repositories.ativo_repository import AtivoRepository
from app.repositories.vulnerabilidade_repository import VulnerabilidadeRepository
from tests.base import CasoDeTesteComBancoTemporario


class TestVulnerabilidadeRepository(CasoDeTesteComBancoTemporario):
    """Testes de persistência de vulnerabilidades no SQLite."""

    def setUp(self) -> None:
        super().setUp()
        self.repositorio_de_ativos = AtivoRepository(self.banco)
        self.repositorio = VulnerabilidadeRepository(self.banco)
        self.ativo = self.repositorio_de_ativos.inserir(
            Ativo(
                nome="Servidor-01",
                responsavel="Fulano de Tal",
                setor="TI",
                tipo=TipoAtivo.SERVIDOR,
            )
        )

    def _criar_vulnerabilidade_de_exemplo(
        self,
        descricao: str = "Senha fraca",
        ativo_id: Optional[int] = None,
        nota_cvss: float = 7.5,
    ) -> Vulnerabilidade:
        vulnerabilidade = Vulnerabilidade(
            ativo_id=ativo_id or self.ativo.id,
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

    def test_listar_por_ativo_retorna_apenas_vulnerabilidades_daquele_ativo(self):
        outro_ativo = self.repositorio_de_ativos.inserir(
            Ativo(
                nome="Servidor-02",
                responsavel="Fulano de Tal",
                setor="TI",
                tipo=TipoAtivo.SERVIDOR,
            )
        )
        self._criar_vulnerabilidade_de_exemplo("Vulnerabilidade do Servidor-01")
        self._criar_vulnerabilidade_de_exemplo(
            "Vulnerabilidade do Servidor-02", ativo_id=outro_ativo.id
        )

        vulnerabilidades_do_primeiro_ativo = self.repositorio.listar_por_ativo(
            self.ativo.id
        )

        self.assertEqual(len(vulnerabilidades_do_primeiro_ativo), 1)
        self.assertEqual(
            vulnerabilidades_do_primeiro_ativo[0].descricao,
            "Vulnerabilidade do Servidor-01",
        )

    def test_listar_por_ativo_sem_vulnerabilidades_retorna_lista_vazia(self):
        self.assertEqual(self.repositorio.listar_por_ativo(self.ativo.id), [])

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

    def test_excluir_remove_vulnerabilidade_do_banco(self):
        vulnerabilidade = self._criar_vulnerabilidade_de_exemplo()

        self.repositorio.excluir(vulnerabilidade.id)

        self.assertIsNone(self.repositorio.buscar_por_id(vulnerabilidade.id))

    def test_excluir_ativo_remove_vulnerabilidades_em_cascata(self):
        """Cobre o RF07: excluir um ativo remove também suas vulnerabilidades."""
        self._criar_vulnerabilidade_de_exemplo()

        self.repositorio_de_ativos.excluir(self.ativo.id)

        self.assertEqual(self.repositorio.listar_por_ativo(self.ativo.id), [])

"""Testes da camada de regras de negócio (VulnerabilidadeService):
CRUD, validações da nota CVSS e exclusão em cascata."""

from app.exceptions import ErroDeValidacao, VulnerabilidadeNaoEncontradaError
from app.models.enums import Severidade, StatusVulnerabilidade, TipoAtivo
from app.repositories.ativo_repository import AtivoRepository
from app.repositories.vulnerabilidade_repository import VulnerabilidadeRepository
from app.services.ativo_service import AtivoService
from app.services.vulnerabilidade_service import VulnerabilidadeService
from tests.base import CasoDeTesteComBancoTemporario

NOME_DO_LOGGER = "app.services.vulnerabilidade_service"


class TestVulnerabilidadeService(CasoDeTesteComBancoTemporario):
    """Testes das regras de negócio de vulnerabilidades."""

    def setUp(self) -> None:
        super().setUp()
        self.servico_de_ativos = AtivoService(AtivoRepository(self.banco))
        self.servico = VulnerabilidadeService(VulnerabilidadeRepository(self.banco))
        self.ativo = self.servico_de_ativos.cadastrar(
            "Servidor-01", "Fulano", "TI", TipoAtivo.SERVIDOR
        )

    # --- Read (RF09: informar explicitamente quando não houver) -------

    def test_ativo_sem_vulnerabilidades_retorna_lista_vazia(self):
        self.assertEqual(self.servico.listar_por_ativo(self.ativo.id), [])

    def test_listar_por_ativo_retorna_apenas_vulnerabilidades_daquele_ativo(self):
        outro_ativo = self.servico_de_ativos.cadastrar(
            "Servidor-02", "Fulano", "TI", TipoAtivo.SERVIDOR
        )
        self.servico.cadastrar(
            self.ativo.id, "Vuln A", "Rede", 2.0, StatusVulnerabilidade.ABERTA
        )
        self.servico.cadastrar(
            outro_ativo.id, "Vuln B", "Rede", 2.0, StatusVulnerabilidade.ABERTA
        )

        vulnerabilidades_do_primeiro_ativo = self.servico.listar_por_ativo(
            self.ativo.id
        )

        self.assertEqual(len(vulnerabilidades_do_primeiro_ativo), 1)
        self.assertEqual(vulnerabilidades_do_primeiro_ativo[0].descricao, "Vuln A")

    # --- Create -----------------------------------------------------

    def test_cadastrar_com_dados_validos_retorna_vulnerabilidade_persistida(self):
        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            vulnerabilidade = self.servico.cadastrar(
                ativo_id=self.ativo.id,
                descricao="Senha fraca",
                categoria="Autenticação",
                nota_cvss=7.5,
                status=StatusVulnerabilidade.ABERTA,
            )

        self.assertIsNotNone(vulnerabilidade.id)
        self.assertEqual(vulnerabilidade.nota_cvss, 7.5)
        self.assertEqual(
            self.servico.listar_por_ativo(self.ativo.id), [vulnerabilidade]
        )

    def test_severidade_e_calculada_automaticamente_a_partir_da_nota_cvss(self):
        vulnerabilidade = self.servico.cadastrar(
            self.ativo.id, "Falha crítica", "Rede", 9.8, StatusVulnerabilidade.ABERTA
        )

        self.assertEqual(vulnerabilidade.severidade, Severidade.CRITICA)

    def test_cadastrar_com_descricao_vazia_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                self.ativo.id, "", "Autenticação", 2.0, StatusVulnerabilidade.ABERTA
            )

    def test_cadastrar_com_categoria_vazia_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                self.ativo.id, "Senha fraca", "", 2.0, StatusVulnerabilidade.ABERTA
            )

    def test_cadastrar_com_nota_cvss_nao_numerica_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                self.ativo.id, "desc", "cat", "alta", StatusVulnerabilidade.ABERTA
            )

    def test_cadastrar_com_nota_cvss_negativa_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                self.ativo.id, "desc", "cat", -0.1, StatusVulnerabilidade.ABERTA
            )

    def test_cadastrar_com_nota_cvss_acima_de_dez_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                self.ativo.id, "desc", "cat", 10.1, StatusVulnerabilidade.ABERTA
            )

    def test_cadastrar_com_nota_cvss_nos_limites_validos_e_aceito(self):
        self.servico.cadastrar(
            self.ativo.id, "nota mínima", "cat", 0.0, StatusVulnerabilidade.ABERTA
        )
        self.servico.cadastrar(
            self.ativo.id, "nota máxima", "cat", 10.0, StatusVulnerabilidade.ABERTA
        )

        self.assertEqual(len(self.servico.listar_por_ativo(self.ativo.id)), 2)

    def test_cadastrar_com_status_invalido_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(self.ativo.id, "desc", "cat", 2.0, "aberta")

    # --- Update ---------------------------------------------------------

    def test_atualizar_altera_nota_cvss_e_status(self):
        vulnerabilidade = self.servico.cadastrar(
            self.ativo.id,
            "Senha fraca",
            "Autenticação",
            8.0,
            StatusVulnerabilidade.ABERTA,
        )

        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            vulnerabilidade_atualizada = self.servico.atualizar(
                vulnerabilidade_id=vulnerabilidade.id,
                descricao="Senha fraca",
                categoria="Autenticação",
                nota_cvss=2.0,
                status=StatusVulnerabilidade.CORRIGIDA,
            )

        self.assertEqual(vulnerabilidade_atualizada.nota_cvss, 2.0)
        self.assertEqual(vulnerabilidade_atualizada.severidade, Severidade.BAIXA)
        self.assertEqual(
            vulnerabilidade_atualizada.status, StatusVulnerabilidade.CORRIGIDA
        )

    def test_atualizar_vulnerabilidade_inexistente_levanta_erro(self):
        with self.assertRaises(VulnerabilidadeNaoEncontradaError):
            self.servico.atualizar(
                999, "desc", "cat", 2.0, StatusVulnerabilidade.ABERTA
            )

    def test_atualizar_com_nota_cvss_fora_da_faixa_levanta_erro_de_validacao(self):
        vulnerabilidade = self.servico.cadastrar(
            self.ativo.id,
            "Senha fraca",
            "Autenticação",
            8.0,
            StatusVulnerabilidade.ABERTA,
        )

        with self.assertRaises(ErroDeValidacao):
            self.servico.atualizar(
                vulnerabilidade.id,
                "Senha fraca",
                "Autenticação",
                11.0,
                StatusVulnerabilidade.ABERTA,
            )

    # --- Delete ---------------------------------------------------------

    def test_excluir_remove_vulnerabilidade_do_cache_e_do_banco(self):
        vulnerabilidade = self.servico.cadastrar(
            self.ativo.id,
            "Senha fraca",
            "Autenticação",
            8.0,
            StatusVulnerabilidade.ABERTA,
        )

        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            self.servico.excluir(vulnerabilidade.id)

        self.assertEqual(self.servico.listar_por_ativo(self.ativo.id), [])
        with self.assertRaises(VulnerabilidadeNaoEncontradaError):
            self.servico.excluir(vulnerabilidade.id)

    def test_excluir_vulnerabilidade_inexistente_levanta_erro(self):
        with self.assertRaises(VulnerabilidadeNaoEncontradaError):
            self.servico.excluir(999)

    # --- Exclusão em cascata (RF07) ------------------------------------

    def test_esquecer_vulnerabilidades_do_ativo_limpa_o_cache_apos_exclusao_do_ativo(
        self,
    ):
        self.servico.cadastrar(
            self.ativo.id,
            "Senha fraca",
            "Autenticação",
            8.0,
            StatusVulnerabilidade.ABERTA,
        )

        self.servico_de_ativos.excluir(self.ativo.id)
        self.servico.esquecer_vulnerabilidades_do_ativo(self.ativo.id)

        self.assertEqual(self.servico.listar_por_ativo(self.ativo.id), [])

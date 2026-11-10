"""Testes da camada de regras de negócio (VulnerabilidadeService):
CRUD, validações da nota CVSS, associações com equipamentos e exclusão em
cascata das vulnerabilidades exclusivas de um equipamento."""

from app.exceptions import (
    EquipamentoNaoEncontradoError,
    ErroDeValidacao,
    VulnerabilidadeNaoEncontradaError,
)
from app.models.enums import Severidade, StatusVulnerabilidade
from app.models.equipamento import Servidor
from app.repositories.equipamento_repository import EquipamentoRepository
from app.repositories.vulnerabilidade_repository import VulnerabilidadeRepository
from app.services.equipamento_service import EquipamentoService
from app.services.vulnerabilidade_service import VulnerabilidadeService
from tests.base import CasoDeTesteComBancoTemporario

NOME_DO_LOGGER = "app.services.vulnerabilidade_service"


class CasoDeTesteComServicos(CasoDeTesteComBancoTemporario):
    """Monta os dois serviços sobre o banco temporário."""

    def setUp(self) -> None:
        super().setUp()
        self.servico_de_equipamentos = EquipamentoService(
            EquipamentoRepository(self.banco)
        )
        self.servico = VulnerabilidadeService(VulnerabilidadeRepository(self.banco))

    def _cadastrar_equipamento(self, nome: str = "Servidor Um"):
        return self.servico_de_equipamentos.cadastrar(nome, "Fulano", "TI", Servidor)

    def _cadastrar_vulnerabilidade(
        self, descricao: str = "Senha fraca", nota_cvss: float = 8.0
    ):
        return self.servico.cadastrar(
            descricao, "Autenticação", nota_cvss, StatusVulnerabilidade.ABERTA
        )


class TestVulnerabilidadeService(CasoDeTesteComServicos):
    """Testes do CRUD e das validações de vulnerabilidades."""

    # --- Create -----------------------------------------------------

    def test_cadastrar_com_dados_validos_retorna_vulnerabilidade_persistida(self):
        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            vulnerabilidade = self.servico.cadastrar(
                descricao="Senha fraca",
                categoria="Autenticação",
                nota_cvss=7.5,
                status=StatusVulnerabilidade.ABERTA,
            )

        self.assertIsNotNone(vulnerabilidade.id)
        self.assertEqual(vulnerabilidade.nota_cvss, 7.5)
        self.assertEqual(self.servico.listar_todas(), [vulnerabilidade])

    def test_vulnerabilidade_recem_cadastrada_nao_afeta_nenhum_equipamento(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade()

        self.assertEqual(
            self.servico.listar_ids_de_equipamentos_afetados(vulnerabilidade.id), []
        )

    def test_severidade_e_calculada_automaticamente_a_partir_da_nota_cvss(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade(nota_cvss=9.8)

        self.assertEqual(vulnerabilidade.severidade, Severidade.CRITICA)

    def test_cadastrar_com_descricao_vazia_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                "", "Autenticação", 2.0, StatusVulnerabilidade.ABERTA
            )

    def test_cadastrar_com_categoria_vazia_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar("Senha fraca", "", 2.0, StatusVulnerabilidade.ABERTA)

    def test_cadastrar_com_nota_cvss_nao_numerica_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar("desc", "cat", "alta", StatusVulnerabilidade.ABERTA)

    def test_cadastrar_com_nota_cvss_negativa_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar("desc", "cat", -0.1, StatusVulnerabilidade.ABERTA)

    def test_cadastrar_com_nota_cvss_acima_de_dez_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar("desc", "cat", 10.1, StatusVulnerabilidade.ABERTA)

    def test_cadastrar_com_nota_cvss_nos_limites_validos_e_aceito(self):
        self.servico.cadastrar("nota mínima", "cat", 0.0, StatusVulnerabilidade.ABERTA)
        self.servico.cadastrar("nota máxima", "cat", 10.0, StatusVulnerabilidade.ABERTA)

        self.assertEqual(len(self.servico.listar_todas()), 2)

    def test_cadastrar_com_status_invalido_levanta_erro_de_validacao(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar("desc", "cat", 2.0, "aberta")

    # --- Read ---------------------------------------------------------

    def test_buscar_por_id_inexistente_levanta_erro(self):
        with self.assertRaises(VulnerabilidadeNaoEncontradaError):
            self.servico.buscar_por_id(999)

    # --- Update ---------------------------------------------------------

    def test_atualizar_altera_nota_cvss_e_status(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade(nota_cvss=8.0)

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
        vulnerabilidade = self._cadastrar_vulnerabilidade()

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
        vulnerabilidade = self._cadastrar_vulnerabilidade()

        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            self.servico.excluir(vulnerabilidade.id)

        self.assertEqual(self.servico.listar_todas(), [])
        with self.assertRaises(VulnerabilidadeNaoEncontradaError):
            self.servico.excluir(vulnerabilidade.id)

    def test_excluir_vulnerabilidade_inexistente_levanta_erro(self):
        with self.assertRaises(VulnerabilidadeNaoEncontradaError):
            self.servico.excluir(999)


class TestVulnerabilidadeServiceAssociacoes(CasoDeTesteComServicos):
    """Testes das associações entre vulnerabilidades e equipamentos."""

    def setUp(self) -> None:
        super().setUp()
        self.equipamento = self._cadastrar_equipamento("Servidor Um")
        self.outro_equipamento = self._cadastrar_equipamento("Servidor Dois")

    # --- Associar / desassociar ------------------------------------

    def test_equipamento_sem_vulnerabilidades_retorna_lista_vazia(self):
        self.assertEqual(self.servico.listar_por_equipamento(self.equipamento.id), [])

    def test_associar_faz_a_vulnerabilidade_aparecer_no_equipamento(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade()

        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            self.servico.associar(vulnerabilidade.id, self.equipamento.id)

        self.assertEqual(
            self.servico.listar_por_equipamento(self.equipamento.id), [vulnerabilidade]
        )
        self.assertEqual(
            self.servico.listar_por_equipamento(self.outro_equipamento.id), []
        )

    def test_mesma_vulnerabilidade_pode_afetar_varios_equipamentos(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade()

        self.servico.associar(vulnerabilidade.id, self.equipamento.id)
        self.servico.associar(vulnerabilidade.id, self.outro_equipamento.id)

        self.assertEqual(
            self.servico.listar_ids_de_equipamentos_afetados(vulnerabilidade.id),
            [self.equipamento.id, self.outro_equipamento.id],
        )
        self.assertEqual(
            self.servico.listar_por_equipamento(self.outro_equipamento.id),
            [vulnerabilidade],
        )

    def test_associar_duas_vezes_levanta_erro_de_validacao(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade()
        self.servico.associar(vulnerabilidade.id, self.equipamento.id)

        with self.assertRaises(ErroDeValidacao):
            self.servico.associar(vulnerabilidade.id, self.equipamento.id)

    def test_associar_a_equipamento_inexistente_levanta_erro(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade()

        with self.assertRaises(EquipamentoNaoEncontradoError):
            self.servico.associar(vulnerabilidade.id, 999)

    def test_associar_vulnerabilidade_inexistente_levanta_erro(self):
        with self.assertRaises(VulnerabilidadeNaoEncontradaError):
            self.servico.associar(999, self.equipamento.id)

    def test_desassociar_mantem_a_vulnerabilidade_cadastrada(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade()
        self.servico.associar(vulnerabilidade.id, self.equipamento.id)

        self.servico.desassociar(vulnerabilidade.id, self.equipamento.id)

        self.assertEqual(self.servico.listar_por_equipamento(self.equipamento.id), [])
        self.assertEqual(self.servico.listar_todas(), [vulnerabilidade])

    def test_desassociar_sem_associacao_levanta_erro_de_validacao(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade()

        with self.assertRaises(ErroDeValidacao):
            self.servico.desassociar(vulnerabilidade.id, self.equipamento.id)

    def test_excluir_vulnerabilidade_remove_de_todos_os_equipamentos(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade()
        self.servico.associar(vulnerabilidade.id, self.equipamento.id)
        self.servico.associar(vulnerabilidade.id, self.outro_equipamento.id)

        self.servico.excluir(vulnerabilidade.id)

        self.assertEqual(self.servico.listar_por_equipamento(self.equipamento.id), [])
        self.assertEqual(
            self.servico.listar_por_equipamento(self.outro_equipamento.id), []
        )

    def test_nova_instancia_do_servico_recarrega_associacoes_do_banco(self):
        vulnerabilidade = self._cadastrar_vulnerabilidade()
        self.servico.associar(vulnerabilidade.id, self.equipamento.id)

        outro_servico = VulnerabilidadeService(VulnerabilidadeRepository(self.banco))

        self.assertEqual(
            outro_servico.listar_ids_de_equipamentos_afetados(vulnerabilidade.id),
            [self.equipamento.id],
        )

    # --- Exclusão de equipamento -----------------------------------

    def _excluir_equipamento(self, equipamento):
        self.servico_de_equipamentos.excluir(equipamento.id)
        return self.servico.sincronizar_apos_exclusao_de_equipamento(equipamento.id)

    def test_excluir_equipamento_exclui_vulnerabilidade_exclusiva_dele(self):
        exclusiva = self._cadastrar_vulnerabilidade("Exclusiva")
        self.servico.associar(exclusiva.id, self.equipamento.id)

        excluidas = self._excluir_equipamento(self.equipamento)

        self.assertEqual(excluidas, [exclusiva])
        with self.assertRaises(VulnerabilidadeNaoEncontradaError):
            self.servico.buscar_por_id(exclusiva.id)
        novo_servico = VulnerabilidadeService(VulnerabilidadeRepository(self.banco))
        self.assertEqual(novo_servico.listar_todas(), [])

    def test_excluir_equipamento_mantem_vulnerabilidade_compartilhada(self):
        compartilhada = self._cadastrar_vulnerabilidade("Compartilhada")
        self.servico.associar(compartilhada.id, self.equipamento.id)
        self.servico.associar(compartilhada.id, self.outro_equipamento.id)

        excluidas = self._excluir_equipamento(self.equipamento)

        self.assertEqual(excluidas, [])
        self.assertEqual(
            self.servico.listar_ids_de_equipamentos_afetados(compartilhada.id),
            [self.outro_equipamento.id],
        )

    def test_excluir_equipamento_mantem_vulnerabilidade_sem_associacao(self):
        avulsa = self._cadastrar_vulnerabilidade("Avulsa")

        self._excluir_equipamento(self.equipamento)

        self.assertEqual(self.servico.listar_todas(), [avulsa])

    def test_listar_exclusivas_do_equipamento_ignora_as_compartilhadas(self):
        exclusiva = self._cadastrar_vulnerabilidade("Exclusiva")
        compartilhada = self._cadastrar_vulnerabilidade("Compartilhada")
        self.servico.associar(exclusiva.id, self.equipamento.id)
        self.servico.associar(compartilhada.id, self.equipamento.id)
        self.servico.associar(compartilhada.id, self.outro_equipamento.id)

        self.assertEqual(
            self.servico.listar_exclusivas_do_equipamento(self.equipamento.id),
            [exclusiva],
        )


class TestVulnerabilidadeServiceValidacaoDeTexto(CasoDeTesteComServicos):
    """Testes das regras de caracteres permitidos nos campos de texto."""

    def test_cadastrar_aceita_numeros_na_descricao(self):
        vulnerabilidade = self.servico.cadastrar(
            "CVE 2024 1234", "Rede", 2.0, StatusVulnerabilidade.ABERTA
        )

        self.assertEqual(vulnerabilidade.descricao, "CVE 2024 1234")

    def test_cadastrar_com_descricao_apenas_numerica_levanta_erro(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar("2024", "Rede", 2.0, StatusVulnerabilidade.ABERTA)

    def test_cadastrar_com_numeros_na_categoria_levanta_erro(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.cadastrar(
                "Senha fraca", "Rede 5", 2.0, StatusVulnerabilidade.ABERTA
            )

    def test_cadastrar_com_caractere_especial_na_categoria_levanta_erro(self):
        with self.assertLogs(NOME_DO_LOGGER, level="WARNING"):
            with self.assertRaises(ErroDeValidacao):
                self.servico.cadastrar(
                    "Senha fraca", "Rede/Wi-Fi", 2.0, StatusVulnerabilidade.ABERTA
                )

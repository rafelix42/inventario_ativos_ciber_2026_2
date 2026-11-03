"""Testes da camada de regras de negócio (DependenciaService): cadastro,
alteração e remoção de dependências, e as regras que garantem que a matriz
(I - A) da análise de risco seja invertível."""

from app.exceptions import EquipamentoNaoEncontradoError, ErroDeValidacao
from app.models.equipamento import Servidor
from app.repositories.dependencia_repository import DependenciaRepository
from app.repositories.equipamento_repository import EquipamentoRepository
from app.services.dependencia_service import DependenciaService
from app.services.equipamento_service import EquipamentoService
from tests.base import CasoDeTesteComBancoTemporario

NOME_DO_LOGGER = "app.services.dependencia_service"


class TestDependenciaService(CasoDeTesteComBancoTemporario):
    """Testes do cadastro e das validações de dependências."""

    def setUp(self) -> None:
        super().setUp()
        self.servico_de_equipamentos = EquipamentoService(
            EquipamentoRepository(self.banco)
        )
        self.servico = DependenciaService(
            DependenciaRepository(self.banco), self.servico_de_equipamentos
        )
        self.web = self._cadastrar_servidor("Web")
        self.banco_de_dados = self._cadastrar_servidor("Banco")
        self.firewall = self._cadastrar_servidor("Firewall")

    def _cadastrar_servidor(self, nome: str):
        return self.servico_de_equipamentos.cadastrar(nome, "Fulano", "TI", Servidor)

    # --- Cadastro e alteração ----------------------------------------------

    def test_salvar_dependencia_valida_persiste_no_banco(self):
        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            self.servico.salvar(self.web.id, self.banco_de_dados.id, 0.4)

        dependencias = self.servico.listar_todas()
        self.assertEqual(len(dependencias), 1)
        self.assertEqual(dependencias[0].equipamento_id, self.web.id)
        self.assertEqual(dependencias[0].depende_de_id, self.banco_de_dados.id)
        self.assertEqual(dependencias[0].fator, 0.4)

    def test_salvar_dependencia_existente_substitui_o_fator(self):
        self.servico.salvar(self.web.id, self.banco_de_dados.id, 0.4)
        self.servico.salvar(self.web.id, self.banco_de_dados.id, 0.7)

        dependencias = self.servico.listar_todas()
        self.assertEqual(len(dependencias), 1)
        self.assertEqual(dependencias[0].fator, 0.7)

    def test_substituir_fator_nao_soma_o_fator_antigo(self):
        self.servico.salvar(self.web.id, self.banco_de_dados.id, 0.6)

        # 0.6 (antigo) + 0.6 (novo) passaria de 1, mas o antigo é substituído.
        self.servico.salvar(self.web.id, self.banco_de_dados.id, 0.6)

        self.assertAlmostEqual(self.servico.soma_dos_fatores(self.web.id), 0.6)

    # --- Validações -------------------------------------------------------

    def test_equipamento_nao_pode_depender_de_si_mesmo(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.salvar(self.web.id, self.web.id, 0.3)

    def test_fator_igual_a_um_e_recusado(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.salvar(self.web.id, self.banco_de_dados.id, 1.0)

    def test_fator_negativo_e_recusado(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.salvar(self.web.id, self.banco_de_dados.id, -0.1)

    def test_fator_nao_numerico_e_recusado(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.salvar(self.web.id, self.banco_de_dados.id, "alto")

    def test_soma_dos_fatores_da_linha_deve_ser_menor_que_um(self):
        self.servico.salvar(self.web.id, self.banco_de_dados.id, 0.6)

        with self.assertRaises(ErroDeValidacao):
            self.servico.salvar(self.web.id, self.firewall.id, 0.4)

    def test_soma_que_da_um_por_erro_de_arredondamento_e_recusada(self):
        # Em ponto flutuante, 0.1 + 0.2 + 0.7 = 0.9999999999999999.
        outro = self._cadastrar_servidor("Outro")
        self.servico.salvar(self.web.id, self.banco_de_dados.id, 0.1)
        self.servico.salvar(self.web.id, self.firewall.id, 0.2)

        with self.assertRaises(ErroDeValidacao):
            self.servico.salvar(self.web.id, outro.id, 0.7)

    def test_equipamento_inexistente_e_recusado(self):
        with self.assertRaises(EquipamentoNaoEncontradoError):
            self.servico.salvar(self.web.id, 999, 0.3)

    # --- Remoção ---------------------------------------------------------

    def test_excluir_remove_a_dependencia(self):
        self.servico.salvar(self.web.id, self.banco_de_dados.id, 0.4)

        with self.assertLogs(NOME_DO_LOGGER, level="INFO"):
            self.servico.excluir(self.web.id, self.banco_de_dados.id)

        self.assertEqual(self.servico.listar_todas(), [])

    def test_excluir_dependencia_inexistente_levanta_erro(self):
        with self.assertRaises(ErroDeValidacao):
            self.servico.excluir(self.web.id, self.banco_de_dados.id)

    def test_excluir_equipamento_remove_suas_dependencias(self):
        self.servico.salvar(self.web.id, self.banco_de_dados.id, 0.4)
        self.servico.salvar(self.firewall.id, self.web.id, 0.2)

        self.servico_de_equipamentos.excluir(self.web.id)

        self.assertEqual(self.servico.listar_todas(), [])

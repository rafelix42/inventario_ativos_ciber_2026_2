"""Testes da análise de risco (requisito 4): montagem de M, v, f e A a partir
dos dados persistidos, verificação de invertibilidade de (I - A) e cálculo
do risco próprio e do risco efetivo.

Cenário resolvido à mão (usado em vários testes abaixo)
-------------------------------------------------------
Três estações de trabalho (fator de exposição 1.0): E1, E2 e E3.
Vulnerabilidades: V1 (CVSS 8.0), V2 (CVSS 5.0) e V3 (CVSS 2.0).

    E1 é afetado por V1 e V2  ->  b1 = 8 + 5 = 13
    E2 é afetado por V2       ->  b2 = 5
    E3 é afetado por V3       ->  b3 = 2

Dependências: E2 depende de E1 com fator 0.5 e E3 depende de E2 com 0.5.

            | 0    0    0 |               |  1    0    0 |
        A = | 0.5  0    0 |      I - A =  | -0.5  1    0 |   det(I - A) = 1
            | 0    0.5  0 |               |  0   -0.5  1 |

Resolvendo x = b + A x linha a linha:
    x1 = 13
    x2 = 5 + 0.5 * x1 = 5 + 6.5  = 11.5
    x3 = 2 + 0.5 * x2 = 2 + 5.75 = 7.75
"""

import unittest

import numpy as np

from app.exceptions import SistemaNaoInvertivelError
from app.models.dependencia import Dependencia
from app.models.enums import StatusVulnerabilidade
from app.models.equipamento import EstacaoDeTrabalho, Firewall
from app.repositories.dependencia_repository import DependenciaRepository
from app.repositories.equipamento_repository import EquipamentoRepository
from app.repositories.vulnerabilidade_repository import VulnerabilidadeRepository
from app.services.analise_de_risco_service import (
    AnaliseDeRiscoService,
    calcular_risco_efetivo,
    calcular_risco_proprio,
    verificar_invertibilidade,
)
from app.services.dependencia_service import DependenciaService
from app.services.equipamento_service import EquipamentoService
from app.services.vulnerabilidade_service import VulnerabilidadeService
from tests.base import CasoDeTesteComBancoTemporario


class TestFuncoesDeAlgebraLinear(unittest.TestCase):
    """Testa as funções de álgebra linear com matrizes montadas à mão."""

    def test_risco_proprio_e_a_imagem_de_v_pela_matriz_m(self):
        matriz_de_incidencia = np.array([[1, 1, 0], [0, 1, 0], [0, 0, 1]])
        vetor_de_severidade = np.array([8.0, 5.0, 2.0])
        vetor_de_exposicao = np.array([1.0, 1.0, 1.0])

        risco_proprio = calcular_risco_proprio(
            matriz_de_incidencia, vetor_de_severidade, vetor_de_exposicao
        )

        np.testing.assert_allclose(risco_proprio, [13.0, 5.0, 2.0])

    def test_fator_de_exposicao_pondera_o_risco_proprio(self):
        matriz_de_incidencia = np.array([[1, 0], [0, 1]])
        vetor_de_severidade = np.array([4.0, 4.0])
        vetor_de_exposicao = np.array([1.5, 0.8])

        risco_proprio = calcular_risco_proprio(
            matriz_de_incidencia, vetor_de_severidade, vetor_de_exposicao
        )

        np.testing.assert_allclose(risco_proprio, [6.0, 3.2])

    def test_risco_efetivo_do_cenario_resolvido_a_mao(self):
        matriz_de_dependencias = np.array(
            [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [0.0, 0.5, 0.0]]
        )
        risco_proprio = np.array([13.0, 5.0, 2.0])

        risco_efetivo, determinante, _ = calcular_risco_efetivo(
            matriz_de_dependencias, risco_proprio
        )

        np.testing.assert_allclose(risco_efetivo, [13.0, 11.5, 7.75])
        self.assertAlmostEqual(determinante, 1.0)

    def test_risco_efetivo_com_dependencia_circular(self):
        # E1 e E2 dependem um do outro com fator 0.5; só E1 tem risco próprio.
        # x1 = 10 + 0.5 x2 e x2 = 0.5 x1  ->  x1 = 40/3 e x2 = 20/3.
        matriz_de_dependencias = np.array([[0.0, 0.5], [0.5, 0.0]])
        risco_proprio = np.array([10.0, 0.0])

        risco_efetivo, determinante, _ = calcular_risco_efetivo(
            matriz_de_dependencias, risco_proprio
        )

        np.testing.assert_allclose(risco_efetivo, [40 / 3, 20 / 3])
        self.assertAlmostEqual(determinante, 0.75)

    def test_matriz_singular_e_recusada(self):
        # Linhas iguais com sinal trocado: o determinante é zero.
        matriz = np.array([[1.0, -1.0], [-1.0, 1.0]])

        with self.assertRaises(SistemaNaoInvertivelError):
            verificar_invertibilidade(matriz)

    def test_matriz_quase_singular_e_recusada(self):
        # Na teoria o determinante é 1 - a², que não é zero, mas fica
        # tão perto de zero que a solução não seria confiável.
        a = 1 - 1e-14
        matriz = np.array([[1.0, -a], [-a, 1.0]])

        with self.assertRaises(SistemaNaoInvertivelError):
            verificar_invertibilidade(matriz)

    def test_numero_de_condicao_alto_e_recusado_mesmo_com_determinante_grande(self):
        # O determinante é 1, mas o número de condição é 10^14: só olhar o
        # determinante não basta para saber se a solução é confiável.
        matriz = np.diag([1e7, 1e-7])

        with self.assertRaises(SistemaNaoInvertivelError):
            verificar_invertibilidade(matriz)

    def test_matriz_bem_condicionada_retorna_determinante_e_condicao(self):
        matriz = np.array([[1.0, -0.5], [-0.5, 1.0]])

        determinante, numero_de_condicao = verificar_invertibilidade(matriz)

        self.assertAlmostEqual(determinante, 0.75)
        self.assertAlmostEqual(numero_de_condicao, 3.0)


class TestAnaliseDeRiscoService(CasoDeTesteComBancoTemporario):
    """Testa a montagem das matrizes a partir do banco e o cálculo completo."""

    def setUp(self) -> None:
        super().setUp()
        self.servico_de_equipamentos = EquipamentoService(
            EquipamentoRepository(self.banco)
        )
        self.servico_de_vulnerabilidades = VulnerabilidadeService(
            VulnerabilidadeRepository(self.banco)
        )
        self.servico_de_dependencias = DependenciaService(
            DependenciaRepository(self.banco), self.servico_de_equipamentos
        )
        self.servico = AnaliseDeRiscoService(
            self.servico_de_equipamentos,
            self.servico_de_vulnerabilidades,
            self.servico_de_dependencias,
        )

    def _cadastrar_equipamento(self, nome: str, classe=EstacaoDeTrabalho):
        return self.servico_de_equipamentos.cadastrar(nome, "Fulano", "TI", classe)

    def _cadastrar_vulnerabilidade(self, descricao: str, nota_cvss: float):
        return self.servico_de_vulnerabilidades.cadastrar(
            descricao, "Rede", nota_cvss, StatusVulnerabilidade.ABERTA
        )

    def _montar_cenario_resolvido_a_mao(self):
        """Cadastra o cenário descrito no início deste arquivo."""
        e1 = self._cadastrar_equipamento("Equipamento Um")
        e2 = self._cadastrar_equipamento("Equipamento Dois")
        e3 = self._cadastrar_equipamento("Equipamento Tres")
        v1 = self._cadastrar_vulnerabilidade("Vulnerabilidade Um", 8.0)
        v2 = self._cadastrar_vulnerabilidade("Vulnerabilidade Dois", 5.0)
        v3 = self._cadastrar_vulnerabilidade("Vulnerabilidade Tres", 2.0)

        self.servico_de_vulnerabilidades.associar(v1.id, e1.id)
        self.servico_de_vulnerabilidades.associar(v2.id, e1.id)
        self.servico_de_vulnerabilidades.associar(v2.id, e2.id)
        self.servico_de_vulnerabilidades.associar(v3.id, e3.id)

        self.servico_de_dependencias.salvar(e2.id, e1.id, 0.5)
        self.servico_de_dependencias.salvar(e3.id, e2.id, 0.5)

    # --- Montagem das matrizes ---------------------------------------------

    def test_montar_modelo_a_partir_dos_dados_persistidos(self):
        self._montar_cenario_resolvido_a_mao()

        modelo = self.servico.montar_modelo()

        np.testing.assert_array_equal(
            modelo.matriz_de_incidencia, [[1, 1, 0], [0, 1, 0], [0, 0, 1]]
        )
        np.testing.assert_array_equal(modelo.vetor_de_severidade, [8.0, 5.0, 2.0])
        np.testing.assert_array_equal(modelo.vetor_de_exposicao, [1.0, 1.0, 1.0])
        np.testing.assert_array_equal(
            modelo.matriz_de_dependencias,
            [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [0.0, 0.5, 0.0]],
        )

    def test_ids_nao_sequenciais_sao_convertidos_em_indices_da_matriz(self):
        excluido = self._cadastrar_equipamento("Sera Excluido")
        e1 = self._cadastrar_equipamento("Equipamento Um")
        e2 = self._cadastrar_equipamento("Equipamento Dois")
        self.servico_de_equipamentos.excluir(excluido.id)
        self.servico_de_dependencias.salvar(e1.id, e2.id, 0.3)

        modelo = self.servico.montar_modelo()

        # e1 tem id 2 e e2 tem id 3, mas viram as linhas 0 e 1 da matriz.
        np.testing.assert_array_equal(
            modelo.matriz_de_dependencias, [[0.0, 0.3], [0.0, 0.0]]
        )

    def test_fator_de_exposicao_vem_da_classe_do_equipamento(self):
        self._cadastrar_equipamento("Estacao", EstacaoDeTrabalho)
        self._cadastrar_equipamento("Perimetro", Firewall)

        modelo = self.servico.montar_modelo()

        np.testing.assert_array_equal(
            modelo.vetor_de_exposicao,
            [EstacaoDeTrabalho.FATOR_DE_EXPOSICAO, Firewall.FATOR_DE_EXPOSICAO],
        )

    # --- Cálculo completo ----------------------------------------------------

    def test_calcular_cenario_resolvido_a_mao(self):
        self._montar_cenario_resolvido_a_mao()

        with self.assertLogs("app.services.analise_de_risco_service", level="INFO"):
            resultado = self.servico.calcular()

        riscos_proprios = [risco.risco_proprio for risco in resultado.riscos]
        riscos_efetivos = [risco.risco_efetivo for risco in resultado.riscos]
        np.testing.assert_allclose(riscos_proprios, [13.0, 5.0, 2.0])
        np.testing.assert_allclose(riscos_efetivos, [13.0, 11.5, 7.75])
        self.assertAlmostEqual(resultado.riscos[1].risco_herdado, 6.5)
        self.assertAlmostEqual(resultado.determinante, 1.0)

    def test_calcular_sem_equipamentos_retorna_resultado_vazio(self):
        resultado = self.servico.calcular()

        self.assertEqual(resultado.riscos, [])

    def test_calcular_sem_vulnerabilidades_resulta_em_risco_zero(self):
        self._cadastrar_equipamento("Equipamento Um")

        resultado = self.servico.calcular()

        self.assertEqual(resultado.riscos[0].risco_proprio, 0.0)
        self.assertEqual(resultado.riscos[0].risco_efetivo, 0.0)

    def test_dependencias_inconsistentes_no_banco_sao_detectadas(self):
        # Gravando direto pelo repositório (sem as validações do serviço),
        # cada equipamento depende dos outros dois com fator 0.5. A soma de
        # cada linha de A fica 1, e (I - A) deixa de ser invertível.
        equipamentos = [
            self._cadastrar_equipamento(nome) for nome in ("Um", "Dois", "Tres")
        ]
        repositorio = DependenciaRepository(self.banco)
        for equipamento in equipamentos:
            for outro in equipamentos:
                if outro is not equipamento:
                    repositorio.salvar(Dependencia(equipamento.id, outro.id, 0.5))

        with self.assertRaises(SistemaNaoInvertivelError):
            self.servico.calcular()

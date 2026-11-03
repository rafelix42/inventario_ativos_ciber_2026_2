"""Análise de risco dos equipamentos por meio de um modelo linear (requisito 4).

Considere n equipamentos e m vulnerabilidades cadastrados. O cálculo segue
estes passos:

1. Matriz de incidência M (n x m):
       M[i][j] = 1 se o equipamento i é afetado pela vulnerabilidade j;
       M[i][j] = 0 caso contrário.

2. Vetor de severidade v (tamanho m):
       v[j] = nota CVSS da vulnerabilidade j.

3. Risco próprio b (tamanho n), considerando só as vulnerabilidades do
   próprio equipamento:
       b = f * (M @ v)
   'M @ v' é o produto matriz-vetor: soma as notas CVSS das vulnerabilidades
   de cada equipamento. 'f' é o vetor de exposição: f[i] é o
   FATOR_DE_EXPOSICAO da classe do equipamento i (polimorfismo: cada
   subclasse de Equipamento define o seu). O '*' multiplica elemento a
   elemento, ou seja, b[i] = f[i] * (M @ v)[i].

4. Matriz de dependências A (n x n):
       A[i][j] = fração do risco do equipamento j herdada pelo equipamento i.
   A diagonal é zero (ninguém depende de si mesmo).

5. Risco efetivo x (tamanho n): o risco próprio somado ao risco herdado:
       x = b + A x   <=>   (I - A) x = b
   Antes de resolver, verificamos se (I - A) é invertível.

A biblioteca NumPy faz as operações de álgebra linear (produto de matrizes,
determinante, número de condição e resolução do sistema).
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from app.exceptions import SistemaNaoInvertivelError
from app.models.equipamento import Equipamento
from app.models.vulnerabilidade import Vulnerabilidade
from app.services.dependencia_service import DependenciaService
from app.services.equipamento_service import EquipamentoService
from app.services.vulnerabilidade_service import VulnerabilidadeService

logger = logging.getLogger(__name__)

# Em ponto flutuante, um determinante que deveria ser zero raramente dá
# exatamente 0.0 (por exemplo, dá 1e-17). Por isso consideramos "zero"
# qualquer determinante com valor absoluto abaixo desta tolerância.
TOLERANCIA_DO_DETERMINANTE = 1e-10

# O número de condição mede o quanto um erro pequeno nos dados pode ser
# ampliado na solução. Com números float (cerca de 16 dígitos de precisão),
# um número de condição de 10^k faz perder aproximadamente k dígitos. Acima
# de 10^12 sobrariam menos de 4 dígitos confiáveis, então recusamos resolver.
LIMITE_DO_NUMERO_DE_CONDICAO = 1e12


@dataclass
class ModeloDeRisco:
    """Matrizes e vetores do modelo, montados a partir dos dados cadastrados.

    A ordem das listas define os índices das matrizes: 'equipamentos[i]' é a
    linha i de M e de A; 'vulnerabilidades[j]' é a coluna j de M.
    """

    equipamentos: List[Equipamento]
    vulnerabilidades: List[Vulnerabilidade]
    matriz_de_incidencia: np.ndarray  # M (n x m)
    vetor_de_severidade: np.ndarray  # v (m)
    vetor_de_exposicao: np.ndarray  # f (n)
    matriz_de_dependencias: np.ndarray  # A (n x n)


@dataclass
class RiscoDoEquipamento:
    """Resultado da análise para um único equipamento."""

    equipamento: Equipamento
    risco_proprio: float  # b[i]
    risco_efetivo: float  # x[i]

    @property
    def risco_herdado(self) -> float:
        """Parte do risco efetivo que vem das dependências: x[i] - b[i]."""
        return self.risco_efetivo - self.risco_proprio


@dataclass
class ResultadoDaAnaliseDeRisco:
    """Resultado completo da análise, com os indicadores numéricos de (I - A)."""

    riscos: List[RiscoDoEquipamento]
    determinante: float
    numero_de_condicao: float


# --- Funções de álgebra linear -------------------------------------------
#
# Ficam fora da classe para poderem ser testadas com matrizes montadas à mão,
# sem precisar de banco de dados.


def calcular_risco_proprio(
    matriz_de_incidencia: np.ndarray,
    vetor_de_severidade: np.ndarray,
    vetor_de_exposicao: np.ndarray,
) -> np.ndarray:
    """Calcula b = f * (M @ v)."""
    soma_das_notas_por_equipamento = matriz_de_incidencia @ vetor_de_severidade
    return vetor_de_exposicao * soma_das_notas_por_equipamento


def verificar_invertibilidade(matriz: np.ndarray) -> Tuple[float, float]:
    """Verifica se a matriz é invertível e se a solução será confiável.

    Retorna (determinante, numero_de_condicao). Levanta
    SistemaNaoInvertivelError se o determinante for praticamente zero ou se
    o número de condição for alto demais.
    """
    determinante = float(np.linalg.det(matriz))
    if abs(determinante) < TOLERANCIA_DO_DETERMINANTE:
        raise SistemaNaoInvertivelError(
            f"A matriz (I - A) não é invertível: o determinante é {determinante:.3e}, "
            "praticamente zero. Revise as dependências cadastradas."
        )

    numero_de_condicao = float(np.linalg.cond(matriz))
    if numero_de_condicao > LIMITE_DO_NUMERO_DE_CONDICAO:
        raise SistemaNaoInvertivelError(
            "A matriz (I - A) é mal condicionada (número de condição "
            f"{numero_de_condicao:.3e}): a solução não seria confiável. "
            "Revise as dependências cadastradas."
        )

    return determinante, numero_de_condicao


def calcular_risco_efetivo(
    matriz_de_dependencias: np.ndarray, risco_proprio: np.ndarray
) -> Tuple[np.ndarray, float, float]:
    """Resolve (I - A) x = b e retorna (x, determinante, numero_de_condicao).

    O sistema é resolvido diretamente com np.linalg.solve, que é mais
    preciso e mais rápido do que calcular a inversa de (I - A) e depois
    multiplicá-la por b.
    """
    quantidade_de_equipamentos = len(risco_proprio)
    identidade = np.eye(quantidade_de_equipamentos)
    matriz_do_sistema = identidade - matriz_de_dependencias  # (I - A)

    determinante, numero_de_condicao = verificar_invertibilidade(matriz_do_sistema)
    risco_efetivo = np.linalg.solve(matriz_do_sistema, risco_proprio)
    return risco_efetivo, determinante, numero_de_condicao


# --- Serviço --------------------------------------------------------------


class AnaliseDeRiscoService:
    """Monta as matrizes do modelo com os dados cadastrados e calcula o
    risco próprio e o risco efetivo de cada equipamento."""

    def __init__(
        self,
        servico_de_equipamentos: EquipamentoService,
        servico_de_vulnerabilidades: VulnerabilidadeService,
        servico_de_dependencias: DependenciaService,
    ):
        self._servico_de_equipamentos = servico_de_equipamentos
        self._servico_de_vulnerabilidades = servico_de_vulnerabilidades
        self._servico_de_dependencias = servico_de_dependencias

    def montar_modelo(self) -> ModeloDeRisco:
        """Monta M, v, f e A a partir dos dados persistidos."""
        equipamentos = self._servico_de_equipamentos.listar_todos()
        vulnerabilidades = self._servico_de_vulnerabilidades.listar_todas()

        # Os ids do banco não são sequenciais (pode haver buracos depois de
        # exclusões), então traduzimos cada id para a posição na matriz.
        indice_do_equipamento = {
            equipamento.id: indice for indice, equipamento in enumerate(equipamentos)
        }
        indice_da_vulnerabilidade = {
            vulnerabilidade.id: indice
            for indice, vulnerabilidade in enumerate(vulnerabilidades)
        }

        return ModeloDeRisco(
            equipamentos=equipamentos,
            vulnerabilidades=vulnerabilidades,
            matriz_de_incidencia=self._montar_matriz_de_incidencia(
                equipamentos, indice_da_vulnerabilidade
            ),
            vetor_de_severidade=np.array(
                [vulnerabilidade.nota_cvss for vulnerabilidade in vulnerabilidades],
                dtype=float,
            ),
            vetor_de_exposicao=np.array(
                [equipamento.FATOR_DE_EXPOSICAO for equipamento in equipamentos],
                dtype=float,
            ),
            matriz_de_dependencias=self._montar_matriz_de_dependencias(
                indice_do_equipamento
            ),
        )

    def calcular(self) -> ResultadoDaAnaliseDeRisco:
        """Calcula o risco próprio e o risco efetivo de todos os equipamentos.

        Levanta SistemaNaoInvertivelError se (I - A) não for invertível.
        """
        modelo = self.montar_modelo()
        if not modelo.equipamentos:
            return ResultadoDaAnaliseDeRisco(
                riscos=[], determinante=1.0, numero_de_condicao=1.0
            )

        risco_proprio = calcular_risco_proprio(
            modelo.matriz_de_incidencia,
            modelo.vetor_de_severidade,
            modelo.vetor_de_exposicao,
        )
        try:
            risco_efetivo, determinante, numero_de_condicao = calcular_risco_efetivo(
                modelo.matriz_de_dependencias, risco_proprio
            )
        except SistemaNaoInvertivelError as erro:
            logger.warning("Análise de risco não realizada: %s", erro)
            raise

        logger.info(
            "Análise de risco calculada: %s equipamento(s), %s vulnerabilidade(s), "
            "det(I - A)=%.4f, número de condição=%.4f",
            len(modelo.equipamentos),
            len(modelo.vulnerabilidades),
            determinante,
            numero_de_condicao,
        )
        riscos = [
            RiscoDoEquipamento(
                equipamento=equipamento,
                risco_proprio=float(risco_proprio[indice]),
                risco_efetivo=float(risco_efetivo[indice]),
            )
            for indice, equipamento in enumerate(modelo.equipamentos)
        ]
        return ResultadoDaAnaliseDeRisco(riscos, determinante, numero_de_condicao)

    def _montar_matriz_de_incidencia(
        self,
        equipamentos: List[Equipamento],
        indice_da_vulnerabilidade: Dict[int, int],
    ) -> np.ndarray:
        """M[i][j] = 1 se o equipamento i é afetado pela vulnerabilidade j."""
        matriz = np.zeros((len(equipamentos), len(indice_da_vulnerabilidade)))
        for i, equipamento in enumerate(equipamentos):
            for (
                vulnerabilidade
            ) in self._servico_de_vulnerabilidades.listar_por_equipamento(
                equipamento.id
            ):
                j = indice_da_vulnerabilidade[vulnerabilidade.id]
                matriz[i][j] = 1
        return matriz

    def _montar_matriz_de_dependencias(
        self, indice_do_equipamento: Dict[int, int]
    ) -> np.ndarray:
        """A[i][j] = fator com que o equipamento i depende do equipamento j."""
        quantidade_de_equipamentos = len(indice_do_equipamento)
        matriz = np.zeros((quantidade_de_equipamentos, quantidade_de_equipamentos))
        for dependencia in self._servico_de_dependencias.listar_todas():
            i = indice_do_equipamento[dependencia.equipamento_id]
            j = indice_do_equipamento[dependencia.depende_de_id]
            matriz[i][j] = dependencia.fator
        return matriz

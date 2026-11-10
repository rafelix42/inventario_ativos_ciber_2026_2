"""Regras de negócio das dependências entre equipamentos.

Uma dependência diz que um equipamento herda uma fração (o 'fator') do
risco de outro equipamento. Ela é a fonte da matriz A usada na análise de
risco (ver app/services/analise_de_risco_service.py).

Regras aplicadas no cadastro:
    - os dois equipamentos precisam existir e ser diferentes (A[i][i] = 0);
    - o fator deve estar no intervalo [0, 1);
    - a soma dos fatores de um mesmo equipamento (a soma da linha i de A)
      deve ser menor que 1.

A última regra garante que a matriz (I - A) seja estritamente diagonal
dominante e, portanto, sempre invertível.

Diferente dos outros serviços, este não mantém cache: as dependências são
sempre lidas do banco. Assim, quando um equipamento é excluído e o banco
remove as dependências dele (ON DELETE CASCADE), não há cache para
atualizar.
"""

import logging
from typing import List, Optional

from app.exceptions import ErroDeValidacao
from app.models.dependencia import Dependencia
from app.repositories.dependencia_repository import DependenciaRepository
from app.services.equipamento_service import EquipamentoService

logger = logging.getLogger(__name__)

FATOR_MINIMO = 0.0
# O fator e a soma dos fatores de um equipamento devem ser MENORES que este valor.
LIMITE_DO_FATOR = 1.0
# Somas como 0.1 + 0.2 + 0.7 dão 0.9999999999999999 em ponto flutuante.
# Arredondar antes de comparar evita aceitar uma soma que, na prática, é 1.
CASAS_DECIMAIS_DA_SOMA = 9


class DependenciaService:
    """Regras de negócio para cadastrar, listar e remover dependências."""

    def __init__(
        self,
        repositorio_de_dependencias: DependenciaRepository,
        servico_de_equipamentos: EquipamentoService,
    ):
        self._repositorio = repositorio_de_dependencias
        self._servico_de_equipamentos = servico_de_equipamentos

    # --- Consultas -------------------------------------------------------

    def listar_todas(self) -> List[Dependencia]:
        """Retorna todas as dependências cadastradas."""
        return self._repositorio.listar_todas()

    def listar_do_equipamento(self, equipamento_id: int) -> List[Dependencia]:
        """Retorna as dependências em que o equipamento é quem depende
        (ou seja, a linha do equipamento na matriz A)."""
        return [
            dependencia
            for dependencia in self.listar_todas()
            if dependencia.equipamento_id == equipamento_id
        ]

    def soma_dos_fatores(self, equipamento_id: int) -> float:
        """Soma dos fatores de um equipamento (soma da linha dele na matriz A)."""
        return sum(
            dependencia.fator
            for dependencia in self.listar_do_equipamento(equipamento_id)
        )

    # --- Cadastro, alteração e remoção --------------------------------------

    def salvar(
        self, equipamento_id: int, depende_de_id: int, fator: float
    ) -> Dependencia:
        """Valida e cadastra a dependência. Se ela já existir, o fator é
        substituído pelo novo valor."""
        # buscar_por_id levanta EquipamentoNaoEncontradoError se não existir.
        self._servico_de_equipamentos.buscar_por_id(equipamento_id)
        self._servico_de_equipamentos.buscar_por_id(depende_de_id)
        self._validar_equipamentos_diferentes(equipamento_id, depende_de_id)
        self._validar_fator(fator)
        self._validar_soma_da_linha(equipamento_id, depende_de_id, fator)

        dependencia = Dependencia(equipamento_id, depende_de_id, float(fator))
        self._repositorio.salvar(dependencia)
        logger.info(
            "Dependência salva: equipamento_id=%s depende de equipamento_id=%s "
            "com fator=%.2f",
            equipamento_id,
            depende_de_id,
            dependencia.fator,
        )
        return dependencia

    def excluir(self, equipamento_id: int, depende_de_id: int) -> None:
        """Remove a dependência entre os dois equipamentos."""
        if self._buscar(equipamento_id, depende_de_id) is None:
            logger.warning(
                "Exclusão de dependência falhou: equipamento_id=%s não depende "
                "de equipamento_id=%s.",
                equipamento_id,
                depende_de_id,
            )
            raise ErroDeValidacao("Esta dependência não está cadastrada.")

        self._repositorio.excluir(equipamento_id, depende_de_id)
        logger.info(
            "Dependência excluída: equipamento_id=%s não depende mais de "
            "equipamento_id=%s",
            equipamento_id,
            depende_de_id,
        )

    def _buscar(self, equipamento_id: int, depende_de_id: int) -> Optional[Dependencia]:
        return next(
            (
                dependencia
                for dependencia in self.listar_do_equipamento(equipamento_id)
                if dependencia.depende_de_id == depende_de_id
            ),
            None,
        )

    # --- Validações -------------------------------------------------------

    @staticmethod
    def _validar_equipamentos_diferentes(
        equipamento_id: int, depende_de_id: int
    ) -> None:
        if equipamento_id == depende_de_id:
            logger.warning(
                "Validação de dependência falhou: equipamento_id=%s não pode "
                "depender de si mesmo.",
                equipamento_id,
            )
            raise ErroDeValidacao("Um equipamento não pode depender de si mesmo.")

    @staticmethod
    def _validar_fator(fator: float) -> None:
        if isinstance(fator, bool) or not isinstance(fator, (int, float)):
            logger.warning(
                "Validação de dependência falhou: fator não numérico (%r).", fator
            )
            raise ErroDeValidacao("Informe o fator como um número.")

        if not FATOR_MINIMO <= fator < LIMITE_DO_FATOR:
            logger.warning(
                "Validação de dependência falhou: fator fora da faixa (%r).", fator
            )
            raise ErroDeValidacao(
                f"O fator deve ser maior ou igual a {FATOR_MINIMO:.1f} "
                f"e menor que {LIMITE_DO_FATOR:.1f}."
            )

    def _validar_soma_da_linha(
        self, equipamento_id: int, depende_de_id: int, fator: float
    ) -> None:
        """A soma dos fatores do equipamento, já contando o novo fator, deve
        ser menor que 1. Se a dependência já existir, o fator antigo dela
        não entra na soma, porque será substituído."""
        soma_das_outras_dependencias = sum(
            dependencia.fator
            for dependencia in self.listar_do_equipamento(equipamento_id)
            if dependencia.depende_de_id != depende_de_id
        )
        soma_total = round(soma_das_outras_dependencias + fator, CASAS_DECIMAIS_DA_SOMA)

        if soma_total >= LIMITE_DO_FATOR:
            logger.warning(
                "Validação de dependência falhou: soma dos fatores do "
                "equipamento_id=%s ficaria %.2f (deve ser menor que 1).",
                equipamento_id,
                soma_total,
            )
            disponivel = LIMITE_DO_FATOR - soma_das_outras_dependencias
            raise ErroDeValidacao(
                "A soma dos fatores das dependências de um equipamento deve ser "
                f"menor que 1. Este equipamento já usa "
                f"{soma_das_outras_dependencias:.2f}; informe um fator menor "
                f"que {disponivel:.2f}."
            )

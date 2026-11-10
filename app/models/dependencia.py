"""Modelo que representa a dependência entre dois equipamentos."""

from dataclasses import dataclass


@dataclass
class Dependencia:
    """Indica que um equipamento depende de outro e, por isso, herda parte
    do risco dele.

    Exemplo: um Servidor Web que depende de um Banco de Dados com fator 0.4
    herda 40% do risco efetivo do Banco de Dados.

    Na análise de risco, cada dependência vira um elemento da matriz A:
        A[i][j] = fator
    em que i é o 'equipamento_id' (quem depende) e j é o 'depende_de_id'
    (de quem ele depende). O fator fica no intervalo [0, 1).
    """

    equipamento_id: int
    depende_de_id: int
    fator: float

"""Enumerações utilizadas para padronizar valores fixos da aplicação.

Usar Enum (em vez de strings soltas) evita erros de digitação e deixa
explícito, em um único lugar, quais são os valores válidos para cada campo.
"""

from enum import Enum


class TipoAtivo(Enum):
    """Tipos de ativos de TI que podem ser cadastrados no inventário."""

    ESTACAO_DE_TRABALHO = 1
    NOTEBOOK = 2
    SERVIDOR = 3
    BANCO_DE_DADOS = 4
    SOFTWARE_LICENCIADO = 5
    IMPRESSORA = 6
    ROTEADOR = 7
    SWITCH = 8
    FIREWALL = 9


class Severidade(Enum):
    """Nível de gravidade de uma vulnerabilidade.

    O usuário não escolhe a severidade diretamente: ele informa uma nota
    CVSS (0.0 a 10.0) e a severidade é classificada automaticamente a
    partir dela, seguindo as faixas oficiais do CVSS v3.1.
    """

    NENHUMA = 0
    BAIXA = 1
    MEDIA = 2
    ALTA = 3
    CRITICA = 4

    @classmethod
    def a_partir_da_nota_cvss(cls, nota_cvss: float) -> "Severidade":
        """Classifica uma nota CVSS (0.0 a 10.0) na faixa de severidade correspondente.

        Faixas oficiais do CVSS v3.1:
            0.0        -> Nenhuma
            0.1 - 3.9  -> Baixa
            4.0 - 6.9  -> Média
            7.0 - 8.9  -> Alta
            9.0 - 10.0 -> Crítica
        """
        if nota_cvss <= 0.0:
            return cls.NENHUMA
        if nota_cvss <= 3.9:
            return cls.BAIXA
        if nota_cvss <= 6.9:
            return cls.MEDIA
        if nota_cvss <= 8.9:
            return cls.ALTA
        return cls.CRITICA


class StatusVulnerabilidade(Enum):
    """Situação atual do tratamento de uma vulnerabilidade."""

    ABERTA = 1
    EM_TRATAMENTO = 2
    CORRIGIDA = 3
    ACEITA_COMO_RISCO = 4


def rotulo_amigavel(nome_do_enum: str) -> str:
    """Formata os nomes para exibição na tela.

    Exemplo: 'EM_TRATAMENTO' vira 'Em Tratamento'.
    """
    return nome_do_enum.replace("_", " ").title()

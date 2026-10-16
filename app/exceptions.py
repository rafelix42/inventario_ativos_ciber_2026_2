"""Exceções personalizadas da aplicação.

Usar exceções próprias (em vez de deixar vazar erros genéricos do Python ou
do SQLite) facilita tratar cada situação de forma específica na interface
de texto, exibindo mensagens claras para o usuário.
"""


class ErroDeValidacao(Exception):
    """Levantada quando os dados informados pelo usuário são inválidos."""


class EquipamentoNaoEncontradoError(Exception):
    """Levantada quando um equipamento não é localizado na base de dados."""


class VulnerabilidadeNaoEncontradaError(Exception):
    """Levantada quando uma vulnerabilidade não é localizada na base de dados."""

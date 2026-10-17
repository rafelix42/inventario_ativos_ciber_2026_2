"""Regras de validação de texto compartilhadas pelos serviços.

Os campos de texto informados pelo usuário nunca aceitam caracteres
especiais (pontuação, hífen, símbolos etc.). Alguns campos aceitam só
letras; outros aceitam também números, desde que não sejam só números.
"""

import logging

from app.exceptions import ErroDeValidacao


def contem_apenas_letras(texto: str) -> bool:
    """Indica se o texto tem apenas letras (inclusive acentuadas) e espaços."""
    return all(caractere.isalpha() or caractere == " " for caractere in texto)


def contem_apenas_letras_e_numeros(texto: str) -> bool:
    """Indica se o texto tem apenas letras, números e espaços."""
    return all(caractere.isalnum() or caractere == " " for caractere in texto)


def contem_alguma_letra(texto: str) -> bool:
    """Indica se o texto tem pelo menos uma letra (ou seja, não é só números)."""
    return any(caractere.isalpha() for caractere in texto)


def validar_apenas_letras(logger: logging.Logger, entidade: str, **campos: str) -> None:
    """Levanta ErroDeValidacao se algum campo tiver números ou caracteres especiais.

    O 'logger' é o do serviço que chamou, para que a tentativa inválida
    fique registrada no log de auditoria com o módulo de origem.
    """
    for nome_do_campo, valor in campos.items():
        if not contem_apenas_letras(valor.strip()):
            _recusar_campo(
                logger,
                entidade,
                nome_do_campo,
                valor,
                "deve conter apenas letras e espaços",
            )


def validar_letras_e_numeros(
    logger: logging.Logger, entidade: str, **campos: str
) -> None:
    """Levanta ErroDeValidacao se algum campo tiver caracteres especiais ou
    for composto apenas por números.

    Campos vazios são ignorados aqui: a obrigatoriedade é verificada à parte.
    """
    for nome_do_campo, valor in campos.items():
        texto = valor.strip()
        if not texto:
            continue
        if not contem_apenas_letras_e_numeros(texto):
            _recusar_campo(
                logger,
                entidade,
                nome_do_campo,
                valor,
                "não pode conter caracteres especiais",
            )
        if not contem_alguma_letra(texto):
            _recusar_campo(
                logger,
                entidade,
                nome_do_campo,
                valor,
                "não pode conter apenas números",
            )


def _recusar_campo(
    logger: logging.Logger, entidade: str, nome_do_campo: str, valor: str, motivo: str
) -> None:
    logger.warning(
        "Validação de %s falhou: campo '%s' %s (%r).",
        entidade,
        nome_do_campo,
        motivo,
        valor,
    )
    raise ErroDeValidacao(f"O campo '{nome_do_campo}' {motivo}.")

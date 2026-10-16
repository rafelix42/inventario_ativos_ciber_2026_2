"""Regras de validação de texto compartilhadas pelos serviços."""

import logging

from app.exceptions import ErroDeValidacao


def contem_apenas_letras(texto: str) -> bool:
    """Indica se o texto tem apenas letras (inclusive acentuadas) e espaços.

    Números e caracteres especiais (pontuação, hífen, símbolos etc.) não
    são permitidos nos campos de texto informados pelo usuário.
    """
    return all(caractere.isalpha() or caractere == " " for caractere in texto)


def validar_apenas_letras(logger: logging.Logger, entidade: str, **campos: str) -> None:
    """Levanta ErroDeValidacao se algum campo tiver números ou caracteres especiais.

    O 'logger' é o do serviço que chamou, para que a tentativa inválida
    fique registrada no log de auditoria com o módulo de origem.
    """
    for nome_do_campo, valor in campos.items():
        if not contem_apenas_letras(valor.strip()):
            logger.warning(
                "Validação de %s falhou: campo '%s' contém números "
                "ou caracteres especiais (%r).",
                entidade,
                nome_do_campo,
                valor,
            )
            raise ErroDeValidacao(
                f"O campo '{nome_do_campo}' deve conter apenas letras e espaços."
            )

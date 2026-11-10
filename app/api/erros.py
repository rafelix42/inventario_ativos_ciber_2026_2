"""Converte as exceções da aplicação em respostas HTTP.

Os serviços levantam exceções próprias (app/exceptions.py) sem saber nada de
HTTP. Aqui cada exceção ganha um código de status, e toda resposta de erro
tem o mesmo formato JSON, fácil de tratar no frontend:

    {"detail": "Mensagem explicando o que deu errado."}

Para tratar uma nova exceção, basta incluí-la em STATUS_HTTP_POR_EXCECAO.
"""

import logging
from typing import Dict, Type

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions import (
    EquipamentoNaoEncontradoError,
    ErroDeValidacao,
    SistemaNaoInvertivelError,
    VulnerabilidadeNaoEncontradaError,
)

logger = logging.getLogger(__name__)

STATUS_HTTP_POR_EXCECAO: Dict[Type[Exception], int] = {
    ErroDeValidacao: 422,  # Unprocessable Content: dados recusados por uma regra
    EquipamentoNaoEncontradoError: 404,  # Not Found
    VulnerabilidadeNaoEncontradaError: 404,  # Not Found
    SistemaNaoInvertivelError: 409,  # Conflict: os dados atuais impedem o cálculo
}


def registrar_tratadores_de_erro(aplicacao: FastAPI) -> None:
    """Registra na aplicação os tratadores de todas as exceções acima."""
    for classe_da_excecao in STATUS_HTTP_POR_EXCECAO:
        aplicacao.add_exception_handler(classe_da_excecao, _tratar_erro_da_aplicacao)
    aplicacao.add_exception_handler(RequestValidationError, _tratar_json_invalido)


async def _tratar_erro_da_aplicacao(_requisicao: Request, erro: Exception):
    # Os serviços já registram no log de auditoria as tentativas inválidas.
    return JSONResponse(
        status_code=STATUS_HTTP_POR_EXCECAO[type(erro)],
        content={"detail": str(erro)},
    )


async def _tratar_json_invalido(requisicao: Request, erro: RequestValidationError):
    """Erros detectados pelos esquemas (tipo errado, campo faltando, opção
    inexistente). Por padrão o FastAPI devolve uma lista de erros; aqui
    juntamos tudo em uma mensagem só, no mesmo formato dos demais erros."""
    mensagens = [_descrever_erro_de_campo(item) for item in erro.errors()]
    mensagem = " ".join(mensagens)
    logger.warning(
        "Requisição recusada: %s %s: %s",
        requisicao.method,
        requisicao.url.path,
        mensagem,
    )
    return JSONResponse(status_code=422, content={"detail": mensagem})


def _descrever_erro_de_campo(item: dict) -> str:
    # 'loc' indica onde está o erro, ex.: ("body", "nota_cvss"). O primeiro
    # elemento (body, path, query) não interessa ao usuário.
    caminho = ".".join(str(parte) for parte in item["loc"][1:])
    texto = MENSAGENS_POR_TIPO_DE_ERRO.get(item["type"]) or item["msg"].removeprefix(
        "Value error, "
    )
    return f"Campo '{caminho}': {texto}." if caminho else f"{texto}."


# O Pydantic escreve as mensagens em inglês. Estas são as mais comuns,
# traduzidas; as demais aparecem como o Pydantic as escreveu. A lista completa
# de tipos está em https://docs.pydantic.dev/latest/errors/validation_errors/
MENSAGENS_POR_TIPO_DE_ERRO: Dict[str, str] = {
    "missing": "campo obrigatório não informado",
    "string_type": "deve ser um texto",
    "float_type": "deve ser um número",
    "float_parsing": "deve ser um número (use ponto como separador decimal)",
    "int_type": "deve ser um número inteiro",
    "int_parsing": "deve ser um número inteiro",
    "json_invalid": "o corpo da requisição não é um JSON válido",
    "model_attributes_type": "o corpo da requisição deve ser um objeto JSON",
}

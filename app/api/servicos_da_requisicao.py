"""Dá às rotas acesso aos serviços da aplicação.

Os serviços são criados uma única vez, quando a API inicia (ver
app/api/aplicacao.py), e guardados em 'app.state.servicos'. Cada rota recebe
esses serviços declarando um parâmetro do tipo 'Servicos':

    @rotas.get("/")
    async def listar(servicos: Servicos): ...

O FastAPI chama 'obter_servicos' automaticamente e passa o resultado para a
rota (é a "injeção de dependências" do FastAPI, com Depends).
"""

from typing import Annotated

from fastapi import Depends, Request

from app.servicos import ServicosDaAplicacao


def obter_servicos(requisicao: Request) -> ServicosDaAplicacao:
    """Retorna os serviços criados na inicialização da API."""
    return requisicao.app.state.servicos


Servicos = Annotated[ServicosDaAplicacao, Depends(obter_servicos)]

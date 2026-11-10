"""Cria a aplicação FastAPI: banco de dados, serviços, CORS, erros e rotas.

Todas as rotas ficam sob o prefixo /api (ex.: GET /api/equipamentos). A
documentação interativa, gerada automaticamente, fica em /docs.

ATENÇÃO: todas as rotas são 'async def'. Assim, o FastAPI executa uma
requisição de cada vez, sempre no mesmo thread em que a conexão com o SQLite
foi aberta, o que mantém seguros a conexão e os caches em dicionário dos
serviços. Uma rota escrita com 'def' (sem async) rodaria em outro thread e o
SQLite recusaria a consulta. Por isso, mantenha 'async def' nas rotas novas.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Sequence

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.erros import registrar_tratadores_de_erro
from app.api.rotas import (
    analise_de_risco,
    dependencias,
    equipamentos,
    opcoes,
    vulnerabilidades,
)
from app.repositories.database import CAMINHO_PADRAO_DO_BANCO, ConexaoBancoDeDados
from app.servicos import criar_servicos

logger = logging.getLogger(__name__)

PREFIXO_DAS_ROTAS = "/api"

# Endereços dos servidores de desenvolvimento mais comuns de frontend
# JavaScript (Vite usa a porta 5173; Create React App e Next.js, a 3000).
ORIGENS_PADRAO = ("http://localhost:5173", "http://localhost:3000")


def criar_aplicacao(
    caminho_do_banco: Path = CAMINHO_PADRAO_DO_BANCO,
    origens_permitidas: Sequence[str] = ORIGENS_PADRAO,
) -> FastAPI:
    """Monta a aplicação FastAPI.

    'caminho_do_banco': arquivo SQLite usado (os testes passam um temporário).
    'origens_permitidas': endereços de frontend que podem chamar a API pelo
    navegador (CORS).
    """

    @asynccontextmanager
    async def ciclo_de_vida(aplicacao: FastAPI) -> AsyncIterator[None]:
        # Executado uma vez ao iniciar a API (antes do 'yield') e uma vez ao
        # encerrá-la (depois do 'yield').
        banco_de_dados = ConexaoBancoDeDados(caminho_do_banco)
        aplicacao.state.servicos = criar_servicos(banco_de_dados)
        logger.info("API iniciada (banco de dados: %s).", caminho_do_banco)
        yield
        banco_de_dados.fechar()
        logger.info("API encerrada.")

    aplicacao = FastAPI(
        title="Inventário de Ativos de TI",
        description="Cadastro de equipamentos e vulnerabilidades, com análise "
        "de risco por modelo linear.",
        version="2.0.0",
        lifespan=ciclo_de_vida,
    )

    # Sem CORS, o navegador bloqueia chamadas de um frontend que está em
    # outro endereço (ex.: http://localhost:5173 chamando a porta 8000).
    aplicacao.add_middleware(
        CORSMiddleware,
        allow_origins=list(origens_permitidas),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    registrar_tratadores_de_erro(aplicacao)

    for modulo in (
        equipamentos,
        vulnerabilidades,
        dependencias,
        analise_de_risco,
        opcoes,
    ):
        aplicacao.include_router(modulo.rotas, prefix=PREFIXO_DAS_ROTAS)

    return aplicacao

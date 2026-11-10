"""Rotas do catálogo de vulnerabilidades.

Para atribuir ou remover uma vulnerabilidade de um equipamento, use as rotas
/equipamentos/{equipamento_id}/vulnerabilidades/{vulnerabilidade_id}
(app/api/rotas/equipamentos.py).
"""

from typing import List

from fastapi import APIRouter

from app.api.esquemas import (
    DadosDaVulnerabilidade,
    EquipamentoResposta,
    VulnerabilidadeResposta,
)
from app.api.respostas import equipamento_para_resposta, vulnerabilidade_para_resposta
from app.api.servicos_da_requisicao import Servicos
from app.models.enums import StatusVulnerabilidade

rotas = APIRouter(prefix="/vulnerabilidades", tags=["Vulnerabilidades"])


@rotas.get("")
async def listar_vulnerabilidades(servicos: Servicos) -> List[VulnerabilidadeResposta]:
    """Lista todas as vulnerabilidades do catálogo."""
    return [
        vulnerabilidade_para_resposta(v, servicos)
        for v in servicos.vulnerabilidades.listar_todas()
    ]


@rotas.get("/{vulnerabilidade_id}")
async def buscar_vulnerabilidade(
    vulnerabilidade_id: int, servicos: Servicos
) -> VulnerabilidadeResposta:
    """Retorna uma vulnerabilidade pelo ID (404 se não existir)."""
    vulnerabilidade = servicos.vulnerabilidades.buscar_por_id(vulnerabilidade_id)
    return vulnerabilidade_para_resposta(vulnerabilidade, servicos)


@rotas.post("", status_code=201)
async def cadastrar_vulnerabilidade(
    dados: DadosDaVulnerabilidade, servicos: Servicos
) -> VulnerabilidadeResposta:
    """Cadastra uma vulnerabilidade. A severidade é calculada pela nota CVSS."""
    vulnerabilidade = servicos.vulnerabilidades.cadastrar(
        descricao=dados.descricao,
        categoria=dados.categoria,
        nota_cvss=dados.nota_cvss,
        status=StatusVulnerabilidade[dados.status],
    )
    return vulnerabilidade_para_resposta(vulnerabilidade, servicos)


@rotas.put("/{vulnerabilidade_id}")
async def atualizar_vulnerabilidade(
    vulnerabilidade_id: int, dados: DadosDaVulnerabilidade, servicos: Servicos
) -> VulnerabilidadeResposta:
    """Atualiza uma vulnerabilidade."""
    vulnerabilidade = servicos.vulnerabilidades.atualizar(
        vulnerabilidade_id=vulnerabilidade_id,
        descricao=dados.descricao,
        categoria=dados.categoria,
        nota_cvss=dados.nota_cvss,
        status=StatusVulnerabilidade[dados.status],
    )
    return vulnerabilidade_para_resposta(vulnerabilidade, servicos)


@rotas.delete("/{vulnerabilidade_id}", status_code=204)
async def excluir_vulnerabilidade(vulnerabilidade_id: int, servicos: Servicos) -> None:
    """Exclui a vulnerabilidade e a remove de todos os equipamentos."""
    servicos.vulnerabilidades.excluir(vulnerabilidade_id)


@rotas.get("/{vulnerabilidade_id}/equipamentos")
async def listar_equipamentos_afetados(
    vulnerabilidade_id: int, servicos: Servicos
) -> List[EquipamentoResposta]:
    """Lista os equipamentos afetados pela vulnerabilidade."""
    ids_afetados = servicos.vulnerabilidades.listar_ids_de_equipamentos_afetados(
        vulnerabilidade_id
    )
    return [
        equipamento_para_resposta(servicos.equipamentos.buscar_por_id(i), servicos)
        for i in ids_afetados
    ]

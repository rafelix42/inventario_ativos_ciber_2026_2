"""Rotas com os valores fixos aceitos pela API e a verificação de saúde.

O frontend usa estas rotas para preencher listas de seleção (tipos de
equipamento, status), em vez de repetir esses valores no código JavaScript.
"""

from typing import Dict, List

from fastapi import APIRouter

from app.api.esquemas import OpcaoResposta, TipoDeEquipamentoResposta
from app.models.enums import Severidade, StatusVulnerabilidade, rotulo_amigavel
from app.models.equipamento import TIPOS_DE_EQUIPAMENTO

rotas = APIRouter(tags=["Opções e saúde"])


@rotas.get("/tipos-de-equipamento")
async def listar_tipos_de_equipamento() -> List[TipoDeEquipamentoResposta]:
    """Tipos de equipamento que podem ser cadastrados."""
    return [
        TipoDeEquipamentoResposta(
            classe=nome_da_classe,
            rotulo=classe.ROTULO,
            fator_de_exposicao=classe.FATOR_DE_EXPOSICAO,
        )
        for nome_da_classe, classe in TIPOS_DE_EQUIPAMENTO.items()
    ]


@rotas.get("/status-de-vulnerabilidade")
async def listar_status_de_vulnerabilidade() -> List[OpcaoResposta]:
    """Status que uma vulnerabilidade pode ter."""
    return [
        OpcaoResposta(valor=status.name, rotulo=rotulo_amigavel(status.name))
        for status in StatusVulnerabilidade
    ]


@rotas.get("/severidades")
async def listar_severidades() -> List[OpcaoResposta]:
    """Severidades possíveis (calculadas a partir da nota CVSS)."""
    return [
        OpcaoResposta(valor=severidade.name, rotulo=rotulo_amigavel(severidade.name))
        for severidade in Severidade
    ]


@rotas.get("/saude")
async def verificar_saude() -> Dict[str, str]:
    """Indica que a API está no ar (usado pelo healthcheck do Docker)."""
    return {"status": "ok"}

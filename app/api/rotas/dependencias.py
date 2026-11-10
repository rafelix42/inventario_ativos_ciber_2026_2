"""Rotas das dependências entre equipamentos (matriz A da análise de risco).

Uma dependência é identificada pelo par de equipamentos:
    /dependencias/{equipamento_id}/{depende_de_id}
em que 'equipamento_id' depende de 'depende_de_id'.
"""

from typing import List, Optional

from fastapi import APIRouter

from app.api.esquemas import DependenciaResposta, FatorDaDependencia
from app.api.servicos_da_requisicao import Servicos

rotas = APIRouter(prefix="/dependencias", tags=["Dependências"])


@rotas.get("")
async def listar_dependencias(
    servicos: Servicos, equipamento_id: Optional[int] = None
) -> List[DependenciaResposta]:
    """Lista as dependências. Com '?equipamento_id=N', só as do equipamento N
    (as dependências em que ele é quem depende)."""
    if equipamento_id is None:
        dependencias = servicos.dependencias.listar_todas()
    else:
        dependencias = servicos.dependencias.listar_do_equipamento(equipamento_id)
    return [DependenciaResposta.a_partir_do_modelo(d) for d in dependencias]


@rotas.put("/{equipamento_id}/{depende_de_id}")
async def salvar_dependencia(
    equipamento_id: int,
    depende_de_id: int,
    dados: FatorDaDependencia,
    servicos: Servicos,
) -> DependenciaResposta:
    """Cadastra a dependência ou, se ela já existir, troca o fator.

    O fator deve estar em [0, 1) e a soma dos fatores do equipamento deve
    ficar menor que 1 (senão, 422)."""
    dependencia = servicos.dependencias.salvar(
        equipamento_id, depende_de_id, dados.fator
    )
    return DependenciaResposta.a_partir_do_modelo(dependencia)


@rotas.delete("/{equipamento_id}/{depende_de_id}", status_code=204)
async def excluir_dependencia(
    equipamento_id: int, depende_de_id: int, servicos: Servicos
) -> None:
    """Remove a dependência."""
    servicos.dependencias.excluir(equipamento_id, depende_de_id)

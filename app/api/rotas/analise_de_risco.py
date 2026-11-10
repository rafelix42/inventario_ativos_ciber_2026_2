"""Rotas da análise de risco (requisito 4).

O cálculo é refeito a cada requisição, sempre com os dados atuais. Se a
matriz (I - A) não for invertível, a resposta é 409 com a explicação.
"""

from fastapi import APIRouter

from app.api.esquemas import (
    AnaliseDeRiscoResposta,
    MatrizesDoModeloResposta,
    RiscoDoEquipamentoResposta,
)
from app.api.servicos_da_requisicao import Servicos

rotas = APIRouter(prefix="/analise-de-risco", tags=["Análise de risco"])


@rotas.get("")
async def calcular_riscos(servicos: Servicos) -> AnaliseDeRiscoResposta:
    """Risco próprio e risco efetivo de todos os equipamentos, do maior para
    o menor risco efetivo, com o determinante e o número de condição de (I - A)."""
    resultado = servicos.analise_de_risco.calcular()
    riscos_ordenados = sorted(
        resultado.riscos, key=lambda risco: risco.risco_efetivo, reverse=True
    )
    return AnaliseDeRiscoResposta(
        determinante=resultado.determinante,
        numero_de_condicao=resultado.numero_de_condicao,
        riscos=[
            RiscoDoEquipamentoResposta.a_partir_do_modelo(r) for r in riscos_ordenados
        ],
    )


@rotas.get("/equipamentos/{equipamento_id}")
async def consultar_risco_do_equipamento(
    equipamento_id: int, servicos: Servicos
) -> RiscoDoEquipamentoResposta:
    """Risco próprio e risco efetivo de um único equipamento."""
    servicos.equipamentos.buscar_por_id(equipamento_id)  # 404 se não existir
    resultado = servicos.analise_de_risco.calcular()
    risco = next(r for r in resultado.riscos if r.equipamento.id == equipamento_id)
    return RiscoDoEquipamentoResposta.a_partir_do_modelo(risco)


@rotas.get("/matrizes")
async def exibir_matrizes(servicos: Servicos) -> MatrizesDoModeloResposta:
    """Matrizes M e A e vetores v e f, montados a partir dos dados cadastrados."""
    modelo = servicos.analise_de_risco.montar_modelo()
    return MatrizesDoModeloResposta.a_partir_do_modelo(modelo)

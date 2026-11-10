"""Monta as respostas de equipamento e de vulnerabilidade.

Ficam aqui (e não nas rotas) porque as duas rotas usam as duas funções: as
rotas de equipamentos devolvem vulnerabilidades, e vice-versa.
"""

from app.api.esquemas import EquipamentoResposta, VulnerabilidadeResposta
from app.models.equipamento import Equipamento
from app.models.vulnerabilidade import Vulnerabilidade
from app.servicos import ServicosDaAplicacao


def equipamento_para_resposta(
    equipamento: Equipamento, servicos: ServicosDaAplicacao
) -> EquipamentoResposta:
    """Monta a resposta de um equipamento, com a quantidade de vulnerabilidades."""
    vulnerabilidades = servicos.vulnerabilidades.listar_por_equipamento(equipamento.id)
    return EquipamentoResposta.a_partir_do_modelo(equipamento, len(vulnerabilidades))


def vulnerabilidade_para_resposta(
    vulnerabilidade: Vulnerabilidade, servicos: ServicosDaAplicacao
) -> VulnerabilidadeResposta:
    """Monta a resposta de uma vulnerabilidade, com os equipamentos afetados."""
    ids_afetados = servicos.vulnerabilidades.listar_ids_de_equipamentos_afetados(
        vulnerabilidade.id
    )
    return VulnerabilidadeResposta.a_partir_do_modelo(vulnerabilidade, ids_afetados)

"""Rotas de equipamentos e das vulnerabilidades de cada equipamento.

As rotas só traduzem HTTP <-> serviços: leem o JSON/parâmetros, chamam o
serviço e convertem o resultado em resposta. Validações e regras de negócio
ficam nos serviços; erros viram respostas HTTP em app/api/erros.py.
"""

from typing import List

from fastapi import APIRouter

from app.api.esquemas import (
    AtualizacaoDeEquipamento,
    CadastroDeEquipamento,
    EquipamentoResposta,
    ExclusaoDeEquipamentoResposta,
    VulnerabilidadeResposta,
)
from app.api.respostas import equipamento_para_resposta, vulnerabilidade_para_resposta
from app.api.servicos_da_requisicao import Servicos
from app.models.equipamento import TIPOS_DE_EQUIPAMENTO

rotas = APIRouter(prefix="/equipamentos", tags=["Equipamentos"])


# --- CRUD --------------------------------------------------------------------


@rotas.get("")
async def listar_equipamentos(
    servicos: Servicos, nome: str = ""
) -> List[EquipamentoResposta]:
    """Lista os equipamentos. Com '?nome=texto', só os que contêm o texto no nome."""
    equipamentos = servicos.equipamentos.buscar_por_nome(nome)
    return [equipamento_para_resposta(e, servicos) for e in equipamentos]


@rotas.get("/{equipamento_id}")
async def buscar_equipamento(
    equipamento_id: int, servicos: Servicos
) -> EquipamentoResposta:
    """Retorna um equipamento pelo ID (404 se não existir)."""
    equipamento = servicos.equipamentos.buscar_por_id(equipamento_id)
    return equipamento_para_resposta(equipamento, servicos)


@rotas.post("", status_code=201)
async def cadastrar_equipamento(
    dados: CadastroDeEquipamento, servicos: Servicos
) -> EquipamentoResposta:
    """Cadastra um equipamento."""
    equipamento = servicos.equipamentos.cadastrar(
        nome=dados.nome,
        responsavel=dados.responsavel,
        setor=dados.setor,
        classe=TIPOS_DE_EQUIPAMENTO[dados.classe],
        descricao=dados.descricao,
    )
    return equipamento_para_resposta(equipamento, servicos)


@rotas.put("/{equipamento_id}")
async def atualizar_equipamento(
    equipamento_id: int, dados: AtualizacaoDeEquipamento, servicos: Servicos
) -> EquipamentoResposta:
    """Atualiza um equipamento. O nome não pode ser alterado."""
    equipamento = servicos.equipamentos.atualizar(
        equipamento_id=equipamento_id,
        responsavel=dados.responsavel,
        setor=dados.setor,
        classe=TIPOS_DE_EQUIPAMENTO[dados.classe],
        descricao=dados.descricao,
    )
    return equipamento_para_resposta(equipamento, servicos)


@rotas.delete("/{equipamento_id}")
async def excluir_equipamento(
    equipamento_id: int, servicos: Servicos
) -> ExclusaoDeEquipamentoResposta:
    """Exclui um equipamento, suas dependências e as vulnerabilidades que só
    afetavam ele. Antes de confirmar, o frontend pode avisar o usuário
    consultando GET /equipamentos/{id}/vulnerabilidades-exclusivas."""
    servicos.equipamentos.excluir(equipamento_id)
    # O banco já excluiu as vulnerabilidades exclusivas; falta atualizar o
    # cache do serviço de vulnerabilidades.
    excluidas = servicos.vulnerabilidades.sincronizar_apos_exclusao_de_equipamento(
        equipamento_id
    )
    return ExclusaoDeEquipamentoResposta(
        ids_das_vulnerabilidades_excluidas=[v.id for v in excluidas]
    )


# --- Vulnerabilidades do equipamento --------------------------------------------


@rotas.get("/{equipamento_id}/vulnerabilidades")
async def listar_vulnerabilidades_do_equipamento(
    equipamento_id: int, servicos: Servicos
) -> List[VulnerabilidadeResposta]:
    """Lista as vulnerabilidades que afetam o equipamento (lista vazia se não
    houver nenhuma)."""
    servicos.equipamentos.buscar_por_id(equipamento_id)
    vulnerabilidades = servicos.vulnerabilidades.listar_por_equipamento(equipamento_id)
    return [vulnerabilidade_para_resposta(v, servicos) for v in vulnerabilidades]


@rotas.get("/{equipamento_id}/vulnerabilidades-exclusivas")
async def listar_vulnerabilidades_exclusivas(
    equipamento_id: int, servicos: Servicos
) -> List[VulnerabilidadeResposta]:
    """Lista as vulnerabilidades que afetam só este equipamento, ou seja, as
    que serão excluídas junto com ele."""
    servicos.equipamentos.buscar_por_id(equipamento_id)
    exclusivas = servicos.vulnerabilidades.listar_exclusivas_do_equipamento(
        equipamento_id
    )
    return [vulnerabilidade_para_resposta(v, servicos) for v in exclusivas]


@rotas.post("/{equipamento_id}/vulnerabilidades/{vulnerabilidade_id}", status_code=204)
async def atribuir_vulnerabilidade(
    equipamento_id: int, vulnerabilidade_id: int, servicos: Servicos
) -> None:
    """Registra que a vulnerabilidade afeta o equipamento."""
    servicos.vulnerabilidades.associar(vulnerabilidade_id, equipamento_id)


@rotas.delete(
    "/{equipamento_id}/vulnerabilidades/{vulnerabilidade_id}", status_code=204
)
async def remover_vulnerabilidade(
    equipamento_id: int, vulnerabilidade_id: int, servicos: Servicos
) -> None:
    """Remove a vulnerabilidade do equipamento. Ela continua no catálogo."""
    servicos.vulnerabilidades.desassociar(vulnerabilidade_id, equipamento_id)

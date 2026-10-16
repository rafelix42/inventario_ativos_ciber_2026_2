"""Regras de negócio relacionadas às vulnerabilidades de um equipamento.

Assim como o EquipamentoService, esta classe mantém as vulnerabilidades em cache
usando dicionários: um indexado pelo id do equipamento (para listar rapidamente
as vulnerabilidades de um equipamento específico) e outro indexado pelo id da
própria vulnerabilidade (para localizar um registro rapidamente na hora de
editar ou excluir).
"""

import logging
from typing import Dict, List

from app.exceptions import ErroDeValidacao, VulnerabilidadeNaoEncontradaError
from app.models.enums import StatusVulnerabilidade
from app.models.vulnerabilidade import Vulnerabilidade
from app.repositories.vulnerabilidade_repository import VulnerabilidadeRepository
from app.services.validacao import validar_apenas_letras

logger = logging.getLogger(__name__)

NOTA_CVSS_MINIMA = 0.0
NOTA_CVSS_MAXIMA = 10.0


class VulnerabilidadeService:
    """Regras de negócio para cadastro, edição e exclusão de vulnerabilidades."""

    def __init__(self, repositorio_de_vulnerabilidades: VulnerabilidadeRepository):
        self._repositorio = repositorio_de_vulnerabilidades
        self._vulnerabilidades_por_id: Dict[int, Vulnerabilidade] = {}
        self._vulnerabilidades_por_equipamento: Dict[int, List[Vulnerabilidade]] = {}
        self._recarregar_cache_a_partir_do_banco()

    def _recarregar_cache_a_partir_do_banco(self) -> None:
        self._vulnerabilidades_por_id = {}
        self._vulnerabilidades_por_equipamento = {}

        for vulnerabilidade in self._repositorio.listar_todas():
            self._indexar_vulnerabilidade_no_cache(vulnerabilidade)

    def _indexar_vulnerabilidade_no_cache(
        self, vulnerabilidade: Vulnerabilidade
    ) -> None:
        self._vulnerabilidades_por_id[vulnerabilidade.id] = vulnerabilidade
        self._vulnerabilidades_por_equipamento.setdefault(
            vulnerabilidade.equipamento_id, []
        ).append(vulnerabilidade)

    def listar_por_equipamento(self, equipamento_id: int) -> List[Vulnerabilidade]:
        """Retorna as vulnerabilidades de um equipamento (lista vazia se não houver)."""
        return list(self._vulnerabilidades_por_equipamento.get(equipamento_id, []))

    def cadastrar(
        self,
        equipamento_id: int,
        descricao: str,
        categoria: str,
        nota_cvss: float,
        status: StatusVulnerabilidade,
    ) -> Vulnerabilidade:
        """Valida e cadastra uma nova vulnerabilidade para um equipamento.

        A severidade não é informada pelo usuário: ela é classificada
        automaticamente a partir da nota CVSS (ver Severidade.a_partir_da_nota_cvss).
        """
        self._validar_campos_obrigatorios(descricao=descricao, categoria=categoria)
        validar_apenas_letras(
            logger, "vulnerabilidade", descricao=descricao, categoria=categoria
        )
        self._validar_nota_cvss(nota_cvss)
        self._validar_status(status)

        nova_vulnerabilidade = Vulnerabilidade(
            equipamento_id=equipamento_id,
            descricao=descricao.strip(),
            categoria=categoria.strip(),
            nota_cvss=float(nota_cvss),
            status=status,
        )
        nova_vulnerabilidade = self._repositorio.inserir(nova_vulnerabilidade)
        self._indexar_vulnerabilidade_no_cache(nova_vulnerabilidade)
        logger.info(
            "Vulnerabilidade cadastrada: id=%s equipamento_id=%s descricao=%r "
            "categoria=%r nota_cvss=%.1f severidade=%s status=%s",
            nova_vulnerabilidade.id,
            nova_vulnerabilidade.equipamento_id,
            nova_vulnerabilidade.descricao,
            nova_vulnerabilidade.categoria,
            nova_vulnerabilidade.nota_cvss,
            nova_vulnerabilidade.severidade.name,
            nova_vulnerabilidade.status.name,
        )
        return nova_vulnerabilidade

    def atualizar(
        self,
        vulnerabilidade_id: int,
        descricao: str,
        categoria: str,
        nota_cvss: float,
        status: StatusVulnerabilidade,
    ) -> Vulnerabilidade:
        """Valida e atualiza uma vulnerabilidade já cadastrada."""
        vulnerabilidade_existente = self._buscar_por_id(vulnerabilidade_id)
        self._validar_campos_obrigatorios(descricao=descricao, categoria=categoria)
        validar_apenas_letras(
            logger, "vulnerabilidade", descricao=descricao, categoria=categoria
        )
        self._validar_nota_cvss(nota_cvss)
        self._validar_status(status)

        valores_antes_da_alteracao = (
            f"nota_cvss={vulnerabilidade_existente.nota_cvss:.1f} "
            f"severidade={vulnerabilidade_existente.severidade.name} "
            f"status={vulnerabilidade_existente.status.name}"
        )

        vulnerabilidade_existente.descricao = descricao.strip()
        vulnerabilidade_existente.categoria = categoria.strip()
        vulnerabilidade_existente.nota_cvss = float(nota_cvss)
        vulnerabilidade_existente.status = status

        self._repositorio.atualizar(vulnerabilidade_existente)
        logger.info(
            "Vulnerabilidade atualizada: id=%s equipamento_id=%s | antes: %s | "
            "depois: nota_cvss=%.1f severidade=%s status=%s",
            vulnerabilidade_existente.id,
            vulnerabilidade_existente.equipamento_id,
            valores_antes_da_alteracao,
            vulnerabilidade_existente.nota_cvss,
            vulnerabilidade_existente.severidade.name,
            vulnerabilidade_existente.status.name,
        )
        return vulnerabilidade_existente

    def excluir(self, vulnerabilidade_id: int) -> None:
        """Exclui uma vulnerabilidade do banco de dados e do cache em memória."""
        vulnerabilidade = self._buscar_por_id(vulnerabilidade_id)

        self._repositorio.excluir(vulnerabilidade_id)
        del self._vulnerabilidades_por_id[vulnerabilidade_id]
        self._vulnerabilidades_por_equipamento[vulnerabilidade.equipamento_id].remove(
            vulnerabilidade
        )
        logger.info(
            "Vulnerabilidade excluída: id=%s equipamento_id=%s descricao=%r",
            vulnerabilidade.id,
            vulnerabilidade.equipamento_id,
            vulnerabilidade.descricao,
        )

    def esquecer_vulnerabilidades_do_equipamento(self, equipamento_id: int) -> None:
        """Remove do cache as vulnerabilidades de um equipamento recém-excluído.

        A exclusão das linhas no banco de dados já é feita automaticamente
        pelo SQLite (ON DELETE CASCADE); este método apenas mantém o cache
        em memória consistente com o banco.
        """
        vulnerabilidades_removidas = self._vulnerabilidades_por_equipamento.pop(
            equipamento_id, []
        )
        for vulnerabilidade in vulnerabilidades_removidas:
            self._vulnerabilidades_por_id.pop(vulnerabilidade.id, None)

        if vulnerabilidades_removidas:
            logger.info(
                "%s vulnerabilidade(s) do equipamento_id=%s removida(s) em cascata.",
                len(vulnerabilidades_removidas),
                equipamento_id,
            )

    def _buscar_por_id(self, vulnerabilidade_id: int) -> Vulnerabilidade:
        vulnerabilidade = self._vulnerabilidades_por_id.get(vulnerabilidade_id)
        if vulnerabilidade is None:
            logger.warning(
                "Busca por ID falhou: nenhuma vulnerabilidade encontrada com id=%s.",
                vulnerabilidade_id,
            )
            raise VulnerabilidadeNaoEncontradaError(
                f"Não existe vulnerabilidade cadastrada com o ID {vulnerabilidade_id}."
            )
        return vulnerabilidade

    @staticmethod
    def _validar_campos_obrigatorios(**campos: str) -> None:
        for nome_do_campo, valor in campos.items():
            if valor is None or not str(valor).strip():
                logger.warning(
                    "Validação de vulnerabilidade falhou: "
                    "campo obrigatório '%s' não foi informado.",
                    nome_do_campo,
                )
                raise ErroDeValidacao(f"O campo '{nome_do_campo}' é obrigatório.")

    @staticmethod
    def _validar_nota_cvss(nota_cvss: float) -> None:
        if isinstance(nota_cvss, bool) or not isinstance(nota_cvss, (int, float)):
            logger.warning(
                "Validação de vulnerabilidade falhou: nota CVSS não numérica (%r).",
                nota_cvss,
            )
            raise ErroDeValidacao("Informe a nota CVSS como um número.")

        if not NOTA_CVSS_MINIMA <= nota_cvss <= NOTA_CVSS_MAXIMA:
            logger.warning(
                "Validação de vulnerabilidade falhou: nota CVSS fora da faixa (%r).",
                nota_cvss,
            )
            raise ErroDeValidacao(
                f"A nota CVSS deve estar entre {NOTA_CVSS_MINIMA:.1f} "
                f"e {NOTA_CVSS_MAXIMA:.1f}."
            )

    @staticmethod
    def _validar_status(status: StatusVulnerabilidade) -> None:
        if not isinstance(status, StatusVulnerabilidade):
            logger.warning(
                "Validação de vulnerabilidade falhou: status inválido (%r).", status
            )
            raise ErroDeValidacao("Selecione um status válido.")

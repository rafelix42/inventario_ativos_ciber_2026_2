"""Regras de negócio relacionadas às vulnerabilidades e às suas associações
com equipamentos.

Uma vulnerabilidade existe independentemente dos equipamentos e pode afetar
vários deles. Assim como o EquipamentoService, esta classe mantém um cache
em dicionários: um indexado pelo id da vulnerabilidade (para localizar um
registro rapidamente) e dois índices das associações, nos dois sentidos
(vulnerabilidades de um equipamento e equipamentos afetados por uma
vulnerabilidade).
"""

import logging
import sqlite3
from typing import Dict, List, Set

from app.exceptions import (
    EquipamentoNaoEncontradoError,
    ErroDeValidacao,
    VulnerabilidadeNaoEncontradaError,
)
from app.models.enums import StatusVulnerabilidade
from app.models.vulnerabilidade import Vulnerabilidade
from app.repositories.vulnerabilidade_repository import VulnerabilidadeRepository
from app.services.validacao import validar_apenas_letras, validar_letras_e_numeros

logger = logging.getLogger(__name__)

NOTA_CVSS_MINIMA = 0.0
NOTA_CVSS_MAXIMA = 10.0


class VulnerabilidadeService:
    """Regras de negócio para cadastro, edição, exclusão e associação de
    vulnerabilidades."""

    def __init__(self, repositorio_de_vulnerabilidades: VulnerabilidadeRepository):
        self._repositorio = repositorio_de_vulnerabilidades
        self._vulnerabilidades_por_id: Dict[int, Vulnerabilidade] = {}
        self._vulnerabilidades_por_equipamento: Dict[int, Set[int]] = {}
        self._equipamentos_por_vulnerabilidade: Dict[int, Set[int]] = {}
        self._recarregar_cache_a_partir_do_banco()

    def _recarregar_cache_a_partir_do_banco(self) -> None:
        self._vulnerabilidades_por_id = {
            vulnerabilidade.id: vulnerabilidade
            for vulnerabilidade in self._repositorio.listar_todas()
        }
        self._vulnerabilidades_por_equipamento = {}
        self._equipamentos_por_vulnerabilidade = {}
        for (
            equipamento_id,
            vulnerabilidade_id,
        ) in self._repositorio.listar_associacoes():
            self._indexar_associacao(equipamento_id, vulnerabilidade_id)

    def _indexar_associacao(self, equipamento_id: int, vulnerabilidade_id: int) -> None:
        self._vulnerabilidades_por_equipamento.setdefault(equipamento_id, set()).add(
            vulnerabilidade_id
        )
        self._equipamentos_por_vulnerabilidade.setdefault(
            vulnerabilidade_id, set()
        ).add(equipamento_id)

    # --- Consultas -------------------------------------------------------

    def listar_todas(self) -> List[Vulnerabilidade]:
        """Retorna todas as vulnerabilidades cadastradas, ordenadas por id."""
        return sorted(
            self._vulnerabilidades_por_id.values(),
            key=lambda vulnerabilidade: vulnerabilidade.id,
        )

    def buscar_por_id(self, vulnerabilidade_id: int) -> Vulnerabilidade:
        """Busca uma vulnerabilidade pelo identificador único, usando o cache."""
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

    def listar_por_equipamento(self, equipamento_id: int) -> List[Vulnerabilidade]:
        """Retorna as vulnerabilidades que afetam um equipamento (lista vazia se
        não houver), ordenadas por id."""
        ids = self._vulnerabilidades_por_equipamento.get(equipamento_id, set())
        return [self._vulnerabilidades_por_id[id_] for id_ in sorted(ids)]

    def listar_ids_de_equipamentos_afetados(self, vulnerabilidade_id: int) -> List[int]:
        """Retorna os ids dos equipamentos afetados por uma vulnerabilidade."""
        self.buscar_por_id(vulnerabilidade_id)
        return sorted(
            self._equipamentos_por_vulnerabilidade.get(vulnerabilidade_id, set())
        )

    def listar_exclusivas_do_equipamento(
        self, equipamento_id: int
    ) -> List[Vulnerabilidade]:
        """Retorna as vulnerabilidades que afetam apenas este equipamento, ou
        seja, as que serão excluídas junto com ele."""
        return [
            vulnerabilidade
            for vulnerabilidade in self.listar_por_equipamento(equipamento_id)
            if self._equipamentos_por_vulnerabilidade[vulnerabilidade.id]
            == {equipamento_id}
        ]

    # --- CRUD --------------------------------------------------------------

    def cadastrar(
        self,
        descricao: str,
        categoria: str,
        nota_cvss: float,
        status: StatusVulnerabilidade,
    ) -> Vulnerabilidade:
        """Valida e cadastra uma nova vulnerabilidade (ainda sem equipamentos).

        A severidade não é informada pelo usuário: ela é classificada
        automaticamente a partir da nota CVSS (ver Severidade.a_partir_da_nota_cvss).
        """
        self._validar_campos(descricao, categoria, nota_cvss, status)

        nova_vulnerabilidade = Vulnerabilidade(
            descricao=descricao.strip(),
            categoria=categoria.strip(),
            nota_cvss=float(nota_cvss),
            status=status,
        )
        nova_vulnerabilidade = self._repositorio.inserir(nova_vulnerabilidade)
        self._vulnerabilidades_por_id[nova_vulnerabilidade.id] = nova_vulnerabilidade
        logger.info(
            "Vulnerabilidade cadastrada: id=%s descricao=%r categoria=%r "
            "nota_cvss=%.1f severidade=%s status=%s",
            nova_vulnerabilidade.id,
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
        vulnerabilidade_existente = self.buscar_por_id(vulnerabilidade_id)
        self._validar_campos(descricao, categoria, nota_cvss, status)

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
            "Vulnerabilidade atualizada: id=%s | antes: %s | "
            "depois: nota_cvss=%.1f severidade=%s status=%s",
            vulnerabilidade_existente.id,
            valores_antes_da_alteracao,
            vulnerabilidade_existente.nota_cvss,
            vulnerabilidade_existente.severidade.name,
            vulnerabilidade_existente.status.name,
        )
        return vulnerabilidade_existente

    def excluir(self, vulnerabilidade_id: int) -> None:
        """Exclui uma vulnerabilidade e todas as suas associações com
        equipamentos, do banco de dados e do cache em memória."""
        vulnerabilidade = self.buscar_por_id(vulnerabilidade_id)

        self._repositorio.excluir(vulnerabilidade_id)
        del self._vulnerabilidades_por_id[vulnerabilidade_id]
        equipamentos_afetados = self._equipamentos_por_vulnerabilidade.pop(
            vulnerabilidade_id, set()
        )
        for equipamento_id in equipamentos_afetados:
            self._vulnerabilidades_por_equipamento[equipamento_id].discard(
                vulnerabilidade_id
            )
        logger.info(
            "Vulnerabilidade excluída: id=%s descricao=%r equipamentos_afetados=%s",
            vulnerabilidade.id,
            vulnerabilidade.descricao,
            sorted(equipamentos_afetados),
        )

    # --- Associações com equipamentos -----------------------------------

    def associar(self, vulnerabilidade_id: int, equipamento_id: int) -> None:
        """Registra que a vulnerabilidade afeta o equipamento."""
        self.buscar_por_id(vulnerabilidade_id)
        if equipamento_id in self._equipamentos_por_vulnerabilidade.get(
            vulnerabilidade_id, set()
        ):
            logger.warning(
                "Associação falhou: vulnerabilidade_id=%s já afeta equipamento_id=%s.",
                vulnerabilidade_id,
                equipamento_id,
            )
            raise ErroDeValidacao(
                "Esta vulnerabilidade já está atribuída a este equipamento."
            )

        try:
            self._repositorio.associar(equipamento_id, vulnerabilidade_id)
        except sqlite3.IntegrityError as erro:
            logger.warning(
                "Associação falhou: equipamento_id=%s não existe.", equipamento_id
            )
            raise EquipamentoNaoEncontradoError(
                f"Não existe equipamento cadastrado com o ID {equipamento_id}."
            ) from erro

        self._indexar_associacao(equipamento_id, vulnerabilidade_id)
        logger.info(
            "Vulnerabilidade atribuída: vulnerabilidade_id=%s equipamento_id=%s",
            vulnerabilidade_id,
            equipamento_id,
        )

    def desassociar(self, vulnerabilidade_id: int, equipamento_id: int) -> None:
        """Remove a associação entre a vulnerabilidade e o equipamento.

        A vulnerabilidade continua cadastrada, mesmo que não afete mais
        nenhum equipamento.
        """
        self.buscar_por_id(vulnerabilidade_id)
        equipamentos_afetados = self._equipamentos_por_vulnerabilidade.get(
            vulnerabilidade_id, set()
        )
        if equipamento_id not in equipamentos_afetados:
            logger.warning(
                "Desassociação falhou: vulnerabilidade_id=%s não afeta "
                "equipamento_id=%s.",
                vulnerabilidade_id,
                equipamento_id,
            )
            raise ErroDeValidacao(
                "Esta vulnerabilidade não está atribuída a este equipamento."
            )

        self._repositorio.desassociar(equipamento_id, vulnerabilidade_id)
        equipamentos_afetados.discard(equipamento_id)
        self._vulnerabilidades_por_equipamento[equipamento_id].discard(
            vulnerabilidade_id
        )
        logger.info(
            "Vulnerabilidade removida do equipamento: vulnerabilidade_id=%s "
            "equipamento_id=%s",
            vulnerabilidade_id,
            equipamento_id,
        )

    def sincronizar_apos_exclusao_de_equipamento(
        self, equipamento_id: int
    ) -> List[Vulnerabilidade]:
        """Atualiza o cache depois que um equipamento foi excluído.

        A exclusão no banco já é feita pelo SQLite: as associações do
        equipamento são removidas (ON DELETE CASCADE) e as vulnerabilidades
        que só afetavam ele são excluídas (trigger 'excluir_vulnerabilidades_orfas').
        Retorna as vulnerabilidades que foram excluídas junto com o equipamento.
        """
        vulnerabilidades_excluidas = self.listar_exclusivas_do_equipamento(
            equipamento_id
        )
        self._recarregar_cache_a_partir_do_banco()

        if vulnerabilidades_excluidas:
            logger.info(
                "%s vulnerabilidade(s) exclusiva(s) do equipamento_id=%s "
                "removida(s) em cascata: ids=%s",
                len(vulnerabilidades_excluidas),
                equipamento_id,
                [vulnerabilidade.id for vulnerabilidade in vulnerabilidades_excluidas],
            )
        return vulnerabilidades_excluidas

    # --- Validações -------------------------------------------------------

    def _validar_campos(
        self,
        descricao: str,
        categoria: str,
        nota_cvss: float,
        status: StatusVulnerabilidade,
    ) -> None:
        self._validar_campos_obrigatorios(descricao=descricao, categoria=categoria)
        validar_letras_e_numeros(logger, "vulnerabilidade", descricao=descricao)
        validar_apenas_letras(logger, "vulnerabilidade", categoria=categoria)
        self._validar_nota_cvss(nota_cvss)
        self._validar_status(status)

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

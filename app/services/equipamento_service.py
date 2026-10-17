"""Regras de negócio relacionadas aos equipamentos de TI.

Além de validar os dados e delegar a gravação ao repositório, esta classe
mantém um cache em memória (um dicionário, indexado pelo id do equipamento)
com todos os equipamentos cadastrados. Isso evita ter que consultar o banco
de dados toda vez que a interface precisa listar ou buscar um equipamento,
otimizando as buscas conforme pedido nos requisitos RF10/RNF05.
"""

import logging
from typing import Dict, List, Type

from app.exceptions import EquipamentoNaoEncontradoError, ErroDeValidacao
from app.models.equipamento import TIPOS_DE_EQUIPAMENTO, Equipamento
from app.repositories.equipamento_repository import EquipamentoRepository
from app.services.validacao import validar_apenas_letras, validar_letras_e_numeros

logger = logging.getLogger(__name__)


class EquipamentoService:
    """Regras de negócio para cadastro, busca, edição e exclusão de equipamentos."""

    def __init__(self, repositorio_de_equipamentos: EquipamentoRepository):
        self._repositorio = repositorio_de_equipamentos
        self._equipamentos_por_id: Dict[int, Equipamento] = {}
        self._recarregar_cache_a_partir_do_banco()

    def _recarregar_cache_a_partir_do_banco(self) -> None:
        equipamentos_cadastrados = self._repositorio.listar_todos()
        self._equipamentos_por_id = {
            equipamento.id: equipamento for equipamento in equipamentos_cadastrados
        }

    def listar_todos(self) -> List[Equipamento]:
        """Retorna todos os equipamentos cadastrados, ordenados por id."""
        return sorted(
            self._equipamentos_por_id.values(), key=lambda equipamento: equipamento.id
        )

    def buscar_por_id(self, equipamento_id: int) -> Equipamento:
        """Busca um equipamento pelo identificador único, usando o cache."""
        equipamento = self._equipamentos_por_id.get(equipamento_id)
        if equipamento is None:
            logger.warning(
                "Busca por ID falhou: nenhum equipamento encontrado com id=%s.",
                equipamento_id,
            )
            raise EquipamentoNaoEncontradoError(
                f"Não existe equipamento cadastrado com o ID {equipamento_id}."
            )
        return equipamento

    def buscar_por_nome(self, texto_buscado: str) -> List[Equipamento]:
        """Busca equipamentos cujo nome/hostname contenha o texto informado."""
        termo_normalizado = texto_buscado.strip().lower()
        if not termo_normalizado:
            return self.listar_todos()

        return [
            equipamento
            for equipamento in self._equipamentos_por_id.values()
            if termo_normalizado in equipamento.nome.lower()
        ]

    def cadastrar(
        self,
        nome: str,
        responsavel: str,
        setor: str,
        classe: Type[Equipamento],
        descricao: str = "",
    ) -> Equipamento:
        """Valida e cadastra um novo equipamento de TI.

        'classe' é a subclasse de Equipamento a ser criada (ex.: Servidor).
        """
        self._validar_campos_obrigatorios(
            nome=nome, responsavel=responsavel, setor=setor
        )
        validar_apenas_letras(logger, "equipamento", responsavel=responsavel)
        validar_letras_e_numeros(
            logger, "equipamento", nome=nome, setor=setor, descricao=descricao
        )
        self._validar_classe_de_equipamento(classe)

        novo_equipamento = classe(
            nome=nome.strip(),
            responsavel=responsavel.strip(),
            setor=setor.strip(),
            descricao=descricao.strip(),
        )
        novo_equipamento = self._repositorio.inserir(novo_equipamento)
        self._equipamentos_por_id[novo_equipamento.id] = novo_equipamento
        logger.info(
            "Equipamento cadastrado: id=%s nome=%r responsavel=%r setor=%r classe=%s",
            novo_equipamento.id,
            novo_equipamento.nome,
            novo_equipamento.responsavel,
            novo_equipamento.setor,
            type(novo_equipamento).__name__,
        )
        return novo_equipamento

    def atualizar(
        self,
        equipamento_id: int,
        responsavel: str,
        setor: str,
        classe: Type[Equipamento],
        descricao: str = "",
    ) -> Equipamento:
        """Valida e atualiza os dados de um equipamento já cadastrado.

        Como o tipo de um equipamento é a sua própria classe, trocar o tipo
        cria um novo objeto da classe escolhida, mantendo o mesmo id.
        """
        equipamento_existente = self.buscar_por_id(equipamento_id)
        self._validar_campos_obrigatorios(responsavel=responsavel, setor=setor)
        validar_apenas_letras(logger, "equipamento", responsavel=responsavel)
        validar_letras_e_numeros(
            logger, "equipamento", setor=setor, descricao=descricao
        )
        self._validar_classe_de_equipamento(classe)

        valores_antes_da_alteracao = (
            f"responsavel={equipamento_existente.responsavel!r} "
            f"setor={equipamento_existente.setor!r} "
            f"classe={type(equipamento_existente).__name__}"
        )

        equipamento_atualizado = classe(
            id=equipamento_existente.id,
            nome=equipamento_existente.nome,
            responsavel=responsavel.strip(),
            setor=setor.strip(),
            descricao=descricao.strip(),
        )

        self._repositorio.atualizar(equipamento_atualizado)
        self._equipamentos_por_id[equipamento_atualizado.id] = equipamento_atualizado
        logger.info(
            "Equipamento atualizado: id=%s | antes: %s | "
            "depois: responsavel=%r setor=%r classe=%s",
            equipamento_atualizado.id,
            valores_antes_da_alteracao,
            equipamento_atualizado.responsavel,
            equipamento_atualizado.setor,
            type(equipamento_atualizado).__name__,
        )
        return equipamento_atualizado

    def excluir(self, equipamento_id: int) -> None:
        """Exclui um equipamento do banco de dados (o banco remove em cascata as
        vulnerabilidades associadas a ele) e do cache em memória."""
        equipamento_a_ser_excluido = self.buscar_por_id(equipamento_id)
        self._repositorio.excluir(equipamento_id)
        del self._equipamentos_por_id[equipamento_id]
        logger.info(
            "Equipamento excluído: id=%s nome=%r "
            "(vulnerabilidades associadas removidas em cascata)",
            equipamento_a_ser_excluido.id,
            equipamento_a_ser_excluido.nome,
        )

    @staticmethod
    def _validar_campos_obrigatorios(**campos: str) -> None:
        for nome_do_campo, valor in campos.items():
            if valor is None or not str(valor).strip():
                logger.warning(
                    "Validação de equipamento falhou: "
                    "campo obrigatório '%s' não foi informado.",
                    nome_do_campo,
                )
                raise ErroDeValidacao(f"O campo '{nome_do_campo}' é obrigatório.")

    @staticmethod
    def _validar_classe_de_equipamento(classe: Type[Equipamento]) -> None:
        if classe not in TIPOS_DE_EQUIPAMENTO.values():
            logger.warning(
                "Validação de equipamento falhou: tipo de equipamento inválido (%r).",
                classe,
            )
            raise ErroDeValidacao("Selecione um tipo de equipamento válido.")

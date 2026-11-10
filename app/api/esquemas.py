"""Esquemas: o formato do JSON que a API recebe e devolve.

Cada classe abaixo (um modelo do Pydantic) descreve um corpo de requisição
ou de resposta. O FastAPI usa esses esquemas para:
    - converter o JSON recebido em objetos Python, recusando tipos errados
      (ex.: texto onde se espera número) com o status 422;
    - converter a resposta em JSON;
    - gerar a documentação interativa em /docs.

As regras de negócio (campos obrigatórios, caracteres permitidos, faixa da
nota CVSS, soma dos fatores...) continuam nos serviços (app/services). Os
esquemas só verificam o tipo de cada campo e se as opções escolhidas
(tipo de equipamento, status) existem.

Convenção de nomes: classes terminadas em 'Resposta' são devolvidas pela
API; as demais são corpos de requisição enviados pelo frontend.
"""

from typing import List

from pydantic import BaseModel, Field, field_validator

from app.models.dependencia import Dependencia
from app.models.enums import StatusVulnerabilidade
from app.models.equipamento import TIPOS_DE_EQUIPAMENTO, Equipamento
from app.models.vulnerabilidade import Vulnerabilidade
from app.services.analise_de_risco_service import ModeloDeRisco, RiscoDoEquipamento

# --- Opções fixas (para preencher listas de seleção no frontend) ----------


class TipoDeEquipamentoResposta(BaseModel):
    """Um tipo de equipamento que pode ser cadastrado."""

    classe: str = Field(description="Valor a enviar no campo 'classe'.")
    rotulo: str = Field(description="Nome para exibir na tela.")
    fator_de_exposicao: float


class OpcaoResposta(BaseModel):
    """Uma opção de um campo de valores fixos (ex.: status)."""

    valor: str = Field(description="Valor a enviar para a API.")
    rotulo: str = Field(description="Nome para exibir na tela.")


# --- Equipamentos ------------------------------------------------------------


class AtualizacaoDeEquipamento(BaseModel):
    """Campos que podem ser alterados em um equipamento (o nome não muda)."""

    responsavel: str
    setor: str
    classe: str = Field(
        description="Tipo do equipamento. Veja GET /api/tipos-de-equipamento.",
        examples=["Servidor"],
    )
    descricao: str = ""

    @field_validator("classe")
    @classmethod
    def _validar_classe(cls, classe: str) -> str:
        if classe not in TIPOS_DE_EQUIPAMENTO:
            opcoes = ", ".join(TIPOS_DE_EQUIPAMENTO)
            raise ValueError(f"tipo de equipamento inválido; use um destes: {opcoes}")
        return classe


class CadastroDeEquipamento(AtualizacaoDeEquipamento):
    """Dados para cadastrar um equipamento: os mesmos da atualização + nome."""

    nome: str


class EquipamentoResposta(BaseModel):
    """Equipamento devolvido pela API."""

    id: int
    nome: str
    responsavel: str
    setor: str
    descricao: str
    classe: str
    tipo: str = Field(description="Rótulo do tipo, para exibir na tela.")
    fator_de_exposicao: float
    quantidade_de_vulnerabilidades: int

    @classmethod
    def a_partir_do_modelo(
        cls, equipamento: Equipamento, quantidade_de_vulnerabilidades: int
    ) -> "EquipamentoResposta":
        """Converte o objeto Equipamento no formato de resposta da API."""
        return cls(
            id=equipamento.id,
            nome=equipamento.nome,
            responsavel=equipamento.responsavel,
            setor=equipamento.setor,
            descricao=equipamento.descricao,
            classe=type(equipamento).__name__,
            tipo=equipamento.ROTULO,
            fator_de_exposicao=equipamento.FATOR_DE_EXPOSICAO,
            quantidade_de_vulnerabilidades=quantidade_de_vulnerabilidades,
        )


class ExclusaoDeEquipamentoResposta(BaseModel):
    """Resultado da exclusão de um equipamento."""

    ids_das_vulnerabilidades_excluidas: List[int] = Field(
        description="Vulnerabilidades que afetavam só este equipamento e "
        "foram excluídas junto com ele."
    )


# --- Vulnerabilidades --------------------------------------------------------


class DadosDaVulnerabilidade(BaseModel):
    """Dados para cadastrar ou atualizar uma vulnerabilidade."""

    descricao: str
    categoria: str
    nota_cvss: float = Field(description="Nota CVSS de 0.0 a 10.0.", examples=[7.5])
    status: str = Field(
        description="Veja GET /api/status-de-vulnerabilidade.", examples=["ABERTA"]
    )

    @field_validator("status")
    @classmethod
    def _validar_status(cls, status: str) -> str:
        if status not in StatusVulnerabilidade.__members__:
            opcoes = ", ".join(StatusVulnerabilidade.__members__)
            raise ValueError(f"status inválido; use um destes: {opcoes}")
        return status


class VulnerabilidadeResposta(BaseModel):
    """Vulnerabilidade devolvida pela API."""

    id: int
    descricao: str
    categoria: str
    nota_cvss: float
    severidade: str = Field(description="Calculada a partir da nota CVSS.")
    status: str
    ids_dos_equipamentos_afetados: List[int]

    @classmethod
    def a_partir_do_modelo(
        cls, vulnerabilidade: Vulnerabilidade, ids_dos_equipamentos_afetados: List[int]
    ) -> "VulnerabilidadeResposta":
        """Converte o objeto Vulnerabilidade no formato de resposta da API."""
        return cls(
            id=vulnerabilidade.id,
            descricao=vulnerabilidade.descricao,
            categoria=vulnerabilidade.categoria,
            nota_cvss=vulnerabilidade.nota_cvss,
            severidade=vulnerabilidade.severidade.name,
            status=vulnerabilidade.status.name,
            ids_dos_equipamentos_afetados=ids_dos_equipamentos_afetados,
        )


# --- Dependências ------------------------------------------------------------


class FatorDaDependencia(BaseModel):
    """Fator de uma dependência: fração do risco herdada, no intervalo [0, 1)."""

    fator: float = Field(examples=[0.3])


class DependenciaResposta(BaseModel):
    """Dependência entre dois equipamentos (um elemento da matriz A)."""

    equipamento_id: int = Field(description="Equipamento que depende (linha i).")
    depende_de_id: int = Field(description="Equipamento do qual ele depende (j).")
    fator: float

    @classmethod
    def a_partir_do_modelo(cls, dependencia: Dependencia) -> "DependenciaResposta":
        """Converte o objeto Dependencia no formato de resposta da API."""
        return cls(
            equipamento_id=dependencia.equipamento_id,
            depende_de_id=dependencia.depende_de_id,
            fator=dependencia.fator,
        )


# --- Análise de risco --------------------------------------------------------


class RiscoDoEquipamentoResposta(BaseModel):
    """Risco próprio e efetivo de um equipamento."""

    equipamento_id: int
    nome: str
    tipo: str
    fator_de_exposicao: float
    risco_proprio: float = Field(description="b[i] = f[i] * (M @ v)[i]")
    risco_herdado: float = Field(description="Parte vinda das dependências.")
    risco_efetivo: float = Field(description="x[i], solução de (I - A) x = b")

    @classmethod
    def a_partir_do_modelo(
        cls, risco: RiscoDoEquipamento
    ) -> "RiscoDoEquipamentoResposta":
        """Converte o resultado da análise de um equipamento em resposta."""
        return cls(
            equipamento_id=risco.equipamento.id,
            nome=risco.equipamento.nome,
            tipo=risco.equipamento.ROTULO,
            fator_de_exposicao=risco.equipamento.FATOR_DE_EXPOSICAO,
            risco_proprio=risco.risco_proprio,
            risco_herdado=risco.risco_herdado,
            risco_efetivo=risco.risco_efetivo,
        )


class AnaliseDeRiscoResposta(BaseModel):
    """Resultado da análise de todos os equipamentos."""

    determinante: float = Field(description="det(I - A)")
    numero_de_condicao: float = Field(description="Número de condição de (I - A).")
    riscos: List[RiscoDoEquipamentoResposta] = Field(
        description="Ordenados do maior para o menor risco efetivo."
    )


class MatrizesDoModeloResposta(BaseModel):
    """Matrizes e vetores do modelo, como listas (linhas de listas)."""

    ids_dos_equipamentos: List[int] = Field(
        description="Ordem das linhas de M e de A, e das colunas de A."
    )
    ids_das_vulnerabilidades: List[int] = Field(
        description="Ordem das colunas de M e dos elementos de v."
    )
    matriz_de_incidencia: List[List[float]] = Field(description="M (n x m)")
    vetor_de_severidade: List[float] = Field(description="v (m)")
    vetor_de_exposicao: List[float] = Field(description="f (n)")
    matriz_de_dependencias: List[List[float]] = Field(description="A (n x n)")

    @classmethod
    def a_partir_do_modelo(cls, modelo: ModeloDeRisco) -> "MatrizesDoModeloResposta":
        """Converte as matrizes do NumPy em listas, que viram arrays em JSON."""
        return cls(
            ids_dos_equipamentos=[e.id for e in modelo.equipamentos],
            ids_das_vulnerabilidades=[v.id for v in modelo.vulnerabilidades],
            matriz_de_incidencia=modelo.matriz_de_incidencia.tolist(),
            vetor_de_severidade=modelo.vetor_de_severidade.tolist(),
            vetor_de_exposicao=modelo.vetor_de_exposicao.tolist(),
            matriz_de_dependencias=modelo.matriz_de_dependencias.tolist(),
        )

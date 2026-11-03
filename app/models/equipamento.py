"""Modelos que representam os equipamentos de TI cadastrados no inventário.

'Equipamento' reúne os dados comuns a qualquer equipamento. Cada tipo de
equipamento (servidor, roteador, switch, etc.) é uma subclasse dele: o tipo
de um equipamento é a própria classe do objeto, e não um campo separado.
"""

from dataclasses import dataclass
from typing import ClassVar, Dict, Optional, Type


@dataclass
class Equipamento:
    """Dados comuns a todo equipamento de TI.

    Não deve ser instanciada diretamente: todo equipamento cadastrado é de
    uma das subclasses abaixo. O campo 'id' é opcional porque só é
    preenchido depois que o equipamento é gravado no banco de dados (o
    SQLite gera o identificador único).
    """

    ROTULO: ClassVar[str] = "Equipamento"

    # Peso aplicado ao risco próprio do equipamento na análise de risco
    # (app/services/analise_de_risco_service.py). Cada subclasse redefine o
    # seu valor: tipos mais expostos a ataques (ex.: Firewall, de frente para
    # a internet) têm fator maior que 1; tipos menos expostos, menor que 1.
    FATOR_DE_EXPOSICAO: ClassVar[float] = 1.0

    nome: str
    responsavel: str
    setor: str
    descricao: str = ""
    id: Optional[int] = None


@dataclass
class EstacaoDeTrabalho(Equipamento):
    """Computador de mesa usado por um colaborador."""

    ROTULO = "Estação de Trabalho"
    FATOR_DE_EXPOSICAO = 1.0


@dataclass
class Notebook(Equipamento):
    """Computador portátil."""

    ROTULO = "Notebook"
    FATOR_DE_EXPOSICAO = 1.1


@dataclass
class Servidor(Equipamento):
    """Servidor físico ou virtual."""

    ROTULO = "Servidor"
    FATOR_DE_EXPOSICAO = 1.2


@dataclass
class BancoDeDados(Equipamento):
    """Servidor ou instância de banco de dados."""

    ROTULO = "Banco de Dados"
    FATOR_DE_EXPOSICAO = 1.3


@dataclass
class SoftwareLicenciado(Equipamento):
    """Software cuja licença de uso é controlada pelo inventário."""

    ROTULO = "Software Licenciado"
    FATOR_DE_EXPOSICAO = 0.9


@dataclass
class Impressora(Equipamento):
    """Impressora ou multifuncional."""

    ROTULO = "Impressora"
    FATOR_DE_EXPOSICAO = 0.8


@dataclass
class Roteador(Equipamento):
    """Roteador de rede."""

    ROTULO = "Roteador"
    FATOR_DE_EXPOSICAO = 1.3


@dataclass
class Switch(Equipamento):
    """Switch de rede."""

    ROTULO = "Switch"
    FATOR_DE_EXPOSICAO = 1.1


@dataclass
class Firewall(Equipamento):
    """Firewall de rede."""

    ROTULO = "Firewall"
    FATOR_DE_EXPOSICAO = 1.5


# Subclasses que podem ser cadastradas, indexadas pelo nome da classe. O
# nome da classe é o que fica gravado na coluna 'classe' do banco de dados.
TIPOS_DE_EQUIPAMENTO: Dict[str, Type[Equipamento]] = {
    classe.__name__: classe
    for classe in (
        EstacaoDeTrabalho,
        Notebook,
        Servidor,
        BancoDeDados,
        SoftwareLicenciado,
        Impressora,
        Roteador,
        Switch,
        Firewall,
    )
}

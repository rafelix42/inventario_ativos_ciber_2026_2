"""Modelo que representa uma vulnerabilidade de segurança."""

from dataclasses import dataclass
from typing import Optional

from app.models.enums import Severidade, StatusVulnerabilidade


@dataclass
class Vulnerabilidade:
    """Representa uma vulnerabilidade de segurança.

    A vulnerabilidade existe por si só: ela pode afetar vários equipamentos,
    e essa associação é guardada à parte (tabela 'equipamento_vulnerabilidade').
    O campo 'id' só é preenchido depois que o registro é gravado no banco.

    A severidade não é armazenada diretamente: o que é cadastrado e
    persistido no banco é a nota CVSS ('nota_cvss', de 0.0 a 10.0). O texto
    da severidade (Nenhuma/Baixa/Média/Alta/Crítica) é sempre calculado a
    partir dessa nota, então nunca fica desatualizado em relação a ela.
    """

    descricao: str
    categoria: str
    nota_cvss: float
    status: StatusVulnerabilidade
    id: Optional[int] = None

    @property
    def severidade(self) -> Severidade:
        """Classificação textual da severidade, calculada a partir da nota CVSS."""
        return Severidade.a_partir_da_nota_cvss(self.nota_cvss)

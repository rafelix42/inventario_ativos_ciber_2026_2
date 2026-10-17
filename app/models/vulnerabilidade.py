"""Modelo que representa uma vulnerabilidade associada a um equipamento de TI."""

from dataclasses import dataclass
from typing import Optional

from app.models.enums import Severidade, StatusVulnerabilidade


@dataclass
class Vulnerabilidade:
    """Representa uma vulnerabilidade encontrada em um equipamento específico.

    O campo 'equipamento_id' liga a vulnerabilidade ao equipamento dono dela. O campo
    'id' só é preenchido depois que o registro é gravado no banco de dados.

    A severidade não é armazenada diretamente: o que é cadastrado e
    persistido no banco é a nota CVSS ('nota_cvss', de 0.0 a 10.0). O texto
    da severidade (Nenhuma/Baixa/Média/Alta/Crítica) é sempre calculado a
    partir dessa nota, então nunca fica desatualizado em relação a ela.
    """

    equipamento_id: int
    descricao: str
    categoria: str
    nota_cvss: float
    status: StatusVulnerabilidade
    id: Optional[int] = None

    @property
    def severidade(self) -> Severidade:
        """Classificação textual da severidade, calculada a partir da nota CVSS."""
        return Severidade.a_partir_da_nota_cvss(self.nota_cvss)

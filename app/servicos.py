"""Cria e conecta todos os serviços da aplicação.

Fica em um único lugar para que o main.py e o seed_dados_teste.py montem os
serviços exatamente da mesma forma. Para adicionar um serviço novo, basta
criá-lo em 'criar_servicos' e incluí-lo em 'ServicosDaAplicacao'.
"""

from dataclasses import dataclass

from app.repositories.database import ConexaoBancoDeDados
from app.repositories.dependencia_repository import DependenciaRepository
from app.repositories.equipamento_repository import EquipamentoRepository
from app.repositories.vulnerabilidade_repository import VulnerabilidadeRepository
from app.services.analise_de_risco_service import AnaliseDeRiscoService
from app.services.dependencia_service import DependenciaService
from app.services.equipamento_service import EquipamentoService
from app.services.vulnerabilidade_service import VulnerabilidadeService


@dataclass
class ServicosDaAplicacao:
    """Agrupa os serviços já conectados ao banco de dados."""

    equipamentos: EquipamentoService
    vulnerabilidades: VulnerabilidadeService
    dependencias: DependenciaService
    analise_de_risco: AnaliseDeRiscoService


def criar_servicos(banco_de_dados: ConexaoBancoDeDados) -> ServicosDaAplicacao:
    """Cria os repositórios e os serviços sobre o banco de dados informado."""
    equipamentos = EquipamentoService(EquipamentoRepository(banco_de_dados))
    vulnerabilidades = VulnerabilidadeService(VulnerabilidadeRepository(banco_de_dados))
    dependencias = DependenciaService(
        DependenciaRepository(banco_de_dados), equipamentos
    )
    analise_de_risco = AnaliseDeRiscoService(
        equipamentos, vulnerabilidades, dependencias
    )
    return ServicosDaAplicacao(
        equipamentos, vulnerabilidades, dependencias, analise_de_risco
    )

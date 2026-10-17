"""Script utilitário para popular o banco de dados com dados fictícios.

Útil para testar a aplicação manualmente sem precisar cadastrar tudo pelo
menu no terminal. Reaproveita os mesmos serviços usados pela aplicação
principal, garantindo que os dados fictícios passem pelas mesmas validações
dos dados reais.

Uso:
    python3 seed_dados_teste.py
"""

from app.logging_config import configurar_logging
from app.models.enums import StatusVulnerabilidade
from app.models.equipamento import (
    EstacaoDeTrabalho,
    Firewall,
    Impressora,
    Roteador,
    Servidor,
    Switch,
)
from app.repositories.equipamento_repository import EquipamentoRepository
from app.repositories.database import ConexaoBancoDeDados
from app.repositories.vulnerabilidade_repository import VulnerabilidadeRepository
from app.services.equipamento_service import EquipamentoService
from app.services.vulnerabilidade_service import VulnerabilidadeService

EQUIPAMENTOS_FICTICIOS = [
    {
        "nome": "Servidor Banco de Dados",
        "responsavel": "Raphael Felix",
        "setor": "Data Center",
        "classe": Servidor,
        "descricao": "Servidor de banco de dados de produção com PostgreSQL",
        "vulnerabilidades": [
            {
                "descricao": "Senha padrão do administrador não foi alterada",
                "categoria": "Autenticação",
                "nota_cvss": 9.8,
                "status": StatusVulnerabilidade.ABERTA,
            },
            {
                "descricao": "Versão desatualizada do PostgreSQL com CVE conhecida",
                "categoria": "Software Desatualizado",
                "nota_cvss": 8.1,
                "status": StatusVulnerabilidade.EM_TRATAMENTO,
            },
        ],
    },
    {
        "nome": "Servidor Web",
        "responsavel": "Mariana Souza",
        "setor": "Data Center",
        "classe": Servidor,
        "descricao": "Servidor de aplicação web com Nginx e Gunicorn",
        "vulnerabilidades": [
            {
                "descricao": "Certificado TLS expirado",
                "categoria": "Criptografia",
                "nota_cvss": 5.3,
                "status": StatusVulnerabilidade.CORRIGIDA,
            },
        ],
    },
    {
        "nome": "Roteador de Borda",
        "responsavel": "Carlos Eduardo",
        "setor": "Sala de Telecom",
        "classe": Roteador,
        "descricao": "Roteador de borda que conecta a rede interna à internet",
        "vulnerabilidades": [
            {
                "descricao": "Interface de gerência exposta na internet",
                "categoria": "Configuração Insegura",
                "nota_cvss": 9.1,
                "status": StatusVulnerabilidade.ABERTA,
            },
        ],
    },
    {
        "nome": "Switch Core",
        "responsavel": "Carlos Eduardo",
        "setor": "Sala de Telecom",
        "classe": Switch,
        "descricao": "Switch principal do backbone da rede",
        "vulnerabilidades": [],
    },
    {
        "nome": "Firewall de Perímetro",
        "responsavel": "Ana Paula Lima",
        "setor": "Sala de Telecom",
        "classe": Firewall,
        "descricao": (
            "Firewall de perímetro responsável pelo filtro de tráfego externo"
        ),
        "vulnerabilidades": [
            {
                "descricao": "Regras de firewall permissivas demais",
                "categoria": "Configuração Insegura",
                "nota_cvss": 8.6,
                "status": StatusVulnerabilidade.EM_TRATAMENTO,
            },
            {
                "descricao": "Firmware desatualizado",
                "categoria": "Software Desatualizado",
                "nota_cvss": 4.3,
                "status": StatusVulnerabilidade.ACEITA_COMO_RISCO,
            },
        ],
    },
    {
        "nome": "Estação do RH",
        "responsavel": "Juliana Costa",
        "setor": "Recursos Humanos",
        "classe": EstacaoDeTrabalho,
        "descricao": "Estação de trabalho utilizada pela equipe de RH",
        "vulnerabilidades": [
            {
                "descricao": "Antivírus desatualizado há mais de noventa dias",
                "categoria": "Proteção de Endpoint",
                "nota_cvss": 2.4,
                "status": StatusVulnerabilidade.ABERTA,
            },
        ],
    },
    {
        "nome": "Impressora do Financeiro",
        "responsavel": "Juliana Costa",
        "setor": "Financeiro",
        "classe": Impressora,
        "descricao": "Impressora multifuncional compartilhada pelo setor financeiro",
        "vulnerabilidades": [],
    },
]


def popular_banco_com_dados_ficticios() -> None:
    """Cadastra equipamentos e vulnerabilidades fictícios, se o banco estiver vazio."""
    configurar_logging()
    banco_de_dados = ConexaoBancoDeDados()
    servico_de_equipamentos = EquipamentoService(EquipamentoRepository(banco_de_dados))
    servico_de_vulnerabilidades = VulnerabilidadeService(
        VulnerabilidadeRepository(banco_de_dados)
    )

    if servico_de_equipamentos.listar_todos():
        print(
            "O banco de dados já possui equipamentos cadastrados. "
            "Nenhum dado fictício foi inserido para evitar duplicidade."
        )
        banco_de_dados.fechar()
        return

    for dados_do_equipamento in EQUIPAMENTOS_FICTICIOS:
        equipamento_cadastrado = servico_de_equipamentos.cadastrar(
            nome=dados_do_equipamento["nome"],
            responsavel=dados_do_equipamento["responsavel"],
            setor=dados_do_equipamento["setor"],
            classe=dados_do_equipamento["classe"],
            descricao=dados_do_equipamento["descricao"],
        )

        for dados_da_vulnerabilidade in dados_do_equipamento["vulnerabilidades"]:
            servico_de_vulnerabilidades.cadastrar(
                equipamento_id=equipamento_cadastrado.id,
                descricao=dados_da_vulnerabilidade["descricao"],
                categoria=dados_da_vulnerabilidade["categoria"],
                nota_cvss=dados_da_vulnerabilidade["nota_cvss"],
                status=dados_da_vulnerabilidade["status"],
            )

        print(
            f"Equipamento '{equipamento_cadastrado.nome}' cadastrado "
            f"(ID {equipamento_cadastrado.id})."
        )

    print(
        f"\n{len(EQUIPAMENTOS_FICTICIOS)} equipamentos fictícios "
        "cadastrados com sucesso."
    )
    banco_de_dados.fechar()


if __name__ == "__main__":
    popular_banco_com_dados_ficticios()

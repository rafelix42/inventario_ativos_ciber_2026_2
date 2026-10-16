"""Script utilitário para popular o banco de dados com dados fictícios.

Útil para testar a aplicação manualmente sem precisar cadastrar tudo pela
interface gráfica. Reaproveita os mesmos serviços usados pela aplicação
principal, garantindo que os dados fictícios passem pelas mesmas validações
dos dados reais.

Uso:
    python3 seed_dados_teste.py
"""

from app.logging_config import configurar_logging
from app.models.enums import StatusVulnerabilidade, TipoAtivo
from app.repositories.ativo_repository import AtivoRepository
from app.repositories.database import ConexaoBancoDeDados
from app.repositories.vulnerabilidade_repository import VulnerabilidadeRepository
from app.services.ativo_service import AtivoService
from app.services.vulnerabilidade_service import VulnerabilidadeService

ATIVOS_FICTICIOS = [
    {
        "nome": "DB-Server-01",
        "responsavel": "Raphael Felix",
        "setor": "Data Center - Sala 1",
        "tipo": TipoAtivo.SERVIDOR,
        "descricao": "Servidor de banco de dados de produção (PostgreSQL).",
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
        "nome": "WEB-Server-02",
        "responsavel": "Mariana Souza",
        "setor": "Data Center - Sala 1",
        "tipo": TipoAtivo.SERVIDOR,
        "descricao": "Servidor de aplicação web (Nginx + Gunicorn).",
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
        "nome": "Roteador-Borda-01",
        "responsavel": "Carlos Eduardo",
        "setor": "Sala de Telecom",
        "tipo": TipoAtivo.ROTEADOR,
        "descricao": "Roteador de borda que conecta a rede interna à internet.",
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
        "nome": "Switch-Core-01",
        "responsavel": "Carlos Eduardo",
        "setor": "Sala de Telecom",
        "tipo": TipoAtivo.SWITCH,
        "descricao": "Switch principal do backbone da rede.",
        "vulnerabilidades": [],
    },
    {
        "nome": "Firewall-Perimetro-01",
        "responsavel": "Ana Paula Lima",
        "setor": "Sala de Telecom",
        "tipo": TipoAtivo.FIREWALL,
        "descricao": (
            "Firewall de perímetro responsável pelo filtro de tráfego externo."
        ),
        "vulnerabilidades": [
            {
                "descricao": "Regras de firewall permissivas demais (any-any)",
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
        "nome": "Estacao-RH-05",
        "responsavel": "Juliana Costa",
        "setor": "Recursos Humanos",
        "tipo": TipoAtivo.ESTACAO_DE_TRABALHO,
        "descricao": "Estação de trabalho utilizada pela equipe de RH.",
        "vulnerabilidades": [
            {
                "descricao": "Antivírus desatualizado há mais de 90 dias",
                "categoria": "Proteção de Endpoint",
                "nota_cvss": 2.4,
                "status": StatusVulnerabilidade.ABERTA,
            },
        ],
    },
    {
        "nome": "Impressora-Financeiro-01",
        "responsavel": "Juliana Costa",
        "setor": "Financeiro",
        "tipo": TipoAtivo.IMPRESSORA,
        "descricao": "Impressora multifuncional compartilhada pelo setor financeiro.",
        "vulnerabilidades": [],
    },
]


def popular_banco_com_dados_ficticios() -> None:
    """Cadastra os ativos e vulnerabilidades fictícios, se o banco estiver vazio."""
    configurar_logging()
    banco_de_dados = ConexaoBancoDeDados()
    servico_de_ativos = AtivoService(AtivoRepository(banco_de_dados))
    servico_de_vulnerabilidades = VulnerabilidadeService(
        VulnerabilidadeRepository(banco_de_dados)
    )

    if servico_de_ativos.listar_todos():
        print(
            "O banco de dados já possui ativos cadastrados. "
            "Nenhum dado fictício foi inserido para evitar duplicidade."
        )
        banco_de_dados.fechar()
        return

    for dados_do_ativo in ATIVOS_FICTICIOS:
        ativo_cadastrado = servico_de_ativos.cadastrar(
            nome=dados_do_ativo["nome"],
            responsavel=dados_do_ativo["responsavel"],
            setor=dados_do_ativo["setor"],
            tipo=dados_do_ativo["tipo"],
            descricao=dados_do_ativo["descricao"],
        )

        for dados_da_vulnerabilidade in dados_do_ativo["vulnerabilidades"]:
            servico_de_vulnerabilidades.cadastrar(
                ativo_id=ativo_cadastrado.id,
                descricao=dados_da_vulnerabilidade["descricao"],
                categoria=dados_da_vulnerabilidade["categoria"],
                nota_cvss=dados_da_vulnerabilidade["nota_cvss"],
                status=dados_da_vulnerabilidade["status"],
            )

        print(f"Ativo '{ativo_cadastrado.nome}' cadastrado (ID {ativo_cadastrado.id}).")

    print(f"\n{len(ATIVOS_FICTICIOS)} ativos fictícios cadastrados com sucesso.")
    banco_de_dados.fechar()


if __name__ == "__main__":
    popular_banco_com_dados_ficticios()

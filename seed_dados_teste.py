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
from app.repositories.database import ConexaoBancoDeDados
from app.servicos import criar_servicos

# Vulnerabilidades do catálogo, indexadas por uma chave usada abaixo para
# atribuí-las aos equipamentos. Uma mesma vulnerabilidade pode afetar
# vários equipamentos.
VULNERABILIDADES_FICTICIAS = {
    "senha_padrao": {
        "descricao": "Senha padrão do administrador não foi alterada",
        "categoria": "Autenticação",
        "nota_cvss": 9.8,
        "status": StatusVulnerabilidade.ABERTA,
    },
    "postgresql": {
        "descricao": "Versão desatualizada do PostgreSQL com CVE conhecida",
        "categoria": "Software Desatualizado",
        "nota_cvss": 8.1,
        "status": StatusVulnerabilidade.EM_TRATAMENTO,
    },
    "tls": {
        "descricao": "Certificado TLS expirado",
        "categoria": "Criptografia",
        "nota_cvss": 5.3,
        "status": StatusVulnerabilidade.CORRIGIDA,
    },
    "gerencia_exposta": {
        "descricao": "Interface de gerência exposta na internet",
        "categoria": "Configuração Insegura",
        "nota_cvss": 9.1,
        "status": StatusVulnerabilidade.ABERTA,
    },
    "regras_permissivas": {
        "descricao": "Regras de firewall permissivas demais",
        "categoria": "Configuração Insegura",
        "nota_cvss": 8.6,
        "status": StatusVulnerabilidade.EM_TRATAMENTO,
    },
    "firmware": {
        "descricao": "Firmware desatualizado",
        "categoria": "Software Desatualizado",
        "nota_cvss": 4.3,
        "status": StatusVulnerabilidade.ACEITA_COMO_RISCO,
    },
    "antivirus": {
        "descricao": "Antivírus desatualizado há mais de 90 dias",
        "categoria": "Proteção de Endpoint",
        "nota_cvss": 2.4,
        "status": StatusVulnerabilidade.ABERTA,
    },
}

EQUIPAMENTOS_FICTICIOS = [
    {
        "nome": "Servidor Banco de Dados 01",
        "responsavel": "Raphael Felix",
        "setor": "Data Center Sala 1",
        "classe": Servidor,
        "descricao": "Servidor de banco de dados de produção com PostgreSQL",
        "vulnerabilidades": ["senha_padrao", "postgresql", "tls"],
    },
    {
        "nome": "Servidor Web 02",
        "responsavel": "Mariana Souza",
        "setor": "Data Center Sala 1",
        "classe": Servidor,
        "descricao": "Servidor de aplicação web com Nginx e Gunicorn",
        "vulnerabilidades": ["tls"],
    },
    {
        "nome": "Roteador de Borda 01",
        "responsavel": "Carlos Eduardo",
        "setor": "Sala de Telecom",
        "classe": Roteador,
        "descricao": "Roteador de borda que conecta a rede interna à internet",
        "vulnerabilidades": ["gerencia_exposta", "firmware"],
    },
    {
        "nome": "Switch Core 01",
        "responsavel": "Carlos Eduardo",
        "setor": "Sala de Telecom",
        "classe": Switch,
        "descricao": "Switch principal do backbone da rede",
        "vulnerabilidades": ["firmware"],
    },
    {
        "nome": "Firewall de Perímetro 01",
        "responsavel": "Ana Paula Lima",
        "setor": "Sala de Telecom",
        "classe": Firewall,
        "descricao": "Firewall de perímetro responsável pelo filtro de tráfego externo",
        "vulnerabilidades": ["regras_permissivas", "firmware"],
    },
    {
        "nome": "Estação RH 05",
        "responsavel": "Juliana Costa",
        "setor": "Recursos Humanos",
        "classe": EstacaoDeTrabalho,
        "descricao": "Estação de trabalho utilizada pela equipe de RH",
        "vulnerabilidades": ["antivirus"],
    },
    {
        "nome": "Impressora Financeiro 01",
        "responsavel": "Juliana Costa",
        "setor": "Financeiro",
        "classe": Impressora,
        "descricao": "Impressora multifuncional compartilhada pelo setor financeiro",
        "vulnerabilidades": ["senha_padrao"],
    },
]

# Dependências entre equipamentos (matriz A da análise de risco), no formato
# (nome de quem depende, nome de quem ele depende, fator). A soma dos fatores
# de um mesmo equipamento deve ser menor que 1.
DEPENDENCIAS_FICTICIAS = [
    ("Servidor Web 02", "Servidor Banco de Dados 01", 0.4),
    ("Servidor Web 02", "Firewall de Perímetro 01", 0.2),
    ("Servidor Banco de Dados 01", "Switch Core 01", 0.2),
    ("Switch Core 01", "Firewall de Perímetro 01", 0.3),
    ("Firewall de Perímetro 01", "Roteador de Borda 01", 0.5),
    ("Estação RH 05", "Switch Core 01", 0.3),
    ("Estação RH 05", "Servidor Web 02", 0.2),
    ("Impressora Financeiro 01", "Switch Core 01", 0.1),
]


def popular_banco_com_dados_ficticios() -> None:
    """Cadastra equipamentos e vulnerabilidades fictícios, se o banco estiver vazio."""
    configurar_logging()
    banco_de_dados = ConexaoBancoDeDados()
    servicos = criar_servicos(banco_de_dados)
    servico_de_equipamentos = servicos.equipamentos
    servico_de_vulnerabilidades = servicos.vulnerabilidades
    servico_de_dependencias = servicos.dependencias

    if (
        servico_de_equipamentos.listar_todos()
        or servico_de_vulnerabilidades.listar_todas()
    ):
        print(
            "O banco de dados já possui dados cadastrados. "
            "Nenhum dado fictício foi inserido para evitar duplicidade."
        )
        banco_de_dados.fechar()
        return

    vulnerabilidades_por_chave = {
        chave: servico_de_vulnerabilidades.cadastrar(**dados)
        for chave, dados in VULNERABILIDADES_FICTICIAS.items()
    }

    ids_por_nome = {}
    for dados_do_equipamento in EQUIPAMENTOS_FICTICIOS:
        equipamento_cadastrado = servico_de_equipamentos.cadastrar(
            nome=dados_do_equipamento["nome"],
            responsavel=dados_do_equipamento["responsavel"],
            setor=dados_do_equipamento["setor"],
            classe=dados_do_equipamento["classe"],
            descricao=dados_do_equipamento["descricao"],
        )
        for chave in dados_do_equipamento["vulnerabilidades"]:
            servico_de_vulnerabilidades.associar(
                vulnerabilidades_por_chave[chave].id, equipamento_cadastrado.id
            )

        ids_por_nome[equipamento_cadastrado.nome] = equipamento_cadastrado.id
        print(
            f"Equipamento '{equipamento_cadastrado.nome}' cadastrado "
            f"(ID {equipamento_cadastrado.id})."
        )

    for nome, nome_de_quem_depende, fator in DEPENDENCIAS_FICTICIAS:
        servico_de_dependencias.salvar(
            ids_por_nome[nome], ids_por_nome[nome_de_quem_depende], fator
        )

    print(
        f"\n{len(EQUIPAMENTOS_FICTICIOS)} equipamentos, "
        f"{len(VULNERABILIDADES_FICTICIAS)} vulnerabilidades e "
        f"{len(DEPENDENCIAS_FICTICIAS)} dependências fictícios "
        "cadastrados com sucesso."
    )
    banco_de_dados.fechar()


if __name__ == "__main__":
    popular_banco_com_dados_ficticios()

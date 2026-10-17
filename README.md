# Inventário de Ativos de TI

Repositório para armazenar os códigos do projeto das sprints 1 e 2 do curso de Cibersegurança da UFU 2026-2 

Aluno: Raphael Felix

Aplicação de cadastro (CRUD) de equipamentos de TI e de suas vulnerabilidades,
com persistência em banco de dados **SQLite**, operada por um menu no
**terminal**.

## Como executar

Não há nenhuma dependência para instalar com `pip` — o projeto usa só
bibliotecas padrão do Python (veja `requirements.txt`).

```bash
python3 main.py
```

O programa abre um menu textual com todas as operações de CRUD de equipamentos
e vulnerabilidades (RNF08).

Na primeira execução, o arquivo de banco de dados `data/inventario.db` é
criado automaticamente com as tabelas necessárias.

## Estrutura do projeto

```
main.py                       # Ponto de entrada da aplicação
requirements.txt
seed_dados_teste.py           # Script utilitário para popular o banco com dados fictícios
data/                         # Banco de dados SQLite (gerado em tempo de execução)
logs/                         # Log de auditoria (gerado em tempo de execução)
tests/                        # Testes automatizados (unittest) do CRUD de equipamentos e vulnerabilidades
app/
├── exceptions.py             # Exceções personalizadas da aplicação
├── logging_config.py         # Configuração central do logging/auditoria
├── models/                   # Entidades e enumerações
│   ├── enums.py               # Severidade, StatusVulnerabilidade
│   ├── equipamento.py         # Equipamento e suas subclasses (Servidor, Roteador, ...)
│   └── vulnerabilidade.py     # Entidade Vulnerabilidade
├── repositories/             # Acesso direto ao SQLite (SQL puro)
│   ├── database.py
│   ├── equipamento_repository.py
│   └── vulnerabilidade_repository.py
├── services/                 # Regras de negócio, validações, cache em dicionário e logging
│   ├── equipamento_service.py
│   └── vulnerabilidade_service.py
└── cli/                      # Menu no terminal (interface de texto)
    └── interface_texto.py
```

## Arquitetura em camadas

- **models**: classes simples (`dataclass`) que representam os dados, sem
  nenhuma lógica de banco de dados ou de interface.
- **repositories**: única camada que conversa com o SQLite. Cada método
  corresponde a uma operação SQL (inserir, atualizar, excluir, buscar).
- **services**: aplicam as regras de negócio (campos obrigatórios, tipos
  válidos etc.) antes de chamar o repositório. Também mantêm em memória um
  **cache em dicionário** dos equipamentos e vulnerabilidades já carregados, para
  otimizar buscas repetidas sem precisar acessar o banco a cada consulta.
- **cli**: interface de texto (menu no terminal). Não tem comando SQL nem
  regra de negócio — apenas coleta dados do usuário, chama os serviços
  (`EquipamentoService`/`VulnerabilidadeService`) e exibe o resultado.

## Tipos de equipamento (herança)

Cada tipo de equipamento é uma subclasse de `Equipamento`
(`app/models/equipamento.py`): `EstacaoDeTrabalho`, `Notebook`, `Servidor`,
`BancoDeDados`, `SoftwareLicenciado`, `Impressora`, `Roteador`, `Switch` e
`Firewall`. Não existe um campo `tipo`: o tipo de um equipamento é a
própria classe do objeto, e cada subclasse define o seu `ROTULO` exibido no
menu.

No banco de dados, todas as subclasses ficam na mesma tabela
`equipamentos`. A coluna `classe` guarda o nome da subclasse (ex.:
`Servidor`), usado pelo repositório para recriar o objeto com a classe
certa ao ler o registro. As vulnerabilidades referenciam o equipamento pela
coluna `equipamento_id`.

## Funcionalidades

- Cadastro, edição, exclusão e busca (por ID ou nome) de equipamentos de TI.
- Ao excluir um equipamento, as vulnerabilidades associadas são removidas em
  cascata (garantido pelo próprio banco de dados, com `ON DELETE CASCADE`).
- Cadastro, edição e exclusão de vulnerabilidades vinculadas a um equipamento.
- Mensagem explícita quando um equipamento não possui nenhuma vulnerabilidade
  cadastrada.
- Nenhum campo de texto aceita caracteres especiais (pontuação, hífen,
  símbolos etc.). Regras por campo (`app/services/validacao.py`):
  - **nome**, **setor** e **descrição** (do equipamento e da
    vulnerabilidade): letras, números e espaços, mas não apenas números
    (ex.: `Servidor 01` é aceito; `2024` não);
  - **responsável** e **categoria**: apenas letras e espaços.
- Tratamento de erros de validação (campos vazios, tipos inválidos) exibido
  no próprio terminal, sem travar a aplicação.

## Severidade por nota CVSS

O usuário não escolhe a severidade da vulnerabilidade em uma lista: ele
informa uma **nota CVSS de 0.0 a 10.0**, e essa nota é o que fica salvo no
banco de dados (coluna `nota_cvss`, tabela `vulnerabilidades`). A severidade
em texto é sempre **calculada a partir da nota** (nunca armazenada), seguindo
as faixas oficiais do CVSS v3.1:

| Nota CVSS   | Severidade |
|-------------|------------|
| 0.0         | Nenhuma    |
| 0.1 – 3.9   | Baixa      |
| 4.0 – 6.9   | Média      |
| 7.0 – 8.9   | Alta       |
| 9.0 – 10.0  | Crítica    |

A classificação está centralizada em `Severidade.a_partir_da_nota_cvss()`
(`app/models/enums.py`), usada tanto pela camada de serviço quanto pela
propriedade `Vulnerabilidade.severidade` (`app/models/vulnerabilidade.py`) —
por isso o texto exibido nunca fica dessincronizado da nota salva. No
terminal, a severidade calculada aparece na confirmação após
cadastrar/atualizar uma vulnerabilidade e em cada linha da listagem.

## Logging / Auditoria

Toda ação de cadastro, edição e exclusão de equipamentos e vulnerabilidades — além
de tentativas inválidas (campo obrigatório vazio, tipo/severidade/status
inválido, busca por um ID inexistente) — é registrada em
`logs/auditoria.log`, servindo como evidência verificável do que foi feito
no sistema e quando.

Formato de cada linha: `data/hora [NÍVEL] módulo: mensagem`. Exemplo:

```
2026-09-14 22:10:03,512 [INFO] app.services.equipamento_service: Equipamento cadastrado: id=1 nome='DB-Server-01' responsavel='Raphael' setor='TI' classe=Servidor
2026-09-14 22:10:15,201 [WARNING] app.services.equipamento_service: Validação de equipamento falhou: campo obrigatório 'nome' não foi informado.
2026-09-14 22:11:02,884 [INFO] app.services.equipamento_service: Equipamento excluído: id=1 nome='DB-Server-01' (vulnerabilidades associadas removidas em cascata)
```

A configuração fica centralizada em `app/logging_config.py`
(`configurar_logging()`), chamada uma única vez ao iniciar a aplicação
(`main.py`). Mensagens de nível `INFO` (ações concluídas) vão só para o
arquivo; mensagens de nível `WARNING` (tentativas inválidas) aparecem tanto
no arquivo quanto no console.

## Testes automatizados

O CRUD completo de equipamentos e vulnerabilidades é coberto por testes
automatizados com `unittest` (biblioteca padrão do Python, sem dependências
extras). Para rodar toda a suíte a partir da raiz do projeto:

```bash
python3 -m unittest discover -s tests -v
```

Estrutura dos testes:

```
tests/
├── base.py                             # Classe base: cria/destrói um SQLite temporário por teste
├── test_equipamento_repository.py      # CRUD de equipamentos direto na camada SQLite
├── test_vulnerabilidade_repository.py  # CRUD de vulnerabilidades + exclusão em cascata (RF07)
├── test_equipamento_service.py         # CRUD + validações (RNF02) + cache em dicionário (RF10/RNF05)
├── test_vulnerabilidade_service.py     # CRUD + validação da nota CVSS (0.0–10.0) + RF09
└── test_severidade_cvss.py             # Classificação da nota CVSS nas faixas de severidade
```

Cada teste usa um banco de dados SQLite próprio, criado em um diretório
temporário e descartado ao final — os testes nunca leem ou alteram o banco
real da aplicação (`data/inventario.db`). Os testes de cadastro, edição e
exclusão também verificam (com `assertLogs`) que a ação correspondente foi
registrada no log de auditoria.

# Inventário de Ativos de TI

Repositório para armazenar os códigos do projeto do primeiro semestre do curso de Cibersegurança da UFU 2026-2

Aluno: Raphael Felix

**API REST** (FastAPI) de cadastro de equipamentos de TI e de suas
vulnerabilidades, com análise de risco por modelo linear e persistência em
banco de dados **SQLite**, e um **frontend** em HTML, CSS e JavaScript puros
(sem frameworks), servido por nginx em outro container.

## Como executar

### Com Docker (recomendado)

```bash
docker compose up -d --build     # sobe a API e o frontend em segundo plano
docker compose logs -f           # acompanha os logs
docker compose down              # para tudo
```

- **Frontend:** `http://localhost:8080`
- **API:** `http://localhost:8000` (documentação em `/docs`)

Os dois containers reiniciam sozinhos se caírem (`restart: unless-stopped`) e
têm healthcheck (`GET /api/saude` na API; a página inicial no frontend). O
banco (`data/`) e o log de auditoria (`logs/`) ficam no computador
hospedeiro, montados como volumes.

### Sem Docker

```bash
pip install -r requirements.txt
python3 main.py
```

Em ambos os casos, a API fica em `http://localhost:8000` e a **documentação
interativa** (Swagger), onde dá para testar todas as rotas pelo navegador,
fica em **`http://localhost:8000/docs`**.

Na primeira execução, o arquivo de banco de dados `data/inventario.db` é
criado automaticamente com as tabelas necessárias. Para popular o banco com
dados fictícios: `python3 seed_dados_teste.py` (ou, com Docker,
`docker compose exec api python seed_dados_teste.py`). Se a API já estiver
rodando, reinicie-a depois do seed (`docker compose restart api`): ela mantém
equipamentos e vulnerabilidades em cache na memória e só lê os dados novos
ao iniciar.

### Configuração (variáveis de ambiente)

| Variável             | Padrão                                         | Uso |
|----------------------|------------------------------------------------|-----|
| `ORIGENS_PERMITIDAS` | `http://localhost:5173,http://localhost:3000` | Endereços do frontend autorizados a chamar a API pelo navegador (CORS). No `docker-compose.yml`: `http://localhost:8080,http://localhost:5173` |
| `CAMINHO_DO_BANCO`   | `data/inventario.db`                           | Arquivo SQLite |
| `HOST` / `PORTA`     | `127.0.0.1` / `8000`                           | Só para `python3 main.py` |
| `API_URL` (frontend) | `http://localhost:8000/api`                    | Endereço da API **visto pelo navegador**. Ao iniciar, o container do frontend grava esse valor em `js/config.js` e no cabeçalho CSP |

## Rotas da API

Todas as rotas têm o prefixo `/api` e trocam JSON. Detalhes de cada campo
estão em `/docs`.

| Método | Rota | O que faz |
|--------|------|-----------|
| GET    | `/equipamentos?nome=texto`           | Lista equipamentos (filtro por nome opcional) |
| POST   | `/equipamentos`                      | Cadastra equipamento |
| GET    | `/equipamentos/{id}`                 | Busca equipamento pelo ID |
| PUT    | `/equipamentos/{id}`                 | Atualiza equipamento (o nome não muda) |
| DELETE | `/equipamentos/{id}`                 | Exclui equipamento (e as vulnerabilidades exclusivas dele) |
| GET    | `/equipamentos/{id}/vulnerabilidades`          | Vulnerabilidades do equipamento |
| GET    | `/equipamentos/{id}/vulnerabilidades-exclusivas` | Vulnerabilidades que seriam excluídas junto com ele |
| POST   | `/equipamentos/{id}/vulnerabilidades/{vid}`    | Atribui vulnerabilidade ao equipamento |
| DELETE | `/equipamentos/{id}/vulnerabilidades/{vid}`    | Remove vulnerabilidade do equipamento |
| GET    | `/vulnerabilidades`                  | Lista o catálogo |
| POST   | `/vulnerabilidades`                  | Cadastra vulnerabilidade |
| GET    | `/vulnerabilidades/{id}`             | Busca vulnerabilidade |
| PUT    | `/vulnerabilidades/{id}`             | Atualiza vulnerabilidade |
| DELETE | `/vulnerabilidades/{id}`             | Exclui vulnerabilidade |
| GET    | `/vulnerabilidades/{id}/equipamentos` | Equipamentos afetados |
| GET    | `/dependencias?equipamento_id=N`     | Lista dependências (filtro opcional) |
| PUT    | `/dependencias/{id}/{depende_de_id}` | Cadastra ou altera dependência (corpo: `{"fator": 0.3}`) |
| DELETE | `/dependencias/{id}/{depende_de_id}` | Remove dependência |
| GET    | `/analise-de-risco`                  | Risco próprio e efetivo de todos os equipamentos |
| GET    | `/analise-de-risco/equipamentos/{id}` | Risco de um equipamento |
| GET    | `/analise-de-risco/matrizes`         | Matrizes M, A e vetores v, f |
| GET    | `/tipos-de-equipamento`, `/status-de-vulnerabilidade`, `/severidades` | Opções para listas de seleção do frontend |
| GET    | `/saude`                             | Verificação de saúde (healthcheck) |

Exemplo de chamada a partir do frontend:

```javascript
const resposta = await fetch("http://localhost:8000/api/equipamentos", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    nome: "Servidor Web 01", responsavel: "Ana", setor: "TI", classe: "Servidor",
  }),
});
const dados = await resposta.json();
if (!resposta.ok) alert(dados.detail); // toda resposta de erro tem "detail"
```

### Códigos de status e erros

Toda resposta de erro tem o mesmo formato, `{"detail": "mensagem em texto"}`,
para o frontend poder exibir a mensagem diretamente.

| Status | Quando |
|--------|--------|
| 200 / 201 | Sucesso (201 = cadastrado) |
| 204    | Sucesso sem conteúdo (exclusões e atribuições) |
| 404    | Equipamento ou vulnerabilidade não encontrado |
| 409    | `I - A` não é invertível (análise de risco impossível com os dados atuais) |
| 422    | Dados inválidos (campo faltando, tipo errado, regra de negócio violada) |

## Estrutura do projeto

```
main.py                       # Ponto de entrada: cria a API com as configurações do ambiente
requirements.txt              # Dependências da aplicação (também instaladas no container)
requirements-dev.txt          # + testes e linters
Dockerfile                    # Imagem da API
docker-compose.yml            # API + frontend em containers, com volumes e reinício automático
frontend/                     # Frontend (HTML, CSS e JS puros), com Dockerfile próprio (nginx)
seed_dados_teste.py           # Script utilitário para popular o banco com dados fictícios
data/                         # Banco de dados SQLite (gerado em tempo de execução)
logs/                         # Log de auditoria (gerado em tempo de execução)
tests/                        # Testes automatizados (unittest)
postman/                      # Coleção Postman com os testes de integração da API
app/
├── exceptions.py             # Exceções personalizadas da aplicação
├── servicos.py               # Cria e conecta todos os serviços (usado pela API e pelo seed)
├── logging_config.py         # Configuração central do logging/auditoria
├── models/                   # Entidades e enumerações
│   ├── enums.py               # Severidade, StatusVulnerabilidade
│   ├── equipamento.py         # Equipamento e suas subclasses (Servidor, Roteador, ...)
│   ├── vulnerabilidade.py     # Entidade Vulnerabilidade
│   └── dependencia.py         # Dependência entre dois equipamentos (matriz A)
├── repositories/             # Acesso direto ao SQLite (SQL puro)
│   ├── database.py
│   ├── equipamento_repository.py
│   ├── vulnerabilidade_repository.py
│   └── dependencia_repository.py
├── services/                 # Regras de negócio, validações, cache em dicionário e logging
│   ├── equipamento_service.py
│   ├── vulnerabilidade_service.py
│   ├── dependencia_service.py
│   └── analise_de_risco_service.py  # Modelo linear de risco (matrizes com NumPy)
└── api/                      # Camada HTTP (FastAPI)
    ├── aplicacao.py           # Cria a aplicação: banco, serviços, CORS, erros e rotas
    ├── esquemas.py            # Formato do JSON de entrada e de saída (Pydantic)
    ├── respostas.py           # Converte equipamentos/vulnerabilidades em respostas
    ├── erros.py               # Converte exceções em respostas HTTP {"detail": ...}
    ├── servicos_da_requisicao.py  # Entrega os serviços às rotas (Depends)
    └── rotas/                 # Um arquivo por recurso
        ├── equipamentos.py
        ├── vulnerabilidades.py
        ├── dependencias.py
        ├── analise_de_risco.py
        └── opcoes.py          # Tipos, status, severidades e saúde
```

## Frontend

HTML, CSS e JavaScript puros: sem frameworks, sem bibliotecas, sem `npm`
nem etapa de build. Os scripts usam ES modules nativos do navegador
(`<script type="module">`). O tema visual ("Wired") é inspirado na estética
de *Serial Experiments Lain*: monitores CRT, linhas de varredura, fósforo
verde, vermelho de alerta e fios elétricos no cabeçalho. Tudo é feito em
CSS, sem imagens. As animações são desligadas para quem ativou "reduzir
movimento" no sistema.

```
frontend/
├── Dockerfile                  # nginx:alpine servindo public/
├── nginx/
│   ├── default.conf.template   # site + cabeçalhos de segurança (CSP com ${API_URL})
│   └── 40-gerar-config.sh      # gera js/config.js com API_URL ao iniciar o container
└── public/                     # tudo o que o navegador recebe
    ├── index.html              # painel: estado da API, contagens, maiores riscos
    ├── equipamentos.html       # lista, busca por nome, cadastro, edição, exclusão
    ├── equipamento.html        # detalhes (?id=N): vulnerabilidades, dependências, risco
    ├── vulnerabilidades.html   # catálogo + equipamentos afetados
    ├── dependencias.html       # dependências entre equipamentos (matriz A)
    ├── risco.html              # ranking de risco e matrizes M, v, f, A
    ├── css/estilo.css          # tema e layout responsivo
    └── js/
        ├── config.js           # endereço da API (sobrescrito no container)
        ├── api.js              # único arquivo que usa fetch; erros viram ErroDaApi
        ├── ui.js               # criação de elementos, tabelas, mensagens, diálogos
        └── <página>.js         # um script por página
```

- **Comunicação:** o navegador chama a API diretamente (CORS). Por isso,
  `API_URL` é o endereço que o *navegador* enxerga. Não use
  `http://api:8000`: esse nome só existe dentro da rede do Docker.
- **Validação:** o HTML faz só o básico (`required`, `min`/`max`/`step`,
  `pattern`). As regras completas ficam na API, e a mensagem `detail` dos
  erros aparece na tela.
- **Segurança:** dados da API são inseridos sempre como texto
  (`textContent`), nunca como HTML, como defesa contra XSS. O nginx envia
  uma Content-Security-Policy que só permite scripts do próprio site e
  chamadas para `API_URL`. Por isso o HTML não tem scripts nem eventos
  inline (`onclick`).
- **Responsivo:** em telas estreitas, o menu vira uma faixa com rolagem
  horizontal e as tabelas viram cartões (cada célula mostra o nome da
  coluna). As matrizes da análise de risco rolam na horizontal.
- **Sem Docker:** `python -m http.server 5173 -d frontend/public` e abra
  `http://localhost:5173`. A porta 5173 já está liberada no CORS da API.
  Abrir o arquivo HTML direto (`file://`) não funciona com ES modules.

O roteiro de teste manual do frontend está em `frontend/README.md`.

## Arquitetura em camadas

- **models**: classes simples (`dataclass`) que representam os dados, sem
  nenhuma lógica de banco de dados ou de interface.
- **repositories**: única camada que conversa com o SQLite. Cada método
  corresponde a uma operação SQL (inserir, atualizar, excluir, buscar).
- **services**: aplicam as regras de negócio (campos obrigatórios, tipos
  válidos etc.) antes de chamar o repositório. Também mantêm em memória um
  **cache em dicionário** dos equipamentos e vulnerabilidades já carregados, para
  otimizar buscas repetidas sem precisar acessar o banco a cada consulta.
- **api**: camada HTTP. Não tem comando SQL nem regra de negócio — cada rota
  só lê o JSON da requisição, chama um serviço e devolve o resultado em JSON.
  Os esquemas (`esquemas.py`) verificam o tipo de cada campo; as exceções dos
  serviços viram códigos HTTP em `erros.py`.

Para adicionar uma rota nova: crie a função no arquivo do recurso em
`app/api/rotas/`, com `async def` e um parâmetro `servicos: Servicos`. Se for
um recurso novo, crie o arquivo e registre-o em `app/api/aplicacao.py`. As
rotas devem ser `async def` porque a conexão SQLite só pode ser usada no
thread que a abriu (veja o comentário no topo de `aplicacao.py`).

## Tipos de equipamento (herança)

Cada tipo de equipamento é uma subclasse de `Equipamento`
(`app/models/equipamento.py`): `EstacaoDeTrabalho`, `Notebook`, `Servidor`,
`BancoDeDados`, `SoftwareLicenciado`, `Impressora`, `Roteador`, `Switch` e
`Firewall`. Não existe um campo `tipo`: o tipo de um equipamento é a
própria classe do objeto, e cada subclasse define o seu `ROTULO` (nome para
exibição) e o seu `FATOR_DE_EXPOSICAO`. Na API, o tipo é enviado no campo
`classe` (ex.: `"Servidor"`); a lista completa está em
`GET /api/tipos-de-equipamento`.

No banco de dados, todas as subclasses ficam na mesma tabela
`equipamentos`. A coluna `classe` guarda o nome da subclasse (ex.:
`Servidor`), usado pelo repositório para recriar o objeto com a classe
certa ao ler o registro.

## Vulnerabilidades compartilhadas entre equipamentos

As vulnerabilidades existem independentemente dos equipamentos: uma mesma
vulnerabilidade pode afetar vários equipamentos, e um equipamento pode ter
várias vulnerabilidades (relação N:N). No banco de dados, a tabela
`vulnerabilidades` guarda só os dados da vulnerabilidade, e a tabela
`equipamento_vulnerabilidade` guarda cada par (equipamento, vulnerabilidade).

- A associação é feita por `POST`/`DELETE`
  `/api/equipamentos/{id}/vulnerabilidades/{vid}`, e pode ser consultada
  pelos dois lados (`/equipamentos/{id}/vulnerabilidades` e
  `/vulnerabilidades/{id}/equipamentos`).
- Remover uma vulnerabilidade de um equipamento não a exclui do catálogo.
- **Ao excluir um equipamento**, são excluídas junto apenas as
  vulnerabilidades que afetavam somente ele. As que também afetam outros
  equipamentos continuam cadastradas. A regra é garantida pelo próprio banco
  (trigger `excluir_vulnerabilidades_orfas`). Para avisar o usuário antes de
  confirmar, o frontend pode consultar
  `GET /api/equipamentos/{id}/vulnerabilidades-exclusivas`.

Bancos criados por versões anteriores (com a coluna `equipamento_id` em
`vulnerabilidades`) são migrados automaticamente ao abrir a aplicação, sem
perder dados (`app/repositories/database.py`).

## Análise de risco (modelo linear)

Rotas **`/api/analise-de-risco`**. Estima o risco de cada equipamento a partir
das vulnerabilidades dele e das dependências entre equipamentos. Todo o
cálculo está em `app/services/analise_de_risco_service.py`.

Com n equipamentos e m vulnerabilidades:

| Símbolo | Tamanho | Significado |
|---------|---------|-------------|
| `M`     | n x m   | Matriz de incidência: `M[i][j] = 1` se o equipamento i é afetado pela vulnerabilidade j |
| `v`     | m       | Vetor de severidade: `v[j]` = nota CVSS da vulnerabilidade j |
| `f`     | n       | Vetor de exposição: `f[i]` = `FATOR_DE_EXPOSICAO` da classe do equipamento i |
| `b`     | n       | Risco próprio: `b = f * (M @ v)` |
| `A`     | n x n   | Matriz de dependências: `A[i][j]` = fração do risco de j herdada por i |
| `x`     | n       | Risco efetivo: solução de `(I - A) x = b` |

- **Fator de exposição (polimorfismo):** cada subclasse de `Equipamento`
  define o seu `FATOR_DE_EXPOSICAO` (ex.: `Firewall` = 1.5,
  `Impressora` = 0.8), que pondera o risco próprio.
- **Dependências:** cadastradas em `PUT /api/dependencias/...` e gravadas na tabela
  `dependencias`. Regras (`app/services/dependencia_service.py`): um
  equipamento não depende de si mesmo, o fator fica em `[0, 1)` e a soma dos
  fatores de um equipamento (soma da linha de A) deve ser menor que 1. Isso
  torna `I - A` estritamente diagonal dominante e, portanto, invertível.
- **Verificação de invertibilidade:** antes de resolver, o programa calcula
  o determinante de `I - A` (comparado com uma tolerância, já que em ponto
  flutuante ele quase nunca dá exatamente zero) e o número de condição
  (que indica quantos dígitos de precisão se perdem). Se a matriz não for
  invertível ou for mal condicionada, a API responde 409 com a explicação.
- **Resolução:** `numpy.linalg.solve`, que resolve o sistema diretamente, sem
  calcular a inversa.
- `GET /api/analise-de-risco/matrizes` devolve M, v, f e A montadas a partir
  dos dados cadastrados.
- O cenário de validação com três equipamentos, resolvido à mão, está
  documentado em `tests/test_analise_de_risco.py`.

## Funcionalidades

- Cadastro, edição, exclusão e busca (por ID ou nome) de equipamentos de TI.
- Catálogo de vulnerabilidades: cadastro, edição e exclusão, independentes
  dos equipamentos.
- Atribuição e remoção de vulnerabilidades em equipamentos, pelos dois lados
  (pelo equipamento ou pela vulnerabilidade).
- Ao excluir um equipamento, as vulnerabilidades exclusivas dele são
  excluídas junto; as compartilhadas são mantidas.
- Nenhum campo de texto aceita caracteres especiais (pontuação, hífen,
  símbolos etc.). Regras por campo (`app/services/validacao.py`):
  - **nome**, **setor** e **descrição** (do equipamento e da
    vulnerabilidade): letras, números e espaços, mas não apenas números
    (ex.: `Servidor 01` é aceito; `2024` não);
  - **responsável** e **categoria**: apenas letras e espaços.
- Erros de validação (campos vazios, tipos inválidos) são devolvidos com
  status 422 e uma mensagem explicando o campo e o problema.

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
por isso o texto exibido nunca fica dessincronizado da nota salva. Na API,
a severidade calculada vem no campo `severidade` de cada vulnerabilidade.

## Logging / Auditoria

Toda ação de cadastro, edição e exclusão de equipamentos e vulnerabilidades — além
de tentativas inválidas (campo obrigatório vazio, tipo/severidade/status
inválido, busca por um ID inexistente, JSON recusado pela API) — é registrada em
`logs/auditoria.log`, servindo como evidência verificável do que foi feito
no sistema e quando.

Formato de cada linha: `data/hora [NÍVEL] módulo: mensagem`. Exemplo:

```
2026-09-14 22:10:03,512 [INFO] app.services.equipamento_service: Equipamento cadastrado: id=1 nome='DB-Server-01' responsavel='Raphael' setor='TI' classe=Servidor
2026-09-14 22:10:15,201 [WARNING] app.services.equipamento_service: Validação de equipamento falhou: campo obrigatório 'nome' não foi informado.
2026-09-14 22:11:02,884 [INFO] app.services.equipamento_service: Equipamento excluído: id=1 nome='DB-Server-01' (vulnerabilidades exclusivas dele removidas em cascata)
```

A configuração fica centralizada em `app/logging_config.py`
(`configurar_logging()`), chamada uma única vez ao iniciar a aplicação
(`main.py`). Mensagens de nível `INFO` (ações concluídas) vão só para o
arquivo; mensagens de nível `WARNING` (tentativas inválidas) aparecem tanto
no arquivo quanto no console.

## Testes automatizados

O CRUD completo de equipamentos e vulnerabilidades, a análise de risco e as
rotas da API são cobertos por testes automatizados com `unittest`. Para rodar
toda a suíte a partir da raiz do projeto:

```bash
pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
```

O GitHub Actions roda os testes e os linters (black, flake8, pylint) a cada
push e pull request para a `main`.

### Testes de integração (Postman)

A coleção `postman/inventario_api.postman_collection.json` testa todas as
rotas com a API rodando de verdade (64 requisições, 248 verificações). Ela
percorre o fluxo completo: cadastra equipamentos e vulnerabilidades, faz as
atribuições e dependências, confere o cenário de risco resolvido à mão
(`x = [13, 11.5, 7.75]`) e, por fim, exclui tudo o que criou.

- **No Postman:** *Import* > selecione o arquivo > clique com o botão
  direito na coleção > *Run collection*. As pastas devem rodar na ordem,
  porque cada requisição guarda os ids criados em variáveis da coleção.
- **Pela linha de comando**, com o [Newman](https://www.npmjs.com/package/newman):

  ```bash
  npx newman run postman/inventario_api.postman_collection.json
  # outra URL: --env-var baseUrl=http://servidor:8000/api
  ```

Os dados criados levam um sufixo aleatório no nome e são apagados no final,
então a coleção pode rodar com outros dados no banco. Mesmo assim, prefira um
banco separado, porque a execução gera linhas no log de auditoria e consome
ids:

```bash
CAMINHO_DO_BANCO=data/teste_postman.db python3 main.py
```

Estrutura dos testes:

```
tests/
├── base.py                             # Classe base: cria/destrói um SQLite temporário por teste
├── test_equipamento_repository.py      # CRUD de equipamentos direto na camada SQLite
├── test_vulnerabilidade_repository.py  # CRUD de vulnerabilidades + associações + trigger de exclusão
├── test_equipamento_service.py         # CRUD + validações (RNF02) + cache em dicionário (RF10/RNF05)
├── test_vulnerabilidade_service.py     # CRUD + nota CVSS + associações N:N + exclusão de equipamento
├── test_dependencia_service.py         # Dependências entre equipamentos e suas regras
├── test_analise_de_risco.py            # Matrizes M, v, f, A, invertibilidade e cenário resolvido à mão
├── test_api.py                         # Rotas da API: JSON, códigos HTTP, erros e CORS
├── test_database.py                    # Migração automática do formato antigo do banco
└── test_severidade_cvss.py             # Classificação da nota CVSS nas faixas de severidade
```

Cada teste usa um banco de dados SQLite próprio, criado em um diretório
temporário e descartado ao final — os testes nunca leem ou alteram o banco
real da aplicação (`data/inventario.db`). Os testes de cadastro, edição e
exclusão também verificam (com `assertLogs`) que a ação correspondente foi
registrada no log de auditoria.

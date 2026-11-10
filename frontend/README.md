# Frontend — roteiro de teste manual

Visão geral, organização das pastas e decisões de projeto: veja a seção
**Frontend** do `README.md` na raiz do repositório.

## Preparação

Use um banco separado para não misturar os testes com dados reais:

```bash
docker compose up -d --build
docker compose exec api python seed_dados_teste.py
docker compose restart api    # a API só lê os dados do seed ao iniciar
```

Abra `http://localhost:8080`. Repita os testes de layout com a janela
estreita, ou com as ferramentas do desenvolvedor (F12) no modo dispositivo,
em uma largura de ~390 px.

## Checklist

### Painel (`index.html`)
- [ ] API aparece como **online**; as contagens batem com o seed (7 equipamentos, 7 vulnerabilidades).
- [ ] A tabela "Maiores riscos" mostra 5 equipamentos, do maior para o menor, com as barras proporcionais.
- [ ] Com a API parada (`docker compose stop api`), o painel mostra **offline** e a mensagem de erro de conexão.

### Equipamentos
- [ ] A busca por nome filtra enquanto se digita; um nome inexistente mostra "Nenhum equipamento com ...".
- [ ] Cadastro: responsável com número (`Ana 2`) é barrado pelo navegador; um cadastro válido fecha o diálogo e mostra a mensagem de sucesso.
- [ ] Edição: o nome aparece somente leitura; a alteração do setor aparece na tabela.
- [ ] Erro da API dentro do diálogo: responsável só com espaços → "O campo 'responsavel' é obrigatório."
- [ ] Exclusão: o diálogo de confirmação lista as vulnerabilidades exclusivas que serão apagadas; "Cancelar" não exclui.

### Detalhes do equipamento (`equipamento.html?id=1`)
- [ ] Dados, risco (próprio, herdado, efetivo e barra) e dependências nos dois sentidos.
- [ ] Atribuir uma vulnerabilidade do catálogo aumenta o risco próprio; removê-la volta ao valor anterior.
- [ ] "Editar" abre a edição do equipamento na página de equipamentos.
- [ ] `?id=999` mostra "Não existe equipamento cadastrado com o ID 999."

### Vulnerabilidades
- [ ] Nota CVSS 11 é barrada pelo navegador; 9,5 gera a etiqueta **crítica**.
- [ ] Editar a nota muda a severidade (calculada pela API).
- [ ] O botão "N equip." abre os afetados; atribuir e remover atualizam a lista e o contador.
- [ ] Excluir pede confirmação e informa de quantos equipamentos ela será removida.

### Dependências
- [ ] `dependencias.html?equipamento=6` já abre com a Estação RH 05 escolhida e filtrada.
- [ ] O texto de ajuda mostra quanto da soma (< 1) o equipamento já usa.
- [ ] O próprio equipamento aparece desativado em "Depende de".
- [ ] Um fator que faça a soma chegar a 1 é recusado pela API, com a mensagem dela.
- [ ] Editar preenche o formulário; Excluir pede confirmação.

### Análise de risco
- [ ] Indicadores n, m, det(I − A) e número de condição.
- [ ] Ranking ordenado pelo risco efetivo; passar o mouse em Vn/En nas matrizes mostra o nome completo.
- [ ] As matrizes M e A rolam na horizontal em telas estreitas, com a coluna de nomes fixa.

### Geral
- [ ] Nenhum erro de CSP no console do navegador (F12 → Console).
- [ ] Navegação só pelo teclado (Tab/Enter/Esc) funciona nos diálogos.
- [ ] No celular, nenhuma página rola na horizontal (só o menu e as matrizes).

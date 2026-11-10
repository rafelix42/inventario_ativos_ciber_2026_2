// Página de análise de risco: ranking dos equipamentos e as matrizes do
// modelo linear (M, v, f e A), exatamente como a API as monta.

import { analiseDeRisco, equipamentos, vulnerabilidades } from "./api.js";
import {
  barraDeRisco,
  el,
  formatarNumero,
  mostrarCarregandoNaTabela,
  mostrarErro,
  mostrarMensagem,
  preencherTabela,
} from "./ui.js";

const tabelaDeRiscos = document.getElementById("tabela-riscos");
const areaDasMatrizes = document.getElementById("matrizes");

function exibirIndicador(id, texto) {
  document.getElementById(id).textContent = texto;
}

// --- Ranking ----------------------------------------------------------------

async function carregarRanking() {
  mostrarCarregandoNaTabela(tabelaDeRiscos);
  try {
    const analise = await analiseDeRisco.calcular();
    exibirIndicador("indicador-determinante", formatarNumero(analise.determinante, 4));
    exibirIndicador("indicador-condicao", formatarNumero(analise.numero_de_condicao, 4));

    const maximo = analise.riscos[0]?.risco_efetivo ?? 0;
    preencherTabela(
      tabelaDeRiscos,
      analise.riscos.map((risco, posicao) => [
        { conteudo: posicao + 1, classe: "numero" },
        el("a", { href: `equipamento.html?id=${risco.equipamento_id}`, texto: risco.nome }),
        risco.tipo,
        { conteudo: formatarNumero(risco.fator_de_exposicao, 1), classe: "numero" },
        { conteudo: formatarNumero(risco.risco_proprio), classe: "numero" },
        { conteudo: formatarNumero(risco.risco_herdado), classe: "numero" },
        { conteudo: formatarNumero(risco.risco_efetivo), classe: "numero" },
        { conteudo: barraDeRisco(risco.risco_proprio, risco.risco_herdado, maximo), classe: "coluna-barra" },
      ]),
      "Nenhum equipamento cadastrado.",
    );
  } catch (erro) {
    if (erro.status !== 409) throw erro;
    // 409: (I - A) não é invertível com as dependências atuais. As matrizes
    // continuam disponíveis e ajudam a encontrar o problema.
    preencherTabela(tabelaDeRiscos, [], "Análise indisponível com os dados atuais.");
    mostrarMensagem(erro.message, "aviso");
  }
}

// --- Matrizes ---------------------------------------------------------------

// Monta uma tabela de matriz. 'linhas' e 'colunas' são listas de
// {rotulo, titulo}; 'valores' é a matriz (lista de linhas).
function tabelaDeMatriz({ linhas, colunas, valores, casas, legenda }) {
  const cabecalho = el(
    "tr",
    {},
    el("th", { scope: "col" }, el("span", { class: "visualmente-oculto", texto: "Linha" })),
    colunas.map((coluna) => el("th", { scope: "col", title: coluna.titulo, texto: coluna.rotulo })),
  );
  const corpo = valores.map((valoresDaLinha, i) =>
    el(
      "tr",
      {},
      el("th", { scope: "row", title: linhas[i].titulo, texto: linhas[i].rotulo }),
      valoresDaLinha.map((valor) =>
        el("td", { class: valor === 0 ? "zero" : "nao-zero", texto: formatarNumero(valor, casas) }),
      ),
    ),
  );
  return el(
    "div",
    { class: "tabela-container" },
    el("table", { class: "matriz" }, el("caption", { class: "visualmente-oculto", texto: legenda }), el("thead", {}, cabecalho), el("tbody", {}, corpo)),
  );
}

function blocoDeMatriz(titulo, explicacao, tabela, aberto = false) {
  return el(
    "details",
    { class: "bloco-matriz", open: aberto },
    el("summary", { texto: titulo }),
    el("p", { class: "texto-suave", texto: explicacao }),
    tabela,
  );
}

async function carregarMatrizes() {
  const [matrizes, listaDeEquipamentos, catalogo] = await Promise.all([
    analiseDeRisco.matrizes(),
    equipamentos.listar(),
    vulnerabilidades.listar(),
  ]);
  const n = matrizes.ids_dos_equipamentos.length;
  const m = matrizes.ids_das_vulnerabilidades.length;
  exibirIndicador("indicador-n", n);
  exibirIndicador("indicador-m", m);

  if (n === 0) {
    areaDasMatrizes.replaceChildren(el("p", { class: "texto-suave", texto: "Sem equipamentos, não há matrizes." }));
    return;
  }

  const equipamentoPorId = new Map(listaDeEquipamentos.map((e) => [e.id, e]));
  const vulnerabilidadePorId = new Map(catalogo.map((v) => [v.id, v]));

  // Linhas: nome do equipamento. Colunas: códigos curtos (E1, V3) com o nome
  // completo no 'title' (aparece ao passar o mouse).
  const linhasDeEquipamentos = matrizes.ids_dos_equipamentos.map((id) => ({
    rotulo: equipamentoPorId.get(id)?.nome ?? `#${id}`,
    titulo: `ID ${id}`,
  }));
  const colunasDeEquipamentos = matrizes.ids_dos_equipamentos.map((id) => ({
    rotulo: `E${id}`,
    titulo: equipamentoPorId.get(id)?.nome ?? "",
  }));
  const colunasDeVulnerabilidades = matrizes.ids_das_vulnerabilidades.map((id) => ({
    rotulo: `V${id}`,
    titulo: vulnerabilidadePorId.get(id)?.descricao ?? "",
  }));

  areaDasMatrizes.replaceChildren(
    blocoDeMatriz(
      `M · incidência (${n} × ${m})`,
      "M[i][j] = 1 se o equipamento i é afetado pela vulnerabilidade j. Passe o mouse sobre Vn para ver a descrição.",
      m
        ? tabelaDeMatriz({
            linhas: linhasDeEquipamentos,
            colunas: colunasDeVulnerabilidades,
            valores: matrizes.matriz_de_incidencia,
            casas: 0,
            legenda: "Matriz de incidência M",
          })
        : el("p", { class: "texto-suave", texto: "Nenhuma vulnerabilidade cadastrada." }),
      true,
    ),
    blocoDeMatriz(
      `v · severidade (${m})`,
      "v[j] = nota CVSS da vulnerabilidade j.",
      tabelaDeMatriz({
        linhas: [{ rotulo: "CVSS", titulo: "" }],
        colunas: colunasDeVulnerabilidades,
        valores: [matrizes.vetor_de_severidade],
        casas: 1,
        legenda: "Vetor de severidade v",
      }),
    ),
    blocoDeMatriz(
      `f · exposição (${n})`,
      "f[i] = fator de exposição do tipo do equipamento i.",
      tabelaDeMatriz({
        linhas: linhasDeEquipamentos,
        colunas: [{ rotulo: "f", titulo: "Fator de exposição" }],
        valores: matrizes.vetor_de_exposicao.map((valor) => [valor]),
        casas: 1,
        legenda: "Vetor de exposição f",
      }),
    ),
    blocoDeMatriz(
      `A · dependências (${n} × ${n})`,
      "A[i][j] = fração do risco do equipamento j herdada pelo equipamento i. A soma de cada linha é menor que 1.",
      tabelaDeMatriz({
        linhas: linhasDeEquipamentos,
        colunas: colunasDeEquipamentos,
        valores: matrizes.matriz_de_dependencias,
        casas: 2,
        legenda: "Matriz de dependências A",
      }),
      true,
    ),
  );
}

// --- Início -----------------------------------------------------------------

async function iniciar() {
  // As duas partes são independentes: se uma falhar, a outra ainda aparece.
  const [ranking, matrizes] = await Promise.allSettled([carregarRanking(), carregarMatrizes()]);
  if (ranking.status === "rejected") {
    preencherTabela(tabelaDeRiscos, [], "Não foi possível calcular os riscos.");
    mostrarErro(ranking.reason);
  }
  if (matrizes.status === "rejected") {
    areaDasMatrizes.replaceChildren();
    // Evita repetir a mesma mensagem (ex.: API fora do ar derruba as duas).
    if (ranking.status === "fulfilled" || ranking.reason.message !== matrizes.reason.message) {
      mostrarErro(matrizes.reason);
    }
  }
}

iniciar();

// Painel (index.html): estado da API, contagens e os maiores riscos.

import { analiseDeRisco, equipamentos, opcoes, vulnerabilidades } from "./api.js";
import { barraDeRisco, el, formatarNumero, mostrarCarregandoNaTabela, mostrarErro, preencherTabela } from "./ui.js";

const QUANTIDADE_DE_MAIORES_RISCOS = 5;

const tabelaDeRiscos = document.getElementById("tabela-maiores-riscos");
const avisoDeRisco = document.getElementById("aviso-risco");

function exibirEstadoDaApi(online) {
  const estado = document.getElementById("estado-api");
  estado.replaceChildren(
    el("span", { class: `ponto ${online ? "ponto-online" : "ponto-offline"}` }),
    online ? "online" : "offline",
  );
  estado.closest(".indicador").classList.toggle("indicador-alerta", !online);
}

function exibirTotal(id, valor) {
  document.getElementById(id).textContent = valor;
}

async function carregarContagens() {
  const [listaDeEquipamentos, listaDeVulnerabilidades] = await Promise.all([
    equipamentos.listar(),
    vulnerabilidades.listar(),
  ]);
  exibirTotal("total-equipamentos", listaDeEquipamentos.length);
  exibirTotal("total-vulnerabilidades", listaDeVulnerabilidades.length);
  exibirTotal("total-abertas", listaDeVulnerabilidades.filter((v) => v.status === "ABERTA").length);
  exibirTotal("total-criticas", listaDeVulnerabilidades.filter((v) => v.severidade === "CRITICA").length);
}

async function carregarMaioresRiscos() {
  mostrarCarregandoNaTabela(tabelaDeRiscos);
  try {
    const analise = await analiseDeRisco.calcular();
    // A API já devolve os riscos do maior para o menor.
    const maiores = analise.riscos.slice(0, QUANTIDADE_DE_MAIORES_RISCOS);
    const maximo = maiores[0]?.risco_efetivo ?? 0;
    preencherTabela(
      tabelaDeRiscos,
      maiores.map((risco) => [
        el("a", { href: `equipamento.html?id=${risco.equipamento_id}`, texto: risco.nome }),
        risco.tipo,
        { conteudo: formatarNumero(risco.risco_efetivo), classe: "numero" },
        { conteudo: barraDeRisco(risco.risco_proprio, risco.risco_herdado, maximo), classe: "coluna-barra" },
      ]),
      "Nenhum equipamento cadastrado.",
    );
  } catch (erro) {
    // 409: as dependências cadastradas impedem o cálculo. Não é uma falha
    // da página, então aparece como aviso dentro do cartão.
    if (erro.status === 409) {
      preencherTabela(tabelaDeRiscos, [], "Análise indisponível.");
      avisoDeRisco.textContent = erro.message;
      avisoDeRisco.hidden = false;
    } else {
      throw erro;
    }
  }
}

async function iniciar() {
  try {
    await opcoes.saude();
    exibirEstadoDaApi(true);
  } catch (erro) {
    exibirEstadoDaApi(false);
    preencherTabela(tabelaDeRiscos, [], "API indisponível.");
    mostrarErro(erro);
    return;
  }

  try {
    await Promise.all([carregarContagens(), carregarMaioresRiscos()]);
  } catch (erro) {
    mostrarErro(erro);
  }
}

iniciar();

// Detalhes de um equipamento (equipamento.html?id=N): dados, risco,
// vulnerabilidades (atribuir/remover) e dependências.

import { analiseDeRisco, dependencias, equipamentos, opcoes, vulnerabilidades } from "./api.js";
import {
  barraDeRisco,
  botao,
  el,
  emAndamento,
  etiquetaSeveridade,
  etiquetaStatus,
  formatarNumero,
  lerFormulario,
  limparMensagens,
  mapaDeRotulos,
  mostrarCarregandoNaTabela,
  mostrarErro,
  mostrarMensagem,
  parametroDaUrl,
  preencherSelect,
  preencherTabela,
} from "./ui.js";

const id = Number(parametroDaUrl("id"));

const tabelaDeVulnerabilidades = document.getElementById("tabela-vulnerabilidades");
const formularioAtribuir = document.getElementById("formulario-atribuir");

let rotulosDeStatus = new Map();
let rotulosDeSeveridade = new Map();

function exibirTexto(idDoElemento, texto) {
  document.getElementById(idDoElemento).textContent = texto;
}

// --- Dados ------------------------------------------------------------------

function exibirDados(equipamento) {
  document.title = `${equipamento.nome} · Inventário de Ativos`;
  const titulo = document.getElementById("titulo");
  titulo.textContent = equipamento.nome;
  titulo.dataset.texto = equipamento.nome;
  titulo.classList.add("titulo-dado");
  exibirTexto("camada", `layer:02 · equipamento #${equipamento.id}`);

  exibirTexto("dado-nome", equipamento.nome);
  exibirTexto("dado-tipo", `${equipamento.tipo} (exposição ${formatarNumero(equipamento.fator_de_exposicao, 1)})`);
  exibirTexto("dado-responsavel", equipamento.responsavel);
  exibirTexto("dado-setor", equipamento.setor);
  exibirTexto("dado-descricao", equipamento.descricao || "—");
  document.getElementById("link-editar").href = `equipamentos.html?editar=${equipamento.id}`;
  document.getElementById("link-dependencias").href = `dependencias.html?equipamento=${equipamento.id}`;
}

// --- Risco ------------------------------------------------------------------

async function carregarRisco() {
  const aviso = document.getElementById("aviso-risco");
  const dadosDoRisco = document.getElementById("dados-risco");
  const barra = document.getElementById("barra-risco");
  try {
    const risco = await analiseDeRisco.doEquipamento(id);
    aviso.hidden = true;
    dadosDoRisco.hidden = false;
    exibirTexto("risco-proprio", formatarNumero(risco.risco_proprio));
    exibirTexto("risco-herdado", formatarNumero(risco.risco_herdado));
    exibirTexto("risco-efetivo", formatarNumero(risco.risco_efetivo));
    barra.replaceChildren(barraDeRisco(risco.risco_proprio, risco.risco_herdado, risco.risco_efetivo));
  } catch (erro) {
    if (erro.status !== 409) throw erro;
    // 409: as dependências cadastradas impedem o cálculo.
    aviso.textContent = erro.message;
    aviso.hidden = false;
    dadosDoRisco.hidden = true;
    barra.replaceChildren();
  }
}

// --- Vulnerabilidades -------------------------------------------------------

async function carregarVulnerabilidades() {
  const [doEquipamento, catalogo] = await Promise.all([
    equipamentos.listarVulnerabilidades(id),
    vulnerabilidades.listar(),
  ]);

  preencherTabela(
    tabelaDeVulnerabilidades,
    doEquipamento.map((v) => [
      { conteudo: v.id, classe: "numero" },
      v.descricao,
      { conteudo: formatarNumero(v.nota_cvss, 1), classe: "numero" },
      etiquetaSeveridade(v.severidade, rotulosDeSeveridade),
      etiquetaStatus(v.status, rotulosDeStatus),
      el("div", { class: "acoes-grupo" }, botao("Remover", () => remover(v), "botao-perigo")),
    ]),
    "Nenhuma vulnerabilidade afeta este equipamento.",
  );

  const atribuidas = new Set(doEquipamento.map((v) => v.id));
  const disponiveis = catalogo.filter((v) => !atribuidas.has(v.id));
  preencherSelect(formularioAtribuir.elements.namedItem("vulnerabilidade_id"), disponiveis, {
    valor: (v) => v.id,
    rotulo: (v) => `#${v.id} ${v.descricao} (CVSS ${formatarNumero(v.nota_cvss, 1)})`,
    vazio: disponiveis.length ? "Selecione…" : "Nenhuma outra vulnerabilidade no catálogo",
  });
  formularioAtribuir.querySelector("button").disabled = disponiveis.length === 0;
}

async function atribuir(evento) {
  evento.preventDefault();
  limparMensagens();
  const vulnerabilidadeId = Number(lerFormulario(formularioAtribuir).vulnerabilidade_id);
  try {
    await emAndamento(evento.submitter, () => equipamentos.atribuirVulnerabilidade(id, vulnerabilidadeId));
    mostrarMensagem(`Vulnerabilidade #${vulnerabilidadeId} atribuída.`, "sucesso");
    await Promise.all([carregarVulnerabilidades(), carregarRisco()]);
  } catch (erro) {
    mostrarErro(erro);
  }
}

async function remover(vulnerabilidade) {
  limparMensagens();
  try {
    await equipamentos.removerVulnerabilidade(id, vulnerabilidade.id);
    mostrarMensagem(`Vulnerabilidade #${vulnerabilidade.id} removida deste equipamento.`, "sucesso");
    await Promise.all([carregarVulnerabilidades(), carregarRisco()]);
  } catch (erro) {
    mostrarErro(erro);
  }
}

// --- Dependências -----------------------------------------------------------

async function carregarDependencias() {
  const [todas, listaDeEquipamentos] = await Promise.all([dependencias.listar(), equipamentos.listar()]);
  const nomes = new Map(listaDeEquipamentos.map((e) => [e.id, e.nome]));
  const linkPara = (outroId) =>
    el("a", { href: `equipamento.html?id=${outroId}`, texto: nomes.get(outroId) ?? `#${outroId}` });

  const dependeDe = todas.filter((d) => d.equipamento_id === id);
  const dependentes = todas.filter((d) => d.depende_de_id === id);

  preencherTabela(
    document.getElementById("tabela-depende-de"),
    dependeDe.map((d) => [linkPara(d.depende_de_id), { conteudo: formatarNumero(d.fator), classe: "numero" }]),
    "Não depende de nenhum equipamento.",
  );
  preencherTabela(
    document.getElementById("tabela-dependentes"),
    dependentes.map((d) => [linkPara(d.equipamento_id), { conteudo: formatarNumero(d.fator), classe: "numero" }]),
    "Nenhum equipamento depende deste.",
  );
  const soma = dependeDe.reduce((total, d) => total + d.fator, 0);
  exibirTexto("soma-dos-fatores", formatarNumero(soma));
}

// --- Início -----------------------------------------------------------------

async function iniciar() {
  if (!Number.isInteger(id) || id <= 0) {
    mostrarMensagem("Informe o equipamento na URL, por exemplo: equipamento.html?id=1", "erro");
    return;
  }
  formularioAtribuir.addEventListener("submit", atribuir);

  try {
    const [equipamento, status, severidades] = await Promise.all([
      equipamentos.buscar(id),
      opcoes.statusDeVulnerabilidade(),
      opcoes.severidades(),
    ]);
    rotulosDeStatus = mapaDeRotulos(status);
    rotulosDeSeveridade = mapaDeRotulos(severidades);
    exibirDados(equipamento);
    document.getElementById("conteudo-equipamento").hidden = false;

    mostrarCarregandoNaTabela(tabelaDeVulnerabilidades);
    await Promise.all([carregarVulnerabilidades(), carregarRisco(), carregarDependencias()]);
  } catch (erro) {
    mostrarErro(erro);
  }
}

iniciar();

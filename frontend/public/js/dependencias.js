// Página de dependências entre equipamentos (matriz A da análise de risco).
// "dependencias.html?equipamento=ID" já abre com esse equipamento escolhido.

import { dependencias, equipamentos } from "./api.js";
import {
  botao,
  confirmar,
  el,
  emAndamento,
  formatarNumero,
  limparMensagens,
  mostrarCarregandoNaTabela,
  mostrarErro,
  mostrarMensagem,
  parametroDaUrl,
  preencherSelect,
  preencherTabela,
} from "./ui.js";

const formulario = document.getElementById("formulario-dependencia");
const selectEquipamento = formulario.elements.namedItem("equipamento_id");
const selectDependeDe = formulario.elements.namedItem("depende_de_id");
const campoFator = formulario.elements.namedItem("fator");
const infoSoma = document.getElementById("info-soma");
const textoPadraoDaInfo = infoSoma.textContent;
const filtro = document.getElementById("filtro");
const tabela = document.getElementById("tabela-dependencias");

let listaDeEquipamentos = [];
let nomes = new Map();
let todas = [];

const nomeDe = (id) => nomes.get(id) ?? `#${id}`;

// --- Listagem ---------------------------------------------------------------

async function carregar() {
  todas = await dependencias.listar();
  exibir();
  atualizarInfoDaSoma();
}

function exibir() {
  const idFiltrado = Number(filtro.value) || null;
  const visiveis = todas
    .filter((d) => idFiltrado === null || d.equipamento_id === idFiltrado || d.depende_de_id === idFiltrado)
    .sort((a, b) => nomeDe(a.equipamento_id).localeCompare(nomeDe(b.equipamento_id)));

  preencherTabela(
    tabela,
    visiveis.map((d) => [
      el("a", { href: `equipamento.html?id=${d.equipamento_id}`, texto: nomeDe(d.equipamento_id) }),
      el("a", { href: `equipamento.html?id=${d.depende_de_id}`, texto: nomeDe(d.depende_de_id) }),
      { conteudo: formatarNumero(d.fator), classe: "numero" },
      el(
        "div",
        { class: "acoes-grupo" },
        botao("Editar", () => editar(d)),
        botao("Excluir", () => excluir(d), "botao-perigo"),
      ),
    ]),
    idFiltrado ? "Este equipamento não tem dependências." : "Nenhuma dependência cadastrada.",
  );
}

// --- Formulário -------------------------------------------------------------

// Mostra quanto da soma dos fatores (que deve ficar abaixo de 1) o
// equipamento escolhido já usa, sem contar a dependência que está sendo
// editada (o fator dela será substituído).
function atualizarInfoDaSoma() {
  const equipamentoId = Number(selectEquipamento.value);
  if (!equipamentoId) {
    infoSoma.textContent = textoPadraoDaInfo;
    return;
  }
  const dependeDeId = Number(selectDependeDe.value);
  const usado = todas
    .filter((d) => d.equipamento_id === equipamentoId && d.depende_de_id !== dependeDeId)
    .reduce((soma, d) => soma + d.fator, 0);
  infoSoma.textContent =
    `As outras dependências de "${nomeDe(equipamentoId)}" já somam ${formatarNumero(usado)}; ` +
    `o fator desta deve ser menor que ${formatarNumero(1 - usado)}.`;
}

// Um equipamento não pode depender de si mesmo: desativa essa opção.
function atualizarOpcoesDeDependeDe() {
  const equipamentoId = selectEquipamento.value;
  for (const opcao of selectDependeDe.options) {
    opcao.disabled = opcao.value !== "" && opcao.value === equipamentoId;
  }
  if (selectDependeDe.value === equipamentoId) {
    selectDependeDe.value = "";
  }
}

function aoMudarEquipamento() {
  atualizarOpcoesDeDependeDe();
  atualizarInfoDaSoma();
}

function editar(dependencia) {
  selectEquipamento.value = dependencia.equipamento_id;
  atualizarOpcoesDeDependeDe();
  selectDependeDe.value = dependencia.depende_de_id;
  campoFator.value = dependencia.fator;
  atualizarInfoDaSoma();
  formulario.scrollIntoView({ behavior: "smooth", block: "center" });
  campoFator.focus({ preventScroll: true });
}

async function salvar(evento) {
  evento.preventDefault();
  limparMensagens();
  const equipamentoId = Number(selectEquipamento.value);
  const dependeDeId = Number(selectDependeDe.value);
  const fator = Number(campoFator.value);

  try {
    await emAndamento(evento.submitter, () => dependencias.salvar(equipamentoId, dependeDeId, fator));
    mostrarMensagem(
      `"${nomeDe(equipamentoId)}" depende de "${nomeDe(dependeDeId)}" com fator ${formatarNumero(fator)}.`,
      "sucesso",
    );
    campoFator.value = "";
    await carregar();
  } catch (erro) {
    mostrarErro(erro);
  }
}

async function excluir(dependencia) {
  const confirmado = await confirmar({
    titulo: "Excluir dependência",
    mensagem:
      `"${nomeDe(dependencia.equipamento_id)}" deixará de herdar risco de ` +
      `"${nomeDe(dependencia.depende_de_id)}".`,
    textoConfirmar: "Excluir",
    perigo: true,
  });
  if (!confirmado) return;

  limparMensagens();
  try {
    await dependencias.excluir(dependencia.equipamento_id, dependencia.depende_de_id);
    mostrarMensagem("Dependência excluída.", "sucesso");
    await carregar();
  } catch (erro) {
    mostrarErro(erro);
  }
}

// --- Início -----------------------------------------------------------------

async function iniciar() {
  formulario.addEventListener("submit", salvar);
  // O 'reset' limpa os campos depois deste evento; por isso a atualização
  // espera o próximo ciclo (setTimeout 0).
  formulario.addEventListener("reset", () => setTimeout(aoMudarEquipamento));
  selectEquipamento.addEventListener("change", aoMudarEquipamento);
  selectDependeDe.addEventListener("change", atualizarInfoDaSoma);
  filtro.addEventListener("change", exibir);

  mostrarCarregandoNaTabela(tabela);
  try {
    listaDeEquipamentos = await equipamentos.listar();
  } catch (erro) {
    preencherTabela(tabela, [], "API indisponível.");
    mostrarErro(erro);
    return;
  }
  nomes = new Map(listaDeEquipamentos.map((e) => [e.id, e.nome]));

  const opcoesDeEquipamento = {
    valor: (e) => e.id,
    rotulo: (e) => `${e.nome} (${e.tipo})`,
  };
  const idDaUrl = parametroDaUrl("equipamento");
  preencherSelect(selectEquipamento, listaDeEquipamentos, {
    ...opcoesDeEquipamento,
    vazio: "Selecione…",
    selecionado: idDaUrl ?? undefined,
  });
  preencherSelect(selectDependeDe, listaDeEquipamentos, { ...opcoesDeEquipamento, vazio: "Selecione…" });
  preencherSelect(filtro, listaDeEquipamentos, {
    ...opcoesDeEquipamento,
    vazio: "Todos os equipamentos",
    selecionado: idDaUrl ?? undefined,
  });
  atualizarOpcoesDeDependeDe();

  if (listaDeEquipamentos.length < 2) {
    mostrarMensagem("Cadastre pelo menos dois equipamentos para criar dependências.", "aviso");
  }

  try {
    await carregar();
  } catch (erro) {
    mostrarErro(erro);
  }
}

iniciar();

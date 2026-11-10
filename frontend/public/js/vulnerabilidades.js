// Página de vulnerabilidades: catálogo (CRUD) e equipamentos afetados.

import { equipamentos, opcoes, vulnerabilidades } from "./api.js";
import {
  botao,
  confirmar,
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
  preencherFormulario,
  preencherSelect,
  preencherTabela,
} from "./ui.js";

const tabela = document.getElementById("tabela-vulnerabilidades");
const campoFiltro = document.getElementById("filtro");

const dialogo = document.getElementById("dialogo-vulnerabilidade");
const formulario = document.getElementById("formulario-vulnerabilidade");
const tituloDoDialogo = document.getElementById("titulo-dialogo-vulnerabilidade");
const mensagensDoFormulario = document.getElementById("mensagens-formulario");

const dialogoAfetados = document.getElementById("dialogo-afetados");
const tabelaAfetados = document.getElementById("tabela-afetados");
const formularioAtribuir = document.getElementById("formulario-atribuir");
const mensagensAfetados = document.getElementById("mensagens-afetados");

let catalogo = [];
let rotulosDeStatus = new Map();
let rotulosDeSeveridade = new Map();
let idEmEdicao = null; // null = cadastro de uma nova vulnerabilidade
let vulnerabilidadeDosAfetados = null;

// --- Listagem ---------------------------------------------------------------

async function carregar() {
  catalogo = await vulnerabilidades.listar();
  exibir();
}

function exibir() {
  const termo = campoFiltro.value.trim().toLowerCase();
  const filtradas = catalogo.filter(
    (v) => v.descricao.toLowerCase().includes(termo) || v.categoria.toLowerCase().includes(termo),
  );
  const mensagemSeVazia = termo
    ? "Nenhuma vulnerabilidade corresponde ao filtro."
    : "Nenhuma vulnerabilidade cadastrada.";

  preencherTabela(
    tabela,
    filtradas.map((v) => [
      { conteudo: v.id, classe: "numero" },
      v.descricao,
      v.categoria,
      { conteudo: formatarNumero(v.nota_cvss, 1), classe: "numero" },
      etiquetaSeveridade(v.severidade, rotulosDeSeveridade),
      etiquetaStatus(v.status, rotulosDeStatus),
      botao(`${v.ids_dos_equipamentos_afetados.length} equip.`, () => abrirAfetados(v)),
      el(
        "div",
        { class: "acoes-grupo" },
        botao("Editar", () => abrirFormulario(v)),
        botao("Excluir", () => excluir(v), "botao-perigo"),
      ),
    ]),
    mensagemSeVazia,
  );
}

// --- Cadastro e edição ------------------------------------------------------

function abrirFormulario(vulnerabilidade = null) {
  formulario.reset();
  limparMensagens(mensagensDoFormulario);
  idEmEdicao = vulnerabilidade?.id ?? null;
  tituloDoDialogo.textContent = vulnerabilidade
    ? `Editar vulnerabilidade #${vulnerabilidade.id}`
    : "Nova vulnerabilidade";
  if (vulnerabilidade) {
    preencherFormulario(formulario, vulnerabilidade);
  }
  dialogo.showModal();
}

async function salvar(evento) {
  // O navegador só dispara 'submit' se os campos passarem nas regras do HTML
  // (required, min, max, pattern...). As demais regras ficam com a API.
  evento.preventDefault();
  limparMensagens(mensagensDoFormulario);
  const dados = lerFormulario(formulario);
  dados.nota_cvss = Number(dados.nota_cvss);

  try {
    await emAndamento(evento.submitter, async () => {
      if (idEmEdicao === null) {
        const nova = await vulnerabilidades.cadastrar(dados);
        mostrarMensagem(`Vulnerabilidade #${nova.id} cadastrada.`, "sucesso");
      } else {
        await vulnerabilidades.atualizar(idEmEdicao, dados);
        mostrarMensagem(`Vulnerabilidade #${idEmEdicao} atualizada.`, "sucesso");
      }
    });
    dialogo.close();
    await carregar();
  } catch (erro) {
    mostrarErro(erro, mensagensDoFormulario);
  }
}

// --- Exclusão ---------------------------------------------------------------

async function excluir(vulnerabilidade) {
  const quantidade = vulnerabilidade.ids_dos_equipamentos_afetados.length;
  const confirmado = await confirmar({
    titulo: "Excluir vulnerabilidade",
    mensagem:
      `A vulnerabilidade #${vulnerabilidade.id} "${vulnerabilidade.descricao}" será excluída do catálogo` +
      (quantidade ? ` e removida de ${quantidade} equipamento(s).` : "."),
    textoConfirmar: "Excluir",
    perigo: true,
  });
  if (!confirmado) return;

  limparMensagens();
  try {
    await vulnerabilidades.excluir(vulnerabilidade.id);
    mostrarMensagem(`Vulnerabilidade #${vulnerabilidade.id} excluída.`, "sucesso");
    await carregar();
  } catch (erro) {
    mostrarErro(erro);
  }
}

// --- Equipamentos afetados --------------------------------------------------

async function abrirAfetados(vulnerabilidade) {
  vulnerabilidadeDosAfetados = vulnerabilidade;
  limparMensagens(mensagensAfetados);
  document.getElementById("descricao-afetados").textContent =
    `#${vulnerabilidade.id} · ${vulnerabilidade.descricao}`;
  mostrarCarregandoNaTabela(tabelaAfetados);
  if (!dialogoAfetados.open) dialogoAfetados.showModal();
  await carregarAfetados();
}

async function carregarAfetados() {
  const id = vulnerabilidadeDosAfetados.id;
  try {
    const [afetados, todos] = await Promise.all([
      vulnerabilidades.listarEquipamentosAfetados(id),
      equipamentos.listar(),
    ]);

    preencherTabela(
      tabelaAfetados,
      afetados.map((equipamento) => [
        el("a", { href: `equipamento.html?id=${equipamento.id}`, texto: equipamento.nome }),
        equipamento.tipo,
        el(
          "div",
          { class: "acoes-grupo" },
          botao("Remover", () => removerDoEquipamento(equipamento), "botao-perigo"),
        ),
      ]),
      "Esta vulnerabilidade não afeta nenhum equipamento.",
    );

    const idsAfetados = new Set(afetados.map((equipamento) => equipamento.id));
    const disponiveis = todos.filter((equipamento) => !idsAfetados.has(equipamento.id));
    const select = formularioAtribuir.elements.namedItem("equipamento_id");
    preencherSelect(select, disponiveis, {
      valor: (equipamento) => equipamento.id,
      rotulo: (equipamento) => `${equipamento.nome} (${equipamento.tipo})`,
      vazio: disponiveis.length ? "Selecione…" : "Todos os equipamentos já são afetados",
    });
    formularioAtribuir.querySelector("button").disabled = disponiveis.length === 0;
  } catch (erro) {
    mostrarErro(erro, mensagensAfetados);
  }
}

async function atribuir(evento) {
  evento.preventDefault();
  limparMensagens(mensagensAfetados);
  const equipamentoId = Number(lerFormulario(formularioAtribuir).equipamento_id);
  try {
    await emAndamento(evento.submitter, () =>
      equipamentos.atribuirVulnerabilidade(equipamentoId, vulnerabilidadeDosAfetados.id),
    );
    mostrarMensagem("Vulnerabilidade atribuída ao equipamento.", "sucesso", mensagensAfetados);
    await Promise.all([carregarAfetados(), carregar()]);
  } catch (erro) {
    mostrarErro(erro, mensagensAfetados);
  }
}

async function removerDoEquipamento(equipamento) {
  limparMensagens(mensagensAfetados);
  try {
    await equipamentos.removerVulnerabilidade(equipamento.id, vulnerabilidadeDosAfetados.id);
    mostrarMensagem(
      `Removida de "${equipamento.nome}". Ela continua no catálogo.`,
      "sucesso",
      mensagensAfetados,
    );
    await Promise.all([carregarAfetados(), carregar()]);
  } catch (erro) {
    mostrarErro(erro, mensagensAfetados);
  }
}

// --- Início -----------------------------------------------------------------

async function iniciar() {
  document.getElementById("botao-nova").addEventListener("click", () => abrirFormulario());
  campoFiltro.addEventListener("input", exibir);
  formulario.addEventListener("submit", salvar);
  formularioAtribuir.addEventListener("submit", atribuir);

  mostrarCarregandoNaTabela(tabela);
  try {
    const [status, severidades] = await Promise.all([
      opcoes.statusDeVulnerabilidade(),
      opcoes.severidades(),
    ]);
    rotulosDeStatus = mapaDeRotulos(status);
    rotulosDeSeveridade = mapaDeRotulos(severidades);
    preencherSelect(formulario.elements.namedItem("status"), status, {
      valor: (opcao) => opcao.valor,
      rotulo: (opcao) => opcao.rotulo,
    });
    await carregar();
  } catch (erro) {
    preencherTabela(tabela, [], "Não foi possível carregar as vulnerabilidades.");
    mostrarErro(erro);
  }
}

iniciar();

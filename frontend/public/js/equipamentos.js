// Página de equipamentos: listagem com busca por nome, cadastro, edição e
// exclusão. Abrir "equipamentos.html?editar=ID" abre direto a edição (usado
// pelo botão "Editar" da página de detalhes).

import { equipamentos, opcoes } from "./api.js";
import {
  atrasar,
  botao,
  confirmar,
  el,
  emAndamento,
  formatarNumero,
  lerFormulario,
  limparMensagens,
  mostrarCarregandoNaTabela,
  mostrarErro,
  mostrarMensagem,
  parametroDaUrl,
  preencherFormulario,
  preencherSelect,
  preencherTabela,
} from "./ui.js";

const tabela = document.getElementById("tabela-equipamentos");
const campoBusca = document.getElementById("busca");

const dialogo = document.getElementById("dialogo-equipamento");
const formulario = document.getElementById("formulario-equipamento");
const tituloDoDialogo = document.getElementById("titulo-dialogo-equipamento");
const mensagensDoFormulario = document.getElementById("mensagens-formulario");
const campoNome = formulario.elements.namedItem("nome");

let idEmEdicao = null; // null = cadastro de um novo equipamento

// --- Listagem ---------------------------------------------------------------

async function carregar() {
  const termo = campoBusca.value.trim();
  try {
    // A busca por nome é feita pela própria API (GET /equipamentos?nome=...).
    const lista = await equipamentos.listar(termo);
    preencherTabela(
      tabela,
      lista.map((equipamento) => [
        { conteudo: equipamento.id, classe: "numero" },
        el("a", { href: `equipamento.html?id=${equipamento.id}`, texto: equipamento.nome }),
        equipamento.tipo,
        equipamento.responsavel,
        equipamento.setor,
        { conteudo: equipamento.quantidade_de_vulnerabilidades, classe: "numero" },
        el(
          "div",
          { class: "acoes-grupo" },
          botao("Editar", () => abrirFormulario(equipamento)),
          botao("Excluir", () => excluir(equipamento), "botao-perigo"),
        ),
      ]),
      termo ? `Nenhum equipamento com "${termo}" no nome.` : "Nenhum equipamento cadastrado.",
    );
  } catch (erro) {
    preencherTabela(tabela, [], "Não foi possível carregar os equipamentos.");
    mostrarErro(erro);
  }
}

// --- Cadastro e edição ------------------------------------------------------

function abrirFormulario(equipamento = null) {
  formulario.reset();
  limparMensagens(mensagensDoFormulario);
  idEmEdicao = equipamento?.id ?? null;

  // O nome não pode mudar depois do cadastro (regra da API).
  const editando = equipamento !== null;
  campoNome.readOnly = editando;
  document.getElementById("dica-nome").hidden = !editando;
  tituloDoDialogo.textContent = editando ? `Editar equipamento #${equipamento.id}` : "Novo equipamento";

  if (editando) {
    preencherFormulario(formulario, equipamento);
  }
  dialogo.showModal();
}

async function salvar(evento) {
  evento.preventDefault();
  limparMensagens(mensagensDoFormulario);
  const dados = lerFormulario(formulario);

  try {
    await emAndamento(evento.submitter, async () => {
      if (idEmEdicao === null) {
        const novo = await equipamentos.cadastrar(dados);
        mostrarMensagem(`Equipamento "${novo.nome}" cadastrado com o ID ${novo.id}.`, "sucesso");
      } else {
        delete dados.nome; // a atualização não recebe o nome
        await equipamentos.atualizar(idEmEdicao, dados);
        mostrarMensagem(`Equipamento #${idEmEdicao} atualizado.`, "sucesso");
      }
    });
    dialogo.close();
    await carregar();
  } catch (erro) {
    mostrarErro(erro, mensagensDoFormulario);
  }
}

// --- Exclusão ---------------------------------------------------------------

async function excluir(equipamento) {
  limparMensagens();
  let exclusivas;
  try {
    // Vulnerabilidades que só afetam este equipamento: serão excluídas junto.
    exclusivas = await equipamentos.listarVulnerabilidadesExclusivas(equipamento.id);
  } catch (erro) {
    mostrarErro(erro);
    return;
  }

  const detalhes = exclusivas.length
    ? el(
        "div",
        {},
        el("p", {
          class: "texto-suave",
          texto: "Estas vulnerabilidades só afetam este equipamento e também serão excluídas:",
        }),
        el(
          "ul",
          { class: "lista-simples" },
          exclusivas.map((v) =>
            el("li", {}, `#${v.id} ${v.descricao} (CVSS ${formatarNumero(v.nota_cvss, 1)})`),
          ),
        ),
      )
    : el("p", {
        class: "texto-suave",
        texto: "Nenhuma vulnerabilidade será excluída: as que afetam este equipamento também afetam outros.",
      });

  const confirmado = await confirmar({
    titulo: "Excluir equipamento",
    mensagem: `O equipamento #${equipamento.id} "${equipamento.nome}" e as dependências dele serão excluídos.`,
    detalhes,
    textoConfirmar: "Excluir",
    perigo: true,
  });
  if (!confirmado) return;

  try {
    const resultado = await equipamentos.excluir(equipamento.id);
    const quantidade = resultado.ids_das_vulnerabilidades_excluidas.length;
    mostrarMensagem(
      `Equipamento "${equipamento.nome}" excluído` +
        (quantidade ? ` junto com ${quantidade} vulnerabilidade(s) exclusiva(s).` : "."),
      "sucesso",
    );
    await carregar();
  } catch (erro) {
    mostrarErro(erro);
  }
}

// --- Início -----------------------------------------------------------------

async function abrirEdicaoPelaUrl() {
  const id = parametroDaUrl("editar");
  if (!id) return;
  try {
    abrirFormulario(await equipamentos.buscar(Number(id)));
  } catch (erro) {
    mostrarErro(erro);
  }
}

async function iniciar() {
  document.getElementById("botao-novo").addEventListener("click", () => abrirFormulario());
  campoBusca.addEventListener("input", atrasar(carregar));
  formulario.addEventListener("submit", salvar);

  mostrarCarregandoNaTabela(tabela);
  try {
    const tipos = await opcoes.tiposDeEquipamento();
    preencherSelect(formulario.elements.namedItem("classe"), tipos, {
      valor: (tipo) => tipo.classe,
      rotulo: (tipo) => `${tipo.rotulo} (exposição ${formatarNumero(tipo.fator_de_exposicao, 1)})`,
      vazio: "Selecione…",
    });
  } catch (erro) {
    preencherTabela(tabela, [], "API indisponível.");
    mostrarErro(erro);
    return;
  }
  await carregar();
  await abrirEdicaoPelaUrl();
}

iniciar();

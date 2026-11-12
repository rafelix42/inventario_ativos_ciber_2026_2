// Funções de interface usadas por todas as páginas: criar elementos,
// preencher tabelas e listas de seleção, exibir mensagens e diálogos.
//
// SEGURANÇA: os dados vindos da API são sempre inseridos como texto
// (textContent / createTextNode), nunca como HTML (innerHTML). Assim, mesmo
// que um texto cadastrado contenha algo como "<script>", ele aparece na tela
// como texto e não é executado (proteção contra XSS).

// --- Criação de elementos ---------------------------------------------------

// Cria um elemento. Exemplo:
//   el("a", { href: "x.html", class: "botao" }, "Abrir")
// 'propriedades' aceita: class, texto, dataset (objeto), on (objeto de
// eventos) e qualquer atributo HTML. Os filhos podem ser elementos ou textos.
export function el(tag, propriedades = {}, ...filhos) {
  const elemento = document.createElement(tag);
  for (const [nome, valor] of Object.entries(propriedades)) {
    if (valor === undefined || valor === null || valor === false) continue;
    if (nome === "class") elemento.className = valor;
    else if (nome === "texto") elemento.textContent = valor;
    else if (nome === "dataset") Object.assign(elemento.dataset, valor);
    else if (nome === "on") {
      for (const [evento, funcao] of Object.entries(valor)) {
        elemento.addEventListener(evento, funcao);
      }
    } else if (valor === true) elemento.setAttribute(nome, "");
    else elemento.setAttribute(nome, valor);
  }
  for (const filho of filhos.flat()) {
    if (filho === undefined || filho === null || filho === false) continue;
    elemento.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  }
  return elemento;
}

export function botao(texto, aoClicar, classe = "") {
  return el("button", {
    type: "button",
    class: `botao botao-pequeno ${classe}`.trim(),
    texto,
    on: { click: aoClicar },
  });
}

// --- Formatação -------------------------------------------------------------

const formatadores = new Map();

export function formatarNumero(numero, casas = 2) {
  if (!formatadores.has(casas)) {
    formatadores.set(
      casas,
      new Intl.NumberFormat("pt-BR", {
        minimumFractionDigits: casas,
        maximumFractionDigits: casas,
      }),
    );
  }
  return formatadores.get(casas).format(numero);
}

// Transforma uma lista de opções da API ([{valor, rotulo}]) em um Map
// valor -> rótulo, para exibir o rótulo a partir do valor.
export function mapaDeRotulos(opcoes) {
  return new Map(opcoes.map((opcao) => [opcao.valor, opcao.rotulo]));
}

export function etiquetaSeveridade(valor, rotulos) {
  return el("span", { class: `etiqueta sev-${valor}`, texto: rotulos?.get(valor) ?? valor });
}

export function etiquetaStatus(valor, rotulos) {
  return el("span", { class: `etiqueta status-${valor}`, texto: rotulos?.get(valor) ?? valor });
}

// Barra horizontal com o risco próprio (sólido) e o herdado (listrado).
// 'maximo' é o maior risco efetivo da lista: a barra dele ocupa 100%.
export function barraDeRisco(riscoProprio, riscoHerdado, maximo) {
  const porcentagem = (valor) => (maximo > 0 ? (Math.max(valor, 0) / maximo) * 100 : 0);
  const propria = el("span", { class: "parte-propria" });
  const herdada = el("span", { class: "parte-herdada" });
  // Alterar estilos pelo JavaScript é permitido pela CSP (só o atributo
  // style escrito no HTML é bloqueado).
  propria.style.width = `${porcentagem(riscoProprio)}%`;
  herdada.style.width = `${porcentagem(riscoHerdado)}%`;
  return el(
    "div",
    {
      class: "barra-risco",
      role: "img",
      "aria-label": `Risco próprio ${formatarNumero(riscoProprio)}, herdado ${formatarNumero(riscoHerdado)}`,
    },
    propria,
    herdada,
  );
}

// --- Tabelas e listas de seleção --------------------------------------------

// Preenche o <tbody> de uma tabela. Cada linha é uma lista de células; cada
// célula pode ser um texto, um número, um elemento ou {conteudo, classe}.
// Em telas estreitas, o CSS usa o atributo data-label (nome da coluna, lido
// do <thead>) para exibir cada linha como um cartão.
export function preencherTabela(tabela, linhas, mensagemSeVazia) {
  const titulos = [...tabela.querySelectorAll("thead th")].map((th) => th.textContent.trim());
  const corpo = tabela.tBodies[0] ?? tabela.appendChild(document.createElement("tbody"));
  corpo.replaceChildren();

  if (linhas.length === 0) {
    corpo.append(
      el("tr", {}, el("td", { class: "vazio", colspan: titulos.length || 1, texto: mensagemSeVazia })),
    );
    return;
  }

  for (const linha of linhas) {
    const tr = el("tr");
    linha.forEach((celula, indice) => {
      const ehObjeto = celula !== null && typeof celula === "object" && !(celula instanceof Node);
      const conteudo = ehObjeto ? celula.conteudo : celula;
      tr.append(
        el("td", { class: ehObjeto ? celula.classe : undefined, "data-label": titulos[indice] ?? "" }, conteudo),
      );
    });
    corpo.append(tr);
  }
}

export function mostrarCarregandoNaTabela(tabela) {
  const colunas = tabela.querySelectorAll("thead th").length || 1;
  tabela.tBodies[0].replaceChildren(
    el("tr", {}, el("td", { class: "vazio", colspan: colunas }, el("span", { class: "carregando", texto: "carregando" }))),
  );
}

// Preenche um <select>. 'valor' e 'rotulo' são funções que recebem um item.
// 'vazio' (opcional) é o texto de uma primeira opção sem valor.
export function preencherSelect(select, itens, { valor, rotulo, vazio, selecionado } = {}) {
  select.replaceChildren();
  if (vazio !== undefined) {
    select.append(el("option", { value: "", texto: vazio }));
  }
  for (const item of itens) {
    const opcao = el("option", { value: valor(item), texto: rotulo(item) });
    if (selecionado !== undefined && String(valor(item)) === String(selecionado)) {
      opcao.selected = true;
    }
    select.append(opcao);
  }
}

// --- Formulários ------------------------------------------------------------

export function lerFormulario(formulario) {
  return Object.fromEntries(new FormData(formulario));
}

export function preencherFormulario(formulario, valores) {
  for (const [nome, valor] of Object.entries(valores)) {
    const campo = formulario.elements.namedItem(nome);
    if (campo) campo.value = valor ?? "";
  }
}

// Desativa o botão enquanto a ação roda, para evitar clique duplo (e, com
// isso, cadastro duplicado).
export async function emAndamento(botaoDaAcao, acao) {
  if (botaoDaAcao) botaoDaAcao.disabled = true;
  try {
    return await acao();
  } finally {
    if (botaoDaAcao) botaoDaAcao.disabled = false;
  }
}

// Só executa 'funcao' depois que o usuário para de digitar por 'espera' ms.
export function atrasar(funcao, espera = 300) {
  let temporizador;
  return (...argumentos) => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => funcao(...argumentos), espera);
  };
}

export function parametroDaUrl(nome) {
  return new URLSearchParams(window.location.search).get(nome);
}

// --- Mensagens --------------------------------------------------------------

// Área padrão de mensagens da página. Os diálogos têm a sua própria área
// (passada no parâmetro 'area'), porque, com um diálogo aberto, o resto da
// página fica escondido atrás do fundo escuro.
function areaDeMensagens() {
  return document.getElementById("mensagens");
}

// tipo: "info", "sucesso", "aviso" ou "erro". Mensagens de sucesso somem
// sozinhas; as demais ficam até o usuário fechar ou a próxima ação.
export function mostrarMensagem(texto, tipo = "info", area = areaDeMensagens()) {
  if (!area) return;
  const mensagem = el(
    "div",
    { class: `mensagem mensagem-${tipo}`, role: tipo === "erro" ? "alert" : undefined },
    el("span", { class: "mensagem-texto", texto }),
    el("button", {
      type: "button",
      class: "mensagem-fechar",
      "aria-label": "Fechar mensagem",
      texto: "×",
      on: { click: () => mensagem.remove() },
    }),
  );
  area.append(mensagem);
  if (tipo === "sucesso") {
    setTimeout(() => mensagem.remove(), 6000);
  }
}

export function mostrarErro(erro, area = areaDeMensagens()) {
  if (erro?.name !== "ErroDaApi") {
    console.error(erro);
  }
  mostrarMensagem(erro?.message ?? String(erro), "erro", area);
}

export function limparMensagens(area = areaDeMensagens()) {
  area?.replaceChildren();
}

// --- Diálogos ---------------------------------------------------------------

// Qualquer botão com o atributo data-fechar fecha o diálogo em que está.
document.addEventListener("click", (evento) => {
  const botaoFechar = evento.target.closest("[data-fechar]");
  if (botaoFechar) botaoFechar.closest("dialog")?.close();
});

let dialogoDeConfirmacao;

function criarDialogoDeConfirmacao() {
  const titulo = el("h2", { id: "confirmacao-titulo" });
  const corpo = el("div", { class: "dialogo-corpo" });
  const botaoCancelar = el("button", { type: "button", class: "botao", texto: "Cancelar", value: "nao" });
  const botaoConfirmar = el("button", { type: "button", class: "botao", value: "sim" });
  const dialogo = el(
    "dialog",
    { "aria-labelledby": "confirmacao-titulo" },
    el("div", { class: "dialogo-cabecalho" }, titulo),
    corpo,
    el("div", { class: "dialogo-rodape" }, botaoCancelar, botaoConfirmar),
  );
  botaoCancelar.addEventListener("click", () => dialogo.close("nao"));
  botaoConfirmar.addEventListener("click", () => dialogo.close("sim"));
  document.body.append(dialogo);
  return { dialogo, titulo, corpo, botaoConfirmar, botaoCancelar };
}

// Abre um diálogo de confirmação e devolve uma Promise com true (confirmou)
// ou false (cancelou, apertou Esc ou fechou). Substitui o confirm() do
// navegador, que não pode ser estilizado.
export function confirmar({ titulo, mensagem, detalhes, textoConfirmar = "Confirmar", perigo = false }) {
  dialogoDeConfirmacao ??= criarDialogoDeConfirmacao();
  const partes = dialogoDeConfirmacao;

  partes.titulo.textContent = titulo;
  partes.corpo.replaceChildren(el("p", { texto: mensagem }), detalhes ?? "");
  partes.botaoConfirmar.textContent = textoConfirmar;
  partes.botaoConfirmar.className = `botao ${perigo ? "botao-perigo" : "botao-primario"}`;

  return new Promise((resolver) => {
    partes.dialogo.returnValue = "nao";
    partes.dialogo.addEventListener(
      "close",
      () => resolver(partes.dialogo.returnValue === "sim"),
      { once: true },
    );
    partes.dialogo.showModal();
    partes.botaoCancelar.focus();
  });
}

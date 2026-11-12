// Comunicação com a API. É o único arquivo que usa fetch: as páginas chamam
// as funções exportadas aqui e não precisam saber montar URLs nem tratar
// códigos HTTP.
//
// Toda resposta de erro da API tem o formato {"detail": "mensagem"}. Aqui
// essa mensagem vira um ErroDaApi, que as páginas exibem diretamente.

import { API_URL } from "./config.js";

export class ErroDaApi extends Error {
  // 'status' é o código HTTP (404, 409, 422...) ou 0 se a API não respondeu.
  constructor(mensagem, status) {
    super(mensagem);
    this.name = "ErroDaApi";
    this.status = status;
  }
}

async function requisitar(metodo, caminho, corpo) {
  const opcoes = { method: metodo, headers: { Accept: "application/json" } };
  if (corpo !== undefined) {
    opcoes.headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(corpo);
  }

  let resposta;
  try {
    resposta = await fetch(API_URL + caminho, opcoes);
  } catch {
    // fetch só falha assim quando não há resposta: API fora do ar, endereço
    // errado ou bloqueio de CORS.
    throw new ErroDaApi(
      `Não foi possível conectar à API em ${API_URL}. Verifique se ela está no ar.`,
      0,
    );
  }

  // 204 = sucesso sem conteúdo (exclusões e atribuições).
  if (resposta.status === 204) {
    return null;
  }

  const dados = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    const mensagem = dados?.detail ?? `A API respondeu com o erro ${resposta.status}.`;
    throw new ErroDaApi(mensagem, resposta.status);
  }
  return dados;
}

// --- Equipamentos -----------------------------------------------------------

export const equipamentos = {
  listar: (nome = "") =>
    requisitar("GET", `/equipamentos?nome=${encodeURIComponent(nome)}`),
  buscar: (id) => requisitar("GET", `/equipamentos/${id}`),
  cadastrar: (dados) => requisitar("POST", "/equipamentos", dados),
  atualizar: (id, dados) => requisitar("PUT", `/equipamentos/${id}`, dados),
  excluir: (id) => requisitar("DELETE", `/equipamentos/${id}`),

  listarVulnerabilidades: (id) =>
    requisitar("GET", `/equipamentos/${id}/vulnerabilidades`),
  listarVulnerabilidadesExclusivas: (id) =>
    requisitar("GET", `/equipamentos/${id}/vulnerabilidades-exclusivas`),
  atribuirVulnerabilidade: (id, vulnerabilidadeId) =>
    requisitar("POST", `/equipamentos/${id}/vulnerabilidades/${vulnerabilidadeId}`),
  removerVulnerabilidade: (id, vulnerabilidadeId) =>
    requisitar("DELETE", `/equipamentos/${id}/vulnerabilidades/${vulnerabilidadeId}`),
};

// --- Vulnerabilidades -------------------------------------------------------

export const vulnerabilidades = {
  listar: () => requisitar("GET", "/vulnerabilidades"),
  buscar: (id) => requisitar("GET", `/vulnerabilidades/${id}`),
  cadastrar: (dados) => requisitar("POST", "/vulnerabilidades", dados),
  atualizar: (id, dados) => requisitar("PUT", `/vulnerabilidades/${id}`, dados),
  excluir: (id) => requisitar("DELETE", `/vulnerabilidades/${id}`),
  listarEquipamentosAfetados: (id) =>
    requisitar("GET", `/vulnerabilidades/${id}/equipamentos`),
};

// --- Dependências -----------------------------------------------------------

export const dependencias = {
  listar: () => requisitar("GET", "/dependencias"),
  listarDoEquipamento: (equipamentoId) =>
    requisitar("GET", `/dependencias?equipamento_id=${equipamentoId}`),
  salvar: (equipamentoId, dependeDeId, fator) =>
    requisitar("PUT", `/dependencias/${equipamentoId}/${dependeDeId}`, { fator }),
  excluir: (equipamentoId, dependeDeId) =>
    requisitar("DELETE", `/dependencias/${equipamentoId}/${dependeDeId}`),
};

// --- Análise de risco -------------------------------------------------------

export const analiseDeRisco = {
  calcular: () => requisitar("GET", "/analise-de-risco"),
  doEquipamento: (id) => requisitar("GET", `/analise-de-risco/equipamentos/${id}`),
  matrizes: () => requisitar("GET", "/analise-de-risco/matrizes"),
};

// --- Opções fixas e saúde ---------------------------------------------------

export const opcoes = {
  tiposDeEquipamento: () => requisitar("GET", "/tipos-de-equipamento"),
  statusDeVulnerabilidade: () => requisitar("GET", "/status-de-vulnerabilidade"),
  severidades: () => requisitar("GET", "/severidades"),
  saude: () => requisitar("GET", "/saude"),
};

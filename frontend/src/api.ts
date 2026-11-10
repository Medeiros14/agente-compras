import type { Requisicao, RespostaPedido } from "./tipos";

const BASE = "/api";

/** Erro já com mensagem pronta para mostrar ao usuário. */
export class ErroApi extends Error {}

async function requisitar<T>(caminho: string, opcoes?: RequestInit): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(BASE + caminho, opcoes);
  } catch {
    throw new ErroApi("Não foi possível conectar ao servidor. Verifique se o backend está no ar.");
  }

  const corpo = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    // Formato de erro do backend: {"erro": {"codigo", "mensagem"}}
    const mensagem = corpo?.erro?.mensagem;
    if (mensagem) throw new ErroApi(mensagem);
    if (resposta.status === 422) throw new ErroApi("Pedido inválido: escreva entre 3 e 1000 caracteres.");
    // 502/503/504 sem corpo JSON vêm do nginx: o backend não respondeu.
    if ([502, 503, 504].includes(resposta.status)) {
      throw new ErroApi("O backend não está respondendo. Tente novamente em instantes.");
    }
    throw new ErroApi(`O servidor respondeu com erro (HTTP ${resposta.status}). Tente novamente.`);
  }
  return corpo as T;
}

export function enviarPedido(pedido: string): Promise<RespostaPedido> {
  return requisitar("/requisicoes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pedido }),
  });
}

export function listarRequisicoes(): Promise<Requisicao[]> {
  return requisitar("/requisicoes");
}

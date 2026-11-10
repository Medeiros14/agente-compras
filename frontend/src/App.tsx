import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";

import { ErroApi, enviarPedido, listarRequisicoes } from "./api";
import { CartaoRequisicao } from "./CartaoRequisicao";
import { Carregando } from "./Carregando";
import { EstadoVazio } from "./EstadoVazio";
import { FerramentasChamadas } from "./FerramentasChamadas";
import { Historico } from "./Historico";
import { IconeAlerta, IconeEnviar, IconeInfo, IconeLista, IconeRecibo, IconeRepetir } from "./Icones";
import type { Requisicao, RespostaPedido } from "./tipos";

type Mensagem =
  | { tipo: "usuario"; texto: string }
  | { tipo: "agente"; resposta: RespostaPedido }
  | { tipo: "erro"; texto: string; pedido: string };

function mensagemDeErro(erro: unknown): string {
  return erro instanceof ErroApi ? erro.message : "Erro inesperado. Tente novamente.";
}

export default function App() {
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [texto, setTexto] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [historico, setHistorico] = useState<Requisicao[]>([]);
  const [erroHistorico, setErroHistorico] = useState<string | null>(null);
  const [historicoAberto, setHistoricoAberto] = useState(false);
  const fimDaConversa = useRef<HTMLDivElement>(null);
  const campo = useRef<HTMLTextAreaElement>(null);

  async function atualizarHistorico() {
    try {
      setHistorico(await listarRequisicoes());
      setErroHistorico(null);
    } catch (erro) {
      setErroHistorico(mensagemDeErro(erro));
    }
  }

  useEffect(() => {
    atualizarHistorico();
  }, []);

  useEffect(() => {
    fimDaConversa.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensagens, carregando]);

  async function enviar(pedido: string) {
    pedido = pedido.trim();
    if (pedido.length < 3 || carregando) return;

    setMensagens((atuais) => [...atuais, { tipo: "usuario", texto: pedido }]);
    setTexto("");
    setCarregando(true);
    try {
      const resposta = await enviarPedido(pedido);
      setMensagens((atuais) => [...atuais, { tipo: "agente", resposta }]);
      if (resposta.requisicao) atualizarHistorico();
    } catch (erro) {
      setMensagens((atuais) => [...atuais, { tipo: "erro", texto: mensagemDeErro(erro), pedido }]);
    } finally {
      setCarregando(false);
      campo.current?.focus();
    }
  }

  function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    enviar(texto);
  }

  function aoTeclar(evento: KeyboardEvent<HTMLTextAreaElement>) {
    if (evento.key === "Enter" && !evento.shiftKey && !evento.nativeEvent.isComposing) {
      evento.preventDefault();
      enviar(texto);
    }
  }

  const podeEnviar = !carregando && texto.trim().length >= 3;

  return (
    <div className="app">
      <header className="barra">
        <div className="marca">
          <span className="marca-simbolo">
            <IconeRecibo className="icone-18" />
          </span>
          <span className="marca-nome">Agente de compras</span>
        </div>
        <button
          type="button"
          className="botao-secundario so-celular"
          onClick={() => setHistoricoAberto(true)}
          aria-expanded={historicoAberto}
        >
          <IconeLista className="icone-18" />
          Requisições
          {historico.length > 0 && <span className="contador">{historico.length}</span>}
        </button>
      </header>

      <div className="corpo">
        <main className="chat">
          <section className="conversa" aria-live="polite">
            {mensagens.length === 0 && !carregando && <EstadoVazio aoEscolher={enviar} />}

            {mensagens.map((mensagem, indice) => {
              if (mensagem.tipo === "usuario") {
                return (
                  <div key={indice} className="pedido">
                    <p>{mensagem.texto}</p>
                  </div>
                );
              }

              if (mensagem.tipo === "erro") {
                return (
                  <div key={indice} className="resposta">
                    <div className="falha" role="alert">
                      <IconeAlerta className="icone-20 falha-icone" />
                      <div>
                        <p className="falha-titulo">Não foi possível processar o pedido</p>
                        <p className="falha-texto">{mensagem.texto}</p>
                        <button
                          type="button"
                          className="botao-secundario"
                          onClick={() => enviar(mensagem.pedido)}
                          disabled={carregando}
                        >
                          <IconeRepetir className="icone-16" />
                          Tentar de novo
                        </button>
                      </div>
                    </div>
                  </div>
                );
              }

              const { resposta, requisicao, ferramentas_chamadas } = mensagem.resposta;
              return (
                <div key={indice} className="resposta">
                  {requisicao ? (
                    <>
                      <CartaoRequisicao requisicao={requisicao} />
                      <p className="justificativa">{resposta}</p>
                    </>
                  ) : (
                    <div className="sem-requisicao">
                      <IconeInfo className="icone-20 sem-requisicao-icone" />
                      <div>
                        <p className="sem-requisicao-titulo">Nenhuma requisição foi criada</p>
                        <p className="sem-requisicao-texto">{resposta}</p>
                      </div>
                    </div>
                  )}
                  <FerramentasChamadas chamadas={ferramentas_chamadas} />
                </div>
              );
            })}

            {carregando && <Carregando />}
            <div ref={fimDaConversa} />
          </section>

          <form className="compositor" onSubmit={aoEnviar}>
            <div className="compositor-caixa">
              <textarea
                ref={campo}
                value={texto}
                onChange={(evento) => setTexto(evento.target.value)}
                onKeyDown={aoTeclar}
                placeholder="Ex.: 3 laptops até US$ 2.000 cada"
                maxLength={1000}
                rows={1}
                disabled={carregando}
                aria-label="Pedido de compra"
              />
              <button type="submit" className="botao-enviar" disabled={!podeEnviar} aria-label="Enviar pedido">
                <IconeEnviar className="icone-20" />
              </button>
            </div>
            <p className="compositor-dica">
              <kbd>Enter</kbd> envia · <kbd>Shift</kbd>+<kbd>Enter</kbd> quebra a linha
            </p>
          </form>
        </main>

        <Historico
          requisicoes={historico}
          erro={erroHistorico}
          aberto={historicoAberto}
          aoFechar={() => setHistoricoAberto(false)}
        />
        {historicoAberto && (
          <div className="veu so-celular" onClick={() => setHistoricoAberto(false)} aria-hidden="true" />
        )}
      </div>
    </div>
  );
}

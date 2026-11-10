import { useEffect, useRef, useState, type FormEvent } from "react";

import { enviarPedido, ErroApi, listarRequisicoes } from "./api";
import { CartaoRequisicao } from "./CartaoRequisicao";
import { Historico } from "./Historico";
import type { Requisicao, RespostaPedido } from "./tipos";

type Mensagem =
  | { tipo: "usuario"; texto: string }
  | { tipo: "agente"; resposta: RespostaPedido }
  | { tipo: "erro"; texto: string };

const EXEMPLOS = [
  "Preciso de 3 laptops para o time de vendas, até US$ 2.000 cada.",
  "Quero 2 smartphones de até US$ 300 cada.",
  "Preciso de 5 laptops de no máximo US$ 500 cada.",
];

function mensagemDeErro(erro: unknown): string {
  return erro instanceof ErroApi ? erro.message : "Erro inesperado. Tente novamente.";
}

export default function App() {
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [texto, setTexto] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [historico, setHistorico] = useState<Requisicao[]>([]);
  const [erroHistorico, setErroHistorico] = useState<string | null>(null);
  const fimDaConversa = useRef<HTMLDivElement>(null);

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
    fimDaConversa.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens, carregando]);

  async function enviar(pedido: string) {
    pedido = pedido.trim();
    if (!pedido || carregando) return;

    setMensagens((atuais) => [...atuais, { tipo: "usuario", texto: pedido }]);
    setTexto("");
    setCarregando(true);
    try {
      const resposta = await enviarPedido(pedido);
      setMensagens((atuais) => [...atuais, { tipo: "agente", resposta }]);
      if (resposta.requisicao) atualizarHistorico();
    } catch (erro) {
      setMensagens((atuais) => [...atuais, { tipo: "erro", texto: mensagemDeErro(erro) }]);
    } finally {
      setCarregando(false);
    }
  }

  function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    enviar(texto);
  }

  return (
    <div className="pagina">
      <main className="chat">
        <header>
          <h1>Agente de compras</h1>
          <p className="discreto">
            Descreva o que precisa. O agente busca no catálogo, escolhe os itens e cria a requisição.
          </p>
        </header>

        <section className="conversa">
          {mensagens.length === 0 && (
            <div className="exemplos">
              <p className="discreto">Experimente:</p>
              {EXEMPLOS.map((exemplo) => (
                <button key={exemplo} type="button" onClick={() => enviar(exemplo)}>
                  {exemplo}
                </button>
              ))}
            </div>
          )}

          {mensagens.map((m, i) => {
            if (m.tipo === "usuario") {
              return <div key={i} className="balao balao-usuario">{m.texto}</div>;
            }
            if (m.tipo === "erro") {
              return (
                <div key={i} className="balao balao-erro" role="alert">
                  <strong>Não foi possível processar o pedido.</strong>
                  <p>{m.texto}</p>
                </div>
              );
            }
            const { resposta, requisicao } = m.resposta;
            return (
              <div key={i} className="balao balao-agente">
                {requisicao ? (
                  <CartaoRequisicao requisicao={requisicao} />
                ) : (
                  <span className="selo selo-alerta">Nenhuma requisição foi criada</span>
                )}
                <p className="texto-agente">{resposta}</p>
              </div>
            );
          })}

          {carregando && (
            <div className="balao balao-agente discreto">Consultando o catálogo e montando a requisição…</div>
          )}
          <div ref={fimDaConversa} />
        </section>

        <form className="entrada" onSubmit={aoEnviar}>
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Ex.: Preciso de 3 laptops até US$ 2.000 cada"
            maxLength={1000}
            disabled={carregando}
            aria-label="Pedido de compra"
          />
          <button type="submit" disabled={carregando || texto.trim().length < 3}>
            Enviar
          </button>
        </form>
      </main>

      <Historico requisicoes={historico} erro={erroHistorico} />
    </div>
  );
}

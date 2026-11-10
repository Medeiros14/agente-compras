import { formatarData, formatarDolar } from "./formatar";
import { IconeX } from "./Icones";
import type { Requisicao } from "./tipos";

interface Props {
  requisicoes: Requisicao[];
  erro: string | null;
  aberto: boolean;
  aoFechar: () => void;
}

/** Requisições salvas (GET /requisicoes). Coluna fixa no desktop, painel deslizante no celular. */
export function Historico({ requisicoes, erro, aberto, aoFechar }: Props) {
  return (
    <aside className={`historico ${aberto ? "historico-aberto" : ""}`} aria-label="Requisições salvas">
      <header className="historico-topo">
        <h2>Requisições salvas</h2>
        <button type="button" className="botao-icone so-celular" onClick={aoFechar} aria-label="Fechar">
          <IconeX className="icone-20" />
        </button>
      </header>

      {erro && <p className="historico-aviso">{erro}</p>}
      {!erro && requisicoes.length === 0 && (
        <p className="historico-vazio">As requisições criadas pelo agente aparecem aqui.</p>
      )}

      <ul className="historico-lista">
        {requisicoes.map((requisicao) => (
          <li key={requisicao.id}>
            <div className="historico-linha">
              <span className="historico-numero">Nº {String(requisicao.id).padStart(4, "0")}</span>
              <span className="historico-valor">{formatarDolar(requisicao.valor_total)}</span>
            </div>
            <p className="historico-itens">
              {requisicao.itens.map((item) => `${item.quantidade}× ${item.titulo}`).join(", ")}
            </p>
            <time className="historico-data" dateTime={requisicao.criado_em}>
              {formatarData(requisicao.criado_em)}
            </time>
          </li>
        ))}
      </ul>
    </aside>
  );
}

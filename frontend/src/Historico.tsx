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
        {requisicoes.map((r) => (
          <li key={r.id}>
            <div className="historico-linha">
              <span className="historico-numero">Nº {String(r.id).padStart(4, "0")}</span>
              <span className="historico-valor">{formatarDolar(r.valor_total)}</span>
            </div>
            <p className="historico-itens">
              {r.itens.map((i) => `${i.quantidade}× ${i.titulo}`).join(", ")}
            </p>
            <time className="historico-data" dateTime={r.criado_em}>
              {formatarData(r.criado_em)}
            </time>
          </li>
        ))}
      </ul>
    </aside>
  );
}

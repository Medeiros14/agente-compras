import { formatarData, formatarDolar } from "./formatar";
import type { Requisicao } from "./tipos";

interface Props {
  requisicoes: Requisicao[];
  erro: string | null;
}

/** Lista das requisições salvas (GET /requisicoes). */
export function Historico({ requisicoes, erro }: Props) {
  return (
    <aside className="historico">
      <h2>Requisições salvas</h2>
      {erro && <p className="aviso-erro">{erro}</p>}
      {!erro && requisicoes.length === 0 && <p className="discreto">Nenhuma requisição ainda.</p>}
      <ul>
        {requisicoes.map((r) => (
          <li key={r.id}>
            <div className="historico-linha">
              <strong>#{r.id}</strong>
              <span>{formatarDolar(r.valor_total)}</span>
            </div>
            <div className="discreto">
              {r.itens.map((i) => `${i.quantidade}x ${i.titulo}`).join(", ")}
            </div>
            <div className="discreto pequeno">{formatarData(r.criado_em)}</div>
          </li>
        ))}
      </ul>
    </aside>
  );
}

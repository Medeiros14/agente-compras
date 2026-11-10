import { formatarData, formatarDolar } from "./formatar";
import { IconeCheck } from "./Icones";
import type { Requisicao } from "./tipos";

/** Comprovante da requisição, montado a partir dos dados gravados no banco (não do texto do LLM). */
export function CartaoRequisicao({ requisicao }: { requisicao: Requisicao }) {
  return (
    <article className="comprovante" aria-label={`Requisição número ${requisicao.id}`}>
      <header className="comprovante-topo">
        <div>
          <p className="comprovante-status">
            <IconeCheck className="icone-16" />
            Requisição criada
          </p>
          <h3 className="comprovante-numero">Nº {String(requisicao.id).padStart(4, "0")}</h3>
        </div>
        <time className="comprovante-data" dateTime={requisicao.criado_em}>
          {formatarData(requisicao.criado_em)}
        </time>
      </header>

      <ul className="comprovante-itens">
        {requisicao.itens.map((item, indice) => (
          <li key={indice}>
            <span className="item-titulo">{item.titulo}</span>
            <span className="item-calculo">
              {item.quantidade} × {formatarDolar(item.preco_unitario)}
              <span className="item-id">ID {item.produto_id}</span>
            </span>
            <span className="item-subtotal">{formatarDolar(item.subtotal)}</span>
          </li>
        ))}
      </ul>

      <footer className="comprovante-total">
        <span>Total</span>
        <strong>{formatarDolar(requisicao.valor_total)}</strong>
      </footer>
    </article>
  );
}

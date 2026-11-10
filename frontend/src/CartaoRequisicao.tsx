import { formatarDolar } from "./formatar";
import type { Requisicao } from "./tipos";

/** Mostra a requisição a partir dos dados gravados no banco (não do texto do LLM). */
export function CartaoRequisicao({ requisicao }: { requisicao: Requisicao }) {
  return (
    <div className="cartao">
      <div className="cartao-titulo">
        <span className="selo selo-ok">Requisição #{requisicao.id} criada</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th className="num">Qtd.</th>
            <th className="num">Preço unit.</th>
            <th className="num">Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {requisicao.itens.map((item) => (
            <tr key={item.produto_id}>
              <td>
                {item.titulo} <span className="discreto">(ID {item.produto_id})</span>
              </td>
              <td className="num">{item.quantidade}</td>
              <td className="num">{formatarDolar(item.preco_unitario)}</td>
              <td className="num">{formatarDolar(item.subtotal)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={3}>Total</td>
            <td className="num">{formatarDolar(requisicao.valor_total)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

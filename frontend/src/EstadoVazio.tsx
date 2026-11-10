import { IconeEnviar } from "./Icones";

const EXEMPLOS = [
  { pedido: "Preciso de 3 laptops para o time de vendas, até US$ 2.000 cada.", nota: "Orçamento por unidade" },
  { pedido: "Preciso de 6 cadeiras para a sala de reunião, orçamento total de US$ 3.500.", nota: "Orçamento total" },
  { pedido: "Preciso de 5 laptops de no máximo US$ 500 cada.", nota: "Nada no catálogo atende" },
];

/** Tela inicial: explica o que o agente faz e oferece pedidos de exemplo clicáveis. */
export function EstadoVazio({ aoEscolher }: { aoEscolher: (pedido: string) => void }) {
  return (
    <div className="vazio">
      <h2 className="vazio-titulo">O que você precisa comprar?</h2>
      <p className="vazio-texto">
        Descreva o produto, a quantidade e o orçamento. O agente consulta o catálogo, confere preço e
        estoque e registra a requisição de compra.
      </p>

      <ul className="vazio-exemplos" aria-label="Pedidos de exemplo">
        {EXEMPLOS.map((exemplo) => (
          <li key={exemplo.pedido}>
            <button type="button" onClick={() => aoEscolher(exemplo.pedido)}>
              <span className="exemplo-texto">{exemplo.pedido}</span>
              <span className="exemplo-nota">{exemplo.nota}</span>
              <IconeEnviar className="icone-18 exemplo-seta" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

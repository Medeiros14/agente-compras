// Espelha o contrato da API (backend/app/schemas.py).

export interface ItemRequisicao {
  produto_id: number;
  titulo: string;
  quantidade: number;
  preco_unitario: number;
  subtotal: number;
}

export interface Requisicao {
  id: number;
  pedido: string;
  valor_total: number;
  criado_em: string;
  itens: ItemRequisicao[];
}

export interface RespostaPedido {
  resposta: string;
  requisicao: Requisicao | null;
}

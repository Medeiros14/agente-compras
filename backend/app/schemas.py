"""Contrato da API (request/response)."""

from datetime import datetime

from pydantic import BaseModel, Field


class PedidoEntrada(BaseModel):
    pedido: str = Field(min_length=3, max_length=1000, examples=[
        "Preciso de 3 laptops para o time de vendas, até US$ 2.000 cada."
    ])


class ItemRequisicao(BaseModel):
    produto_id: int
    titulo: str
    quantidade: int
    preco_unitario: float
    subtotal: float


class Requisicao(BaseModel):
    id: int
    pedido: str
    valor_total: float
    criado_em: datetime
    itens: list[ItemRequisicao]


class RespostaPedido(BaseModel):
    resposta: str = Field(description="Texto final do agente.")
    requisicao: Requisicao | None = Field(
        description="Requisição gravada, ou null quando o agente não criou nenhuma "
        "(o motivo está em `resposta`)."
    )

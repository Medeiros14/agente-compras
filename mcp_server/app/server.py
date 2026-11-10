"""Servidor MCP de compras: expõe o catálogo da DummyJSON e a criação de requisições.

Toda ferramenta devolve um dicionário com "ok". Em caso de falha, "ok" é false
e "erro" traz {"codigo", "mensagem"}: o erro vira dado para o agente explicar
ao usuário, em vez de uma exceção que derrubaria a conversa.
"""

from decimal import ROUND_HALF_UP, Decimal

import psycopg
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from app import config, db, dummyjson
from app.dummyjson import ErroDummyJSON

mcp = FastMCP(
    "compras",
    host="0.0.0.0",
    port=config.MCP_PORT,
    # Sem estado entre chamadas: cada requisição HTTP é independente.
    stateless_http=True,
    json_response=True,
)


def erro(codigo: str, mensagem: str) -> dict:
    return {"ok": False, "erro": {"codigo": codigo, "mensagem": mensagem}}


def dinheiro(valor) -> Decimal:
    """Converte para Decimal com 2 casas (str() evita imprecisão do float)."""
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def formatar_dolar(valor) -> str:
    """Formato usado em toda a aplicação: US$ 1.099,99."""
    texto = f"{dinheiro(valor):,.2f}"  # 1,099.99
    return "US$ " + texto.replace(",", "_").replace(".", ",").replace("_", ".")


class ItemPedido(BaseModel):
    produto_id: int = Field(description="ID do produto na DummyJSON, obtido em buscar_produtos.")
    quantidade: int = Field(gt=0, description="Quantidade de unidades desejada.")


@mcp.tool()
async def buscar_produtos(termo: str) -> dict:
    """Busca produtos no catálogo pelo termo informado.

    O catálogo está em inglês: use termos em inglês (ex.: "laptop", "phone",
    "chair"). Se não houver resultado, tente sinônimos. Retorna id, título,
    preço (USD), estoque e quantidade mínima de cada produto.
    """
    if not termo.strip():
        return erro("TERMO_VAZIO", "Informe um termo de busca.")
    try:
        produtos = await dummyjson.buscar(termo.strip())
    except ErroDummyJSON as e:
        return erro(e.codigo, e.mensagem)

    resultado = {"ok": True, "termo": termo, "total": len(produtos), "produtos": produtos}
    if not produtos:
        resultado["mensagem"] = f"Nenhum produto encontrado para '{termo}'. Tente um sinônimo em inglês."
    return resultado


@mcp.tool()
async def detalhar_produto(produto_id: int) -> dict:
    """Consulta um produto pelo id para confirmar preço atual e estoque disponível."""
    try:
        produto = await dummyjson.obter_produto(produto_id)
    except ErroDummyJSON as e:
        return erro(e.codigo, e.mensagem)
    return {"ok": True, "produto": produto}


@mcp.tool()
async def criar_requisicao(
    pedido: str,
    itens: list[ItemPedido],
    orcamento_unitario_max: float | None = None,
    orcamento_total_max: float | None = None,
) -> dict:
    """Cria a requisição de compra no banco. Chame só depois de escolher os produtos.

    Informe apenas o id e a quantidade de cada item: o preço é consultado na
    DummyJSON por esta ferramenta e o total é calculado aqui. Passe o orçamento
    extraído do pedido (por unidade e/ou total) para que ele seja validado com
    os preços reais. Nada é gravado se algum item falhar na validação.

    Args:
        pedido: texto original do pedido do usuário.
        itens: produtos escolhidos (produto_id e quantidade).
        orcamento_unitario_max: preço máximo por unidade em USD, se houver.
        orcamento_total_max: valor máximo total em USD, se houver.
    """
    if not itens:
        return erro("ITENS_VAZIOS", "A requisição precisa de pelo menos um item.")

    itens_validados = []
    for item in itens:
        try:
            produto = await dummyjson.obter_produto(item.produto_id)
        except ErroDummyJSON as e:
            return erro(e.codigo, e.mensagem)

        preco = dinheiro(produto["price"])
        titulo = produto["title"]

        if item.quantidade > produto["stock"]:
            return erro(
                "ESTOQUE_INSUFICIENTE",
                f"'{titulo}' tem {produto['stock']} unidades em estoque; foram pedidas {item.quantidade}.",
            )
        if item.quantidade < produto["minimumOrderQuantity"]:
            return erro(
                "QUANTIDADE_ABAIXO_DO_MINIMO",
                f"'{titulo}' exige pedido mínimo de {produto['minimumOrderQuantity']} unidades.",
            )
        if orcamento_unitario_max is not None and preco > dinheiro(orcamento_unitario_max):
            return erro(
                "ORCAMENTO_EXCEDIDO",
                f"'{titulo}' custa {formatar_dolar(preco)} por unidade, acima do limite de "
                f"{formatar_dolar(orcamento_unitario_max)}.",
            )

        itens_validados.append(
            {
                "produto_id": produto["id"],
                "titulo": titulo,
                "quantidade": item.quantidade,
                "preco_unitario": preco,
                "subtotal": preco * item.quantidade,
            }
        )

    valor_total = sum((i["subtotal"] for i in itens_validados), Decimal("0.00"))
    if orcamento_total_max is not None and valor_total > dinheiro(orcamento_total_max):
        return erro(
            "ORCAMENTO_EXCEDIDO",
            f"O total seria {formatar_dolar(valor_total)}, acima do orçamento de "
            f"{formatar_dolar(orcamento_total_max)}.",
        )

    try:
        requisicao_id = await db.salvar_requisicao(pedido, itens_validados, valor_total)
    except psycopg.Error:
        return erro("BANCO_INDISPONIVEL", "Não foi possível gravar a requisição no banco de dados.")

    return {
        "ok": True,
        "requisicao_id": requisicao_id,
        "valor_total": float(valor_total),
        "itens": [
            {
                **i,
                "preco_unitario": float(i["preco_unitario"]),
                "subtotal": float(i["subtotal"]),
            }
            for i in itens_validados
        ],
    }


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """Usado pelo healthcheck do docker compose."""
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

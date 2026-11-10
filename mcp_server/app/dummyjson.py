"""Cliente da DummyJSON.

Toda falha de rede, timeout ou resposta inesperada vira um ErroDummyJSON com
um código estável. As ferramentas do MCP convertem esse erro em um resultado
estruturado ({"ok": false, "erro": {...}}) que o agente consegue explicar.
"""

import httpx

from app import config


class ErroDummyJSON(Exception):
    def __init__(self, codigo: str, mensagem: str):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


def resumir_produto(produto: dict) -> dict:
    """Mantém só os campos úteis para uma compra (economiza tokens do LLM)."""
    return {
        "id": produto["id"],
        "title": produto["title"],
        "brand": produto.get("brand"),
        "category": produto.get("category"),
        "price": produto["price"],
        "stock": produto["stock"],
        "minimumOrderQuantity": produto.get("minimumOrderQuantity", 1),
        "availabilityStatus": produto.get("availabilityStatus"),
    }


async def _consultar(caminho: str, parametros: dict | None = None) -> dict | None:
    """GET na DummyJSON: None em 404, ErroDummyJSON nas demais falhas."""
    try:
        async with httpx.AsyncClient(
            base_url=config.DUMMYJSON_URL, timeout=config.DUMMYJSON_TIMEOUT
        ) as cliente:
            resposta = await cliente.get(caminho, params=parametros)
    except httpx.TimeoutException as e:
        raise ErroDummyJSON(
            "DUMMYJSON_TIMEOUT",
            f"O catálogo de produtos (DummyJSON) não respondeu em {config.DUMMYJSON_TIMEOUT:g}s.",
        ) from e
    except httpx.HTTPError as e:
        raise ErroDummyJSON(
            "DUMMYJSON_INDISPONIVEL",
            "Não foi possível conectar ao catálogo de produtos (DummyJSON).",
        ) from e

    if resposta.status_code == 404:
        return None
    if resposta.status_code >= 400:
        raise ErroDummyJSON(
            "DUMMYJSON_ERRO",
            f"O catálogo de produtos (DummyJSON) respondeu com erro HTTP {resposta.status_code}.",
        )
    try:
        return resposta.json()
    except ValueError as e:
        raise ErroDummyJSON(
            "DUMMYJSON_RESPOSTA_INVALIDA",
            "O catálogo de produtos (DummyJSON) devolveu uma resposta inválida.",
        ) from e


async def buscar(termo: str) -> list[dict]:
    dados = await _consultar("/products/search", parametros={"q": termo, "limit": 20})
    produtos = (dados or {}).get("products", [])
    return [resumir_produto(produto) for produto in produtos]


async def obter_produto(produto_id: int) -> dict:
    dados = await _consultar(f"/products/{produto_id}")
    if dados is None:
        raise ErroDummyJSON(
            "PRODUTO_NAO_ENCONTRADO",
            f"O produto {produto_id} não existe no catálogo.",
        )
    return resumir_produto(dados)

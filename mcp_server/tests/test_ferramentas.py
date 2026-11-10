"""Testes das ferramentas do MCP.

Rodam sem chave de LLM e sem banco: a DummyJSON é mockada com respx e a
gravação no Postgres é substituída por uma função falsa (monkeypatch).
"""

import httpx
import psycopg
import pytest
import respx

from app import config, db
from app.server import ItemPedido, buscar_produtos, criar_requisicao, detalhar_produto, mcp

LAPTOP = {
    "id": 78,
    "title": "Apple MacBook Pro 14 Inch Space Grey",
    "brand": "Apple",
    "category": "laptops",
    "price": 1999.99,
    "stock": 24,
    "minimumOrderQuantity": 1,
    "availabilityStatus": "In Stock",
    "description": "campo extra que não deve ir para o agente",
}


@pytest.fixture
def dummyjson():
    with respx.mock(base_url=config.DUMMYJSON_URL, assert_all_called=False) as mock:
        yield mock


@pytest.fixture
def banco_falso(monkeypatch):
    """Substitui a gravação no Postgres e guarda o que seria gravado."""
    chamadas = []

    async def salvar(pedido, itens, valor_total):
        chamadas.append({"pedido": pedido, "itens": itens, "valor_total": valor_total})
        return 42

    monkeypatch.setattr(db, "salvar_requisicao", salvar)
    return chamadas


async def test_servidor_expoe_as_tres_ferramentas():
    nomes = {t.name for t in await mcp.list_tools()}
    assert nomes == {"buscar_produtos", "detalhar_produto", "criar_requisicao"}


# --- buscar_produtos ---------------------------------------------------------


async def test_buscar_produtos_sucesso(dummyjson):
    dummyjson.get("/products/search").respond(json={"products": [LAPTOP], "total": 1})

    resultado = await buscar_produtos("laptop")

    assert resultado["ok"] is True
    assert resultado["total"] == 1
    assert resultado["produtos"][0]["id"] == 78
    assert resultado["produtos"][0]["price"] == 1999.99
    assert "description" not in resultado["produtos"][0]  # resumo enxuto
    assert dummyjson.calls.last.request.url.params["q"] == "laptop"


async def test_buscar_produtos_sem_resultado_sugere_outro_termo(dummyjson):
    dummyjson.get("/products/search").respond(json={"products": [], "total": 0})

    resultado = await buscar_produtos("notebook")

    assert resultado["ok"] is True
    assert resultado["total"] == 0
    assert "sinônimo" in resultado["mensagem"]


async def test_buscar_produtos_timeout(dummyjson):
    dummyjson.get("/products/search").mock(side_effect=httpx.ReadTimeout("lento"))

    resultado = await buscar_produtos("laptop")

    assert resultado["ok"] is False
    assert resultado["erro"]["codigo"] == "DUMMYJSON_TIMEOUT"


async def test_buscar_produtos_erro_http(dummyjson):
    dummyjson.get("/products/search").respond(status_code=500)

    resultado = await buscar_produtos("laptop")

    assert resultado["ok"] is False
    assert resultado["erro"]["codigo"] == "DUMMYJSON_ERRO"


# --- detalhar_produto --------------------------------------------------------


async def test_detalhar_produto_sucesso(dummyjson):
    dummyjson.get("/products/78").respond(json=LAPTOP)

    resultado = await detalhar_produto(78)

    assert resultado["ok"] is True
    assert resultado["produto"]["stock"] == 24


async def test_detalhar_produto_inexistente(dummyjson):
    dummyjson.get("/products/99999").respond(status_code=404, json={"message": "not found"})

    resultado = await detalhar_produto(99999)

    assert resultado["ok"] is False
    assert resultado["erro"]["codigo"] == "PRODUTO_NAO_ENCONTRADO"


async def test_detalhar_produto_sem_conexao(dummyjson):
    dummyjson.get("/products/78").mock(side_effect=httpx.ConnectError("sem rede"))

    resultado = await detalhar_produto(78)

    assert resultado["ok"] is False
    assert resultado["erro"]["codigo"] == "DUMMYJSON_INDISPONIVEL"


# --- criar_requisicao --------------------------------------------------------


async def test_criar_requisicao_usa_preco_da_dummyjson(dummyjson, banco_falso):
    dummyjson.get("/products/78").respond(json=LAPTOP)

    resultado = await criar_requisicao(
        pedido="3 laptops até US$ 2.000 cada",
        itens=[ItemPedido(produto_id=78, quantidade=3)],
        orcamento_unitario_max=2000,
    )

    assert resultado["ok"] is True
    assert resultado["requisicao_id"] == 42
    assert resultado["valor_total"] == 5999.97  # 3 x 1999.99, calculado aqui
    assert resultado["itens"][0]["preco_unitario"] == 1999.99
    # O que foi para o banco também veio da DummyJSON
    gravado = banco_falso[0]
    assert str(gravado["valor_total"]) == "5999.97"
    assert gravado["itens"][0]["titulo"] == LAPTOP["title"]


async def test_criar_requisicao_estoque_insuficiente_nao_grava(dummyjson, banco_falso):
    dummyjson.get("/products/78").respond(json=LAPTOP)

    resultado = await criar_requisicao(
        pedido="100 laptops", itens=[ItemPedido(produto_id=78, quantidade=100)]
    )

    assert resultado["ok"] is False
    assert resultado["erro"]["codigo"] == "ESTOQUE_INSUFICIENTE"
    assert banco_falso == []


async def test_criar_requisicao_acima_do_orcamento_nao_grava(dummyjson, banco_falso):
    dummyjson.get("/products/78").respond(json=LAPTOP)

    resultado = await criar_requisicao(
        pedido="3 laptops até US$ 500 cada",
        itens=[ItemPedido(produto_id=78, quantidade=3)],
        orcamento_unitario_max=500,
    )

    assert resultado["ok"] is False
    assert resultado["erro"]["codigo"] == "ORCAMENTO_EXCEDIDO"
    assert banco_falso == []


async def test_criar_requisicao_timeout_da_dummyjson_nao_grava(dummyjson, banco_falso):
    dummyjson.get("/products/78").mock(side_effect=httpx.ReadTimeout("lento"))

    resultado = await criar_requisicao(
        pedido="3 laptops", itens=[ItemPedido(produto_id=78, quantidade=3)]
    )

    assert resultado["ok"] is False
    assert resultado["erro"]["codigo"] == "DUMMYJSON_TIMEOUT"
    assert banco_falso == []


async def test_criar_requisicao_banco_indisponivel(dummyjson, monkeypatch):
    dummyjson.get("/products/78").respond(json=LAPTOP)

    async def banco_fora(*args):
        raise psycopg.OperationalError("conexão recusada")

    monkeypatch.setattr(db, "salvar_requisicao", banco_fora)

    resultado = await criar_requisicao(
        pedido="3 laptops", itens=[ItemPedido(produto_id=78, quantidade=3)]
    )

    assert resultado["ok"] is False
    assert resultado["erro"]["codigo"] == "BANCO_INDISPONIVEL"

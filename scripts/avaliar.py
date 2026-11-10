"""Avalia o agente com 5 pedidos de teste e mostra quantos ele acertou.

Uso (com o ambiente no ar):  python scripts/avaliar.py

Para os pedidos possíveis, cada item gravado é conferido direto na DummyJSON,
sem confiar no agente: categoria certa, preço gravado igual ao do catálogo,
estoque, quantidade mínima e orçamento. Para os impossíveis, o acerto é não
criar requisição. Só usa a biblioteca padrão do Python.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

API_URL = os.getenv("API_URL", "http://localhost:8000")
DUMMYJSON_URL = os.getenv("DUMMYJSON_URL", "https://dummyjson.com")

CASOS = [
    {
        "pedido": "Preciso de 3 laptops para o time de vendas, até US$ 2.000 cada.",
        "deve_criar": True,
        "categoria": "laptops",
        "quantidade": 3,
        "max_unitario": 2000,
    },
    {
        "pedido": "Quero 2 smartphones de até US$ 300 cada.",
        "deve_criar": True,
        "categoria": "smartphones",
        "quantidade": 2,
        "max_unitario": 300,
    },
    {
        "pedido": "Preciso de 6 cadeiras para a sala de reunião, orçamento total de US$ 3.500.",
        "deve_criar": True,
        "categoria": "furniture",
        "quantidade": 6,
        "max_total": 3500,
    },
    {
        "pedido": "Preciso de 5 laptops de no máximo US$ 500 cada.",  # orçamento baixo demais
        "deve_criar": False,
    },
    {
        "pedido": "Preciso de 100 laptops até US$ 2.000 cada.",  # nenhum laptop tem estoque
        "deve_criar": False,
    },
]


def formatar_dolar(valor: float) -> str:
    """Mesmo formato do chat: US$ 1.099,99."""
    texto = f"{valor:,.2f}"
    return "US$ " + texto.replace(",", "_").replace(".", ",").replace("_", ".")


def http_json(url: str, corpo: dict | None = None) -> tuple[int, dict]:
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    cabecalhos = {
        "Content-Type": "application/json",
        # O Cloudflare da DummyJSON bloqueia o User-Agent padrão do urllib (erro 1010).
        "User-Agent": "agente-compras-avaliacao",
    }
    req = urllib.request.Request(url, data=dados, headers=cabecalhos)
    try:
        with urllib.request.urlopen(req, timeout=180) as resposta:
            return resposta.status, json.load(resposta)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except json.JSONDecodeError:
            return e.code, {}


def conferir_requisicao(caso: dict, requisicao: dict) -> list[str]:
    """Devolve a lista de problemas encontrados (vazia = acertou)."""
    problemas = []
    itens = requisicao["itens"]

    quantidade = sum(i["quantidade"] for i in itens)
    if quantidade != caso["quantidade"]:
        problemas.append(f"quantidade {quantidade}, esperado {caso['quantidade']}")

    for item in itens:
        _, produto = http_json(f"{DUMMYJSON_URL}/products/{item['produto_id']}")
        nome = f"'{item['titulo']}'"
        if produto.get("category") != caso["categoria"]:
            problemas.append(f"{nome} é da categoria {produto.get('category')}, esperado {caso['categoria']}")
        if item["preco_unitario"] != produto.get("price"):
            problemas.append(
                f"{nome}: preço gravado {item['preco_unitario']} ≠ catálogo {produto.get('price')}"
            )
        if item["quantidade"] > produto.get("stock", 0):
            problemas.append(f"{nome}: quantidade acima do estoque ({produto.get('stock')})")
        if item["quantidade"] < produto.get("minimumOrderQuantity", 1):
            problemas.append(f"{nome}: abaixo do pedido mínimo ({produto.get('minimumOrderQuantity')})")
        if "max_unitario" in caso and item["preco_unitario"] > caso["max_unitario"]:
            problemas.append(f"{nome}: {formatar_dolar(item['preco_unitario'])} acima do limite por unidade")

    if "max_total" in caso and requisicao["valor_total"] > caso["max_total"]:
        problemas.append(f"total {formatar_dolar(requisicao['valor_total'])} acima do orçamento")
    return problemas


def avaliar(caso: dict) -> tuple[bool, str]:
    status, resposta = http_json(f"{API_URL}/requisicoes", {"pedido": caso["pedido"]})
    if status != 200:
        return False, f"HTTP {status}: {resposta.get('erro', resposta)}"

    requisicao = resposta["requisicao"]
    ferramentas = " → ".join(c["nome"] for c in resposta["ferramentas_chamadas"])

    if not caso["deve_criar"]:
        if requisicao is None:
            return True, f"não criou, como esperado [{ferramentas}]"
        return False, f"criou a requisição #{requisicao['id']}, mas o pedido era impossível"

    if requisicao is None:
        return False, f"não criou requisição: {resposta['resposta'][:120]}"
    problemas = conferir_requisicao(caso, requisicao)
    if problemas:
        return False, "; ".join(problemas)
    itens = ", ".join(f"{i['quantidade']}x {i['titulo']}" for i in requisicao["itens"])
    return (
        True,
        f"#{requisicao['id']}: {itens}, total {formatar_dolar(requisicao['valor_total'])} [{ferramentas}]",
    )


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    acertos = 0
    for numero, caso in enumerate(CASOS, start=1):
        inicio = time.monotonic()
        try:
            acertou, detalhe = avaliar(caso)
        except (urllib.error.URLError, TimeoutError) as e:
            acertou, detalhe = False, f"falha de conexão: {e}"
        segundos = time.monotonic() - inicio
        acertos += acertou
        print(f"{'✓' if acertou else '✗'} {numero}. {caso['pedido']}  ({segundos:.0f}s)")
        print(f"     {detalhe}")

    print(f"\nAcertos: {acertos}/{len(CASOS)}")
    return 0 if acertos == len(CASOS) else 1


if __name__ == "__main__":
    sys.exit(main())

"""Gravação da requisição de compra no Postgres (SQL explícito com psycopg)."""

from decimal import Decimal

import psycopg

from app import config


async def salvar_requisicao(pedido: str, itens: list[dict], valor_total: Decimal) -> int:
    """Grava a requisição e seus itens numa única transação e devolve o id.

    Ao sair do bloco `async with` a conexão faz commit; se qualquer INSERT
    falhar, faz rollback, então nunca fica requisição sem itens.
    """
    async with await psycopg.AsyncConnection.connect(config.DATABASE_URL, connect_timeout=5) as conn:
        cursor = await conn.execute(
            "INSERT INTO requisicoes (pedido, valor_total) VALUES (%s, %s) RETURNING id",
            (pedido, valor_total),
        )
        (requisicao_id,) = await cursor.fetchone()

        for item in itens:
            await conn.execute(
                """
                INSERT INTO itens_requisicao
                    (requisicao_id, produto_id, titulo, quantidade, preco_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    requisicao_id,
                    item["produto_id"],
                    item["titulo"],
                    item["quantidade"],
                    item["preco_unitario"],
                    item["subtotal"],
                ),
            )
    return requisicao_id

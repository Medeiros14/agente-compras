"""Leitura das requisições no Postgres. A gravação é feita pela ferramenta
criar_requisicao, no servidor MCP."""

import psycopg
from psycopg.rows import dict_row

from app import config
from app.erros import ErroApi

# Uma consulta só: cada requisição já vem com a lista de itens em JSON.
# Com %(id)s nulo, lista todas; com um id, traz só aquela.
SQL_REQUISICOES = """
SELECT r.id,
       r.pedido,
       r.valor_total,
       r.criado_em,
       COALESCE(
           json_agg(
               json_build_object(
                   'produto_id', i.produto_id,
                   'titulo', i.titulo,
                   'quantidade', i.quantidade,
                   'preco_unitario', i.preco_unitario,
                   'subtotal', i.subtotal
               ) ORDER BY i.id
           ) FILTER (WHERE i.id IS NOT NULL),
           '[]'
       ) AS itens
FROM requisicoes r
LEFT JOIN itens_requisicao i ON i.requisicao_id = r.id
WHERE (%(id)s::int IS NULL OR r.id = %(id)s::int)
GROUP BY r.id
ORDER BY r.id DESC
"""


async def _consultar(requisicao_id: int | None) -> list[dict]:
    try:
        async with await psycopg.AsyncConnection.connect(
            config.DATABASE_URL, connect_timeout=5, row_factory=dict_row
        ) as conn:
            cursor = await conn.execute(SQL_REQUISICOES, {"id": requisicao_id})
            return await cursor.fetchall()
    except psycopg.Error as e:
        raise ErroApi(503, "BANCO_INDISPONIVEL", "Não foi possível consultar o banco de dados.") from e


async def listar_requisicoes() -> list[dict]:
    return await _consultar(None)


async def obter_requisicao(requisicao_id: int) -> dict | None:
    linhas = await _consultar(requisicao_id)
    return linhas[0] if linhas else None

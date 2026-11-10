"""Cliente MCP: abre a sessão com o servidor e adapta as ferramentas para o LLM."""

import json
from contextlib import asynccontextmanager
from datetime import timedelta

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app import config


@asynccontextmanager
async def abrir_sessao():
    """Abre uma sessão MCP via streamable HTTP (uma por pedido)."""
    async with streamablehttp_client(config.MCP_URL, timeout=config.MCP_TIMEOUT) as (
        leitura,
        escrita,
        _,
    ):
        async with ClientSession(
            leitura, escrita, read_timeout_seconds=timedelta(seconds=config.MCP_TIMEOUT)
        ) as sessao:
            await sessao.initialize()
            yield sessao


async def listar_ferramentas(sessao: ClientSession) -> list[dict]:
    """Converte as ferramentas do MCP para o formato de "tools" da API da OpenAI.

    O backend não conhece as ferramentas pelo nome: ele repassa ao modelo o que
    o servidor MCP oferece (nome, descrição e JSON Schema dos argumentos).
    """
    resultado = await sessao.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name": ferramenta.name,
                "description": ferramenta.description or "",
                "parameters": ferramenta.inputSchema,
            },
        }
        for ferramenta in resultado.tools
    ]


async def chamar_ferramenta(sessao: ClientSession, nome: str, argumentos: dict) -> dict:
    """Executa a ferramenta e devolve sempre um dict no formato {"ok": ..., ...}."""
    resultado = await sessao.call_tool(nome, argumentos)
    texto = "".join(bloco.text for bloco in resultado.content if bloco.type == "text")

    if resultado.isError:
        # Ex.: argumentos que não passam na validação do schema (quantidade 0).
        return {"ok": False, "erro": {"codigo": "ERRO_NA_FERRAMENTA", "mensagem": texto}}
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return {"ok": False, "erro": {"codigo": "RESPOSTA_INVALIDA", "mensagem": texto}}

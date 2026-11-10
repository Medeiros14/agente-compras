"""Cliente MCP: abre a sessão com o servidor e adapta as ferramentas para o LLM."""

import json
from contextlib import asynccontextmanager
from datetime import timedelta

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app import config


@asynccontextmanager
async def abrir_sessao():
    """Abre uma sessão MCP por pedido, via streamable HTTP."""
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
    """Repassa ao modelo, no formato "tools" da OpenAI, as ferramentas que o MCP oferece."""
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
    """Executa a ferramenta e devolve sempre um dict com "ok"."""
    resultado = await sessao.call_tool(nome, argumentos)
    texto = "".join(bloco.text for bloco in resultado.content if bloco.type == "text")

    if resultado.isError:
        # O FastMCP rejeitou os argumentos pelo schema antes de rodar a ferramenta.
        return {"ok": False, "erro": {"codigo": "ERRO_NA_FERRAMENTA", "mensagem": texto}}
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return {"ok": False, "erro": {"codigo": "RESPOSTA_INVALIDA", "mensagem": texto}}

"""API HTTP do agente: POST e GET /requisicoes."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import db
from app.agente import executar_agente
from app.erros import ErroApi
from app.schemas import PedidoEntrada, Requisicao, RespostaPedido

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Agente de compras")


@app.exception_handler(ErroApi)
async def tratar_erro_api(requisicao_http: Request, erro: ErroApi) -> JSONResponse:
    return JSONResponse(
        status_code=erro.status_http,
        content={"erro": {"codigo": erro.codigo, "mensagem": erro.mensagem}},
    )


@app.post("/requisicoes", response_model=RespostaPedido)
async def criar_requisicao(entrada: PedidoEntrada) -> RespostaPedido:
    """Roda o agente; `requisicao` vem null quando ele não cria nenhuma, e `resposta` explica."""
    resultado = await executar_agente(entrada.pedido)

    requisicao = None
    if resultado.requisicao_id is not None:
        requisicao = await db.obter_requisicao(resultado.requisicao_id)

    return RespostaPedido(
        resposta=resultado.resposta,
        requisicao=requisicao,
        ferramentas_chamadas=resultado.ferramentas_chamadas,
    )


@app.get("/requisicoes", response_model=list[Requisicao])
async def listar_requisicoes() -> list[dict]:
    return await db.listar_requisicoes()


@app.get("/health")
async def verificar_saude() -> dict:
    return {"status": "ok"}

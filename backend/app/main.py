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
async def tratar_erro_api(request: Request, erro: ErroApi) -> JSONResponse:
    return JSONResponse(
        status_code=erro.status_http,
        content={"erro": {"codigo": erro.codigo, "mensagem": erro.mensagem}},
    )


@app.post("/requisicoes", response_model=RespostaPedido)
async def criar_requisicao(entrada: PedidoEntrada) -> RespostaPedido:
    """Recebe o pedido em linguagem natural e deixa o agente resolver.

    Se o agente criar a requisição (via ferramenta criar_requisicao), ela é lida
    do banco e devolvida. Caso contrário, `requisicao` vem null e `resposta`
    explica o que faltou.
    """
    resultado = await executar_agente(entrada.pedido)

    requisicao = None
    if resultado.requisicao_id is not None:
        requisicao = await db.obter_requisicao(resultado.requisicao_id)

    return RespostaPedido(resposta=resultado.resposta, requisicao=requisicao)


@app.get("/requisicoes", response_model=list[Requisicao])
async def listar_requisicoes() -> list[dict]:
    return await db.listar_requisicoes()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

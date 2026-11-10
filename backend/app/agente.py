"""Loop de tool calling escrito à mão.

O backend não decide o fluxo: ele manda as mensagens e as ferramentas para o
modelo, executa as tool calls que o modelo pedir, devolve os resultados e
repete até o modelo responder sem pedir ferramentas (ou estourar o limite).
"""

import json
import logging
from dataclasses import dataclass, field
from functools import partial

import openai

from app import config
from app.erros import ErroApi
from app.mcp_cliente import abrir_sessao, chamar_ferramenta, listar_ferramentas
from app.prompt import SYSTEM_PROMPT

log = logging.getLogger(__name__)


@dataclass
class ResultadoAgente:
    resposta: str
    requisicao_id: int | None = None
    ferramentas_chamadas: list[dict] = field(default_factory=list)


def criar_cliente_llm() -> openai.AsyncOpenAI:
    return openai.AsyncOpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        timeout=config.LLM_TIMEOUT,
        max_retries=1,
    )


async def chamar_llm(llm, mensagens: list[dict], ferramentas: list[dict]):
    """Uma chamada ao modelo. Falhas da OpenRouter viram ErroApi com mensagem clara."""
    try:
        resposta = await llm.chat.completions.create(
            model=config.OPENROUTER_MODEL,
            messages=mensagens,
            tools=ferramentas,
            temperature=0,
        )
    except openai.APIError as e:
        log.warning("Falha na OpenRouter: %r", e)
        raise _erro_da_openrouter(e) from e

    if not resposta.choices:  # a OpenRouter às vezes devolve 200 sem choices
        raise ErroApi(502, "LLM_INDISPONIVEL", "O modelo devolveu uma resposta vazia.")
    return resposta.choices[0].message


def _erro_da_openrouter(e: openai.APIError) -> ErroApi:
    """Traduz a exceção do SDK numa mensagem clara para o usuário."""
    if isinstance(e, openai.AuthenticationError):
        return ErroApi(
            502,
            "LLM_NAO_AUTORIZADO",
            "A OpenRouter recusou a chave de API. Verifique OPENROUTER_API_KEY no .env.",
        )
    if isinstance(e, openai.APITimeoutError):
        return ErroApi(
            504,
            "LLM_TIMEOUT",
            f"O modelo não respondeu em {config.LLM_TIMEOUT:g}s. Tente novamente.",
        )
    # 4xx (exceto 429): problema de configuração, não adianta repetir.
    status = getattr(e, "status_code", None)
    if status is not None and 400 <= status < 500 and status != 429:
        return ErroApi(
            502,
            "LLM_CONFIGURACAO",
            f"A OpenRouter recusou o pedido para o modelo '{config.OPENROUTER_MODEL}' "
            f"(HTTP {status}). Verifique OPENROUTER_MODEL e as configurações da conta.",
        )
    return ErroApi(
        502,
        "LLM_INDISPONIVEL",
        "Não foi possível falar com o modelo (OpenRouter). Tente novamente em instantes.",
    )


async def rodar_loop(llm, ferramentas: list[dict], executar_ferramenta, pedido: str) -> ResultadoAgente:
    """Loop do agente: chama o modelo, executa as tool calls pedidas e repete até a resposta final.

    `executar_ferramenta(nome, argumentos)` devolve um dict {"ok": ...}. Só o resultado
    de criar_requisicao define se a requisição foi criada, e uma segunda chamada a ela
    no mesmo pedido não é executada.
    """
    mensagens = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": pedido},
    ]
    ferramentas_chamadas = []
    requisicao_id = None

    for _ in range(config.AGENTE_MAX_ITERACOES):
        mensagem = await chamar_llm(llm, mensagens, ferramentas)

        # Sem tool calls: o modelo terminou e esta é a resposta final.
        if not mensagem.tool_calls:
            return ResultadoAgente(mensagem.content or "", requisicao_id, ferramentas_chamadas)

        mensagens.append(
            {
                "role": "assistant",
                "content": mensagem.content,
                "tool_calls": [
                    {
                        "id": chamada.id,
                        "type": "function",
                        "function": {"name": chamada.function.name, "arguments": chamada.function.arguments},
                    }
                    for chamada in mensagem.tool_calls
                ],
            }
        )

        for chamada in mensagem.tool_calls:
            nome = chamada.function.name
            try:
                argumentos = json.loads(chamada.function.arguments or "{}")
            except json.JSONDecodeError:
                argumentos = {}
                resultado = {
                    "ok": False,
                    "erro": {"codigo": "ARGUMENTOS_INVALIDOS", "mensagem": "Argumentos não são JSON válido."},
                }
            else:
                if nome == "criar_requisicao" and requisicao_id is not None:
                    # Uma requisição por pedido, garantida aqui e não só pelo prompt:
                    # a segunda criação nem chega ao MCP.
                    resultado = {
                        "ok": False,
                        "erro": {
                            "codigo": "REQUISICAO_JA_CRIADA",
                            "mensagem": f"A requisição #{requisicao_id} já foi criada para este pedido. "
                            "Cada pedido gera uma única requisição.",
                        },
                    }
                else:
                    resultado = await executar_ferramenta(nome, argumentos)

            log.info("ferramenta=%s argumentos=%s ok=%s", nome, argumentos, resultado.get("ok"))
            ferramentas_chamadas.append(
                {
                    "nome": nome,
                    "argumentos": argumentos,
                    "ok": bool(resultado.get("ok")),
                    "erro": (resultado.get("erro") or {}).get("codigo"),
                }
            )

            # A única fonte da verdade sobre "requisição criada" é o resultado
            # da ferramenta, não o texto do modelo.
            if nome == "criar_requisicao" and resultado.get("ok"):
                requisicao_id = resultado["requisicao_id"]

            mensagens.append(
                {
                    "role": "tool",
                    "tool_call_id": chamada.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                }
            )

    # Limite de iterações atingido.
    if requisicao_id is not None:
        return ResultadoAgente(
            "A requisição foi criada, mas o agente não concluiu a justificativa da escolha.",
            requisicao_id,
            ferramentas_chamadas,
        )
    raise ErroApi(
        502,
        "AGENTE_SEM_RESPOSTA",
        f"O agente não chegou a uma resposta em {config.AGENTE_MAX_ITERACOES} passos. "
        "Tente reformular o pedido.",
    )


async def executar_agente(pedido: str) -> ResultadoAgente:
    """Abre a sessão MCP, lista as ferramentas e roda o loop."""
    if not config.OPENROUTER_API_KEY:
        raise ErroApi(503, "LLM_NAO_CONFIGURADO", "OPENROUTER_API_KEY não está definida no .env.")

    llm = criar_cliente_llm()
    erro_do_loop = None
    try:
        async with abrir_sessao() as sessao:
            ferramentas = await listar_ferramentas(sessao)
            try:
                return await rodar_loop(llm, ferramentas, partial(chamar_ferramenta, sessao), pedido)
            except ErroApi as e:
                # Guardado e relançado fora da sessão: dentro dela o cliente MCP
                # embrulharia o erro num ExceptionGroup (task groups do anyio).
                erro_do_loop = e
    except Exception as e:
        log.exception("Falha na comunicação com o servidor MCP")
        raise ErroApi(
            503,
            "MCP_INDISPONIVEL",
            "O servidor de ferramentas (MCP) não está disponível. Tente novamente em instantes.",
        ) from e
    raise erro_do_loop

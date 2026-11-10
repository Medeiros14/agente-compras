"""Testes do loop do agente com um LLM falso (sem chave, sem rede)."""

from types import SimpleNamespace

import pytest

from app import agente, config
from app.erros import ErroApi


def tool_call(id_, nome, argumentos_json):
    return SimpleNamespace(id=id_, function=SimpleNamespace(name=nome, arguments=argumentos_json))


def mensagem(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


class LLMFalso:
    """Devolve as mensagens roteirizadas, uma por chamada, e guarda o que recebeu."""

    def __init__(self, roteiro):
        self.roteiro = list(roteiro)
        self.recebido = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.recebido.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=self.roteiro.pop(0))])


def ferramentas_falsas(respostas: dict):
    chamadas = []

    async def executar(nome, argumentos):
        chamadas.append((nome, argumentos))
        return respostas[nome]

    return executar, chamadas


async def test_loop_executa_tools_pedidas_e_captura_requisicao():
    llm = LLMFalso(
        [
            mensagem(tool_calls=[tool_call("1", "buscar_produtos", '{"termo": "laptop"}')]),
            mensagem(
                tool_calls=[
                    tool_call(
                        "2",
                        "criar_requisicao",
                        '{"pedido": "x", "itens": [{"produto_id": 81, "quantidade": 3}]}',
                    )
                ]
            ),
            mensagem(content="Requisição #7 criada."),
        ]
    )
    executar, chamadas = ferramentas_falsas(
        {
            "buscar_produtos": {"ok": True, "produtos": [{"id": 81, "price": 1099.99}]},
            "criar_requisicao": {"ok": True, "requisicao_id": 7},
        }
    )

    resultado = await agente.rodar_loop(llm, [], executar, "3 laptops")

    assert resultado.requisicao_id == 7
    assert resultado.resposta == "Requisição #7 criada."
    assert [c[0] for c in chamadas] == ["buscar_produtos", "criar_requisicao"]
    assert [c["nome"] for c in resultado.ferramentas_chamadas] == ["buscar_produtos", "criar_requisicao"]
    # O resultado da ferramenta volta para o modelo como mensagem "tool"
    ultima_conversa = llm.recebido[-1]["messages"]
    assert ultima_conversa[-1]["role"] == "tool"
    assert '"requisicao_id": 7' in ultima_conversa[-1]["content"]


async def test_loop_sem_criar_requisicao_devolve_requisicao_nula():
    llm = LLMFalso(
        [
            mensagem(tool_calls=[tool_call("1", "buscar_produtos", '{"termo": "laptop"}')]),
            mensagem(content="Nenhuma requisição foi criada. Motivo: o mais barato custa US$ 1099.99."),
        ]
    )
    executar, _ = ferramentas_falsas({"buscar_produtos": {"ok": True, "produtos": []}})

    resultado = await agente.rodar_loop(llm, [], executar, "3 laptops até US$ 100")

    assert resultado.requisicao_id is None
    assert "Nenhuma requisição" in resultado.resposta


async def test_criar_requisicao_com_erro_nao_conta_como_criada():
    llm = LLMFalso(
        [
            mensagem(tool_calls=[tool_call("1", "criar_requisicao", '{"pedido": "x", "itens": []}')]),
            mensagem(content="Não foi possível criar."),
        ]
    )
    executar, _ = ferramentas_falsas(
        {
            "criar_requisicao": {"ok": False, "erro": {"codigo": "ESTOQUE_INSUFICIENTE", "mensagem": "..."}},
        }
    )

    resultado = await agente.rodar_loop(llm, [], executar, "pedido")

    assert resultado.requisicao_id is None
    assert resultado.ferramentas_chamadas[0]["ok"] is False
    assert resultado.ferramentas_chamadas[0]["erro"] == "ESTOQUE_INSUFICIENTE"


async def test_segunda_criacao_de_requisicao_e_bloqueada():
    criar = '{"pedido": "x", "itens": [{"produto_id": 81, "quantidade": 3}]}'
    llm = LLMFalso(
        [
            mensagem(tool_calls=[tool_call("1", "criar_requisicao", criar)]),
            mensagem(tool_calls=[tool_call("2", "criar_requisicao", criar)]),
            mensagem(content="Escolhi o Lenovo Yoga 920."),
        ]
    )
    executar, chamadas = ferramentas_falsas({"criar_requisicao": {"ok": True, "requisicao_id": 7}})

    resultado = await agente.rodar_loop(llm, [], executar, "3 laptops")

    # A segunda chamada não chegou à ferramenta (ao MCP)
    assert [c[0] for c in chamadas] == ["criar_requisicao"]
    assert resultado.requisicao_id == 7
    assert resultado.ferramentas_chamadas[1]["ok"] is False
    assert resultado.ferramentas_chamadas[1]["erro"] == "REQUISICAO_JA_CRIADA"
    # O modelo recebeu o erro como resultado da tool call
    assert "REQUISICAO_JA_CRIADA" in llm.recebido[-1]["messages"][-1]["content"]


async def test_loop_para_no_limite_de_iteracoes(monkeypatch):
    monkeypatch.setattr(config, "AGENTE_MAX_ITERACOES", 2)
    pede_busca = mensagem(tool_calls=[tool_call("1", "buscar_produtos", '{"termo": "x"}')])
    llm = LLMFalso([pede_busca, pede_busca, pede_busca])
    executar, _ = ferramentas_falsas({"buscar_produtos": {"ok": True, "produtos": []}})

    with pytest.raises(ErroApi) as erro:
        await agente.rodar_loop(llm, [], executar, "pedido")

    assert erro.value.codigo == "AGENTE_SEM_RESPOSTA"
    assert len(llm.recebido) == 2

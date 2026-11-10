# Agente de compras

## Resumo

```bash
cp .env.example .env        # Windows: copy .env.example .env
# coloque a sua OPENROUTER_API_KEY no .env
docker compose up --build   # chat em http://localhost:8080
```

- **O modelo decide o fluxo:** o backend só roda o loop de tool calling com as ferramentas que o MCP lista.
- **O preço vem da ferramenta, não do LLM:** `criar_requisicao` recebe só id e quantidade, consulta a DummyJSON e calcula o total.
- **Erros como dado:** falhas viram `{"ok": false, "erro": {...}}` e o agente explica o problema ao usuário.

O restante do README traz os detalhes.

## O que é

Você escreve no chat o que precisa, por exemplo *"Preciso de 3 laptops para o time de vendas, até US$ 2.000 cada."*. O agente busca no catálogo da [DummyJSON](https://dummyjson.com/docs/products), escolhe os itens, grava uma requisição de compra no Postgres e mostra itens, quantidades, preço unitário e total. Se nada atender ao pedido, ele explica o que falta e não cria requisição.

```
 React (nginx :8080) ──/api──▶ Backend FastAPI (:8000) ──MCP / streamable HTTP──▶ Servidor MCP (:8001) ──▶ DummyJSON
                                   │    ▲                                              │
                                   │    └── LLM via OpenRouter (tool calling)          │ criar_requisicao
                                   └──────────────── lê ──────────▶ Postgres ◀── grava ┘
```

## Como rodar

Pré-requisito: Docker com Compose.

1. Crie o `.env` a partir do exemplo:

   ```bash
   cp .env.example .env          # Linux/macOS
   copy .env.example .env        # Windows (cmd ou PowerShell)
   ```

2. Abra o `.env` e coloque **a sua chave da OpenRouter** em `OPENROUTER_API_KEY=`. A chave não vem no repositório, e o `.env` está no `.gitignore`.

   O modelo padrão é `anthropic/claude-haiku-5.5`, escolhido por ser compatível com a restrição de Zero Data Retention (ZDR) da chave fornecida para o case (o `openai/gpt-4o-mini` é bloqueado por ela). Com outra chave, troque o modelo em `OPENROUTER_MODEL`, desde que ele suporte tool calling.

3. Suba os 4 serviços:

   ```bash
   docker compose up --build
   ```

   Quando `docker compose ps` mostrar os 4 serviços como `healthy`, abra o chat.

| Endereço | O que é |
|---|---|
| http://localhost:8080 | Chat |
| http://localhost:8000/docs | Swagger do backend (`POST /requisicoes`, `GET /requisicoes`) |
| http://localhost:8001/mcp | Endpoint do protocolo MCP (streamable HTTP), usado pelo backend. Não abre como página no navegador |

As tabelas são criadas automaticamente por [db/init.sql](db/init.sql) na primeira subida. Esse script só roda com o volume vazio, então para recriar o banco do zero use `docker compose down -v`.

### Exemplo pela API

```bash
curl -X POST http://localhost:8000/requisicoes \
  -H "Content-Type: application/json" \
  -d '{"pedido": "Preciso de 3 laptops para o time de vendas, até US$ 2.000 cada."}'
```

```json
{
  "resposta": "Escolhi o Lenovo Yoga 920, que é o laptop de menor preço dentro do orçamento...",
  "requisicao": {
    "id": 1, "pedido": "Preciso de 3 laptops...", "valor_total": 3299.97, "criado_em": "...",
    "itens": [{ "produto_id": 81, "titulo": "Lenovo Yoga 920", "quantidade": 3,
                "preco_unitario": 1099.99, "subtotal": 3299.97 }]
  },
  "ferramentas_chamadas": [
    { "nome": "buscar_produtos", "argumentos": { "termo": "laptop" }, "ok": true, "erro": null },
    { "nome": "criar_requisicao", "argumentos": { "pedido": "...", "itens": [{ "produto_id": 81, "quantidade": 3 }],
      "orcamento_unitario_max": 2000 }, "ok": true, "erro": null }
  ]
}
```

O chat mostra essa lista de ferramentas, recolhida, abaixo de cada resposta.

Quando o agente não cria requisição, `requisicao` vem `null` e `resposta` traz o motivo e uma sugestão. Falhas de infraestrutura voltam como `{"erro": {"codigo", "mensagem"}}`.

### Testes

Os testes não precisam de chave de LLM nem de banco: a DummyJSON é mockada com `respx`, o Postgres por uma função falsa e o LLM por respostas roteirizadas.

Todos os comandos rodam **a partir da raiz do projeto**, em sequência, com Python 3.12. Cada pasta tem o seu `pytest.ini`, que o pytest encontra sozinho:

```bash
pip install -r mcp_server/requirements-dev.txt -r backend/requirements-dev.txt
pytest mcp_server   # ferramentas do MCP: sucesso, timeout, erro HTTP, estoque, orçamento, banco fora
pytest backend      # loop do agente
```

Sem Python local, rode tudo num container, também a partir da raiz:
`docker run --rm -v "${PWD}:/repo" -w /repo python:3.12-slim sh -c "pip install -q -r mcp_server/requirements-dev.txt -r backend/requirements-dev.txt && pytest mcp_server && pytest backend"`

O GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) roda `ruff check`, `ruff format --check`, os dois conjuntos de testes e o build do frontend com checagem de tipos.

### Avaliação do agente (com o LLM real)

Com o ambiente no ar, [scripts/avaliar.py](scripts/avaliar.py) envia 5 pedidos: 3 possíveis e 2 impossíveis (orçamento baixo demais e estoque insuficiente). O script usa só a biblioteca padrão. Para os possíveis, cada item gravado é conferido direto na DummyJSON, sem confiar no agente: categoria, preço gravado igual ao do catálogo, estoque, quantidade mínima e orçamento.

```bash
python scripts/avaliar.py
```

```
✓ 1. Preciso de 3 laptops para o time de vendas, até US$ 2.000 cada.  (8s)
     #9: 3x Lenovo Yoga 920, total US$ 3.299,97 [buscar_produtos → criar_requisicao]
...
✓ 5. Preciso de 100 laptops até US$ 2.000 cada.  (6s)
     não criou, como esperado [buscar_produtos]

Acertos: 5/5
```

## Decisões principais

- **O modelo decide o fluxo.** O backend lista as ferramentas que o servidor MCP oferece e as repassa ao LLM. Depois só roda o loop ([backend/app/agente.py](backend/app/agente.py)): chama o modelo, executa as tool calls pedidas, devolve os resultados e repete até a resposta final, com limite de 8 iterações. Não há framework de agente.
- **O modelo decide quando gravar.** Por isso a gravação é uma ferramenta, `criar_requisicao`. Ela recebe só `produto_id` e `quantidade`: o preço é consultado na DummyJSON dentro da ferramenta, e o total é calculado com `Decimal`. O LLM não tem como informar um preço.
- **Validação no servidor, não só no prompt.** `criar_requisicao` confere estoque, quantidade mínima e o orçamento extraído do pedido contra os preços reais. Se algo falhar, nada é gravado.
- **Uma requisição por pedido, garantida no código.** Se o modelo chamar `criar_requisicao` de novo depois de uma criação com sucesso, o loop não repassa a chamada ao MCP e devolve `REQUISICAO_JA_CRIADA` ao modelo. Isso não depende só do prompt.
- **"Requisição criada" vem do resultado da ferramenta, não do texto do modelo.** Os números exibidos no chat vêm do banco. O texto do agente traz só a justificativa da escolha ou o motivo de não ter criado.
- **Erros como dados.** Toda ferramenta devolve `{"ok": false, "erro": {"codigo", "mensagem"}}` em vez de lançar exceção, então o agente consegue explicar ao usuário o que aconteceu.
- **Modelo padrão `anthropic/claude-haiku-5.5`**, escolhido por ser compatível com a política de Zero Data Retention da chave fornecida. Para trocar, use a variável `OPENROUTER_MODEL`.
- **`mcp==1.30.0`.** Na linha 2.x do SDK o `FastMCP` foi renomeado para `MCPServer`, então fixei a última 1.x, em que o `FastMCP` é a API oficial.
- **Valores em dólar sempre no formato `US$ 1.099,99`**: no cartão, nas mensagens de erro das ferramentas e no texto do agente (regra no prompt). Na API os valores continuam numéricos.
- **SQL explícito com psycopg**, sem ORM: são duas tabelas, e o SQL fica visível e fácil de revisar.
- **Portas presas ao localhost** (`127.0.0.1:8080`, `:8000`, `:8001`). Sem isso, qualquer máquina da rede poderia chamar o servidor MCP e executar `criar_requisicao` direto, sem passar pelo backend. Entre os containers, a comunicação segue pela rede interna do compose.
- **Containers sem root.** O backend e o servidor MCP rodam com um usuário de sistema sem privilégios (`app`, uid 10001), criado nos Dockerfiles.
- **nginx faz proxy de `/api` para o backend**, então não há CORS. Ele resolve o nome `backend` pelo DNS do Docker a cada requisição e por isso continua funcionando se o container for recriado.

O prompt do agente está em [backend/app/prompt.py](backend/app/prompt.py), e as ferramentas em [mcp_server/app/server.py](mcp_server/app/server.py).

## Tratamento de falhas

| Falha | O que o usuário vê |
|---|---|
| DummyJSON lenta (mais de 5s) ou fora do ar | O agente informa que o catálogo não respondeu, sem criar requisição (HTTP 200, `requisicao: null`) |
| Banco fora do ar | `POST`: o agente informa que nada foi gravado. `GET`: 503 `BANCO_INDISPONIVEL` |
| Servidor MCP fora do ar | 503 `MCP_INDISPONIVEL` |
| OpenRouter: chave recusada / fora do ar / timeout | 502 `LLM_NAO_AUTORIZADO` / 502 `LLM_INDISPONIVEL` / 504 `LLM_TIMEOUT` |
| Backend fora do ar | O chat mostra "O backend não está respondendo" |

Para reproduzir sem editar arquivos, defina a variável só para o comando: variáveis do shell têm prioridade sobre o `.env`.

**bash** (Linux, macOS, Git Bash):

```bash
DUMMYJSON_URL=http://10.255.255.1 docker compose up -d mcp   # timeout real da DummyJSON
DUMMYJSON_TIMEOUT=0.001 docker compose up -d mcp             # timeout imediato
docker compose stop mcp                                     # MCP fora do ar
OPENROUTER_API_KEY=invalida docker compose up -d backend     # chave recusada
docker compose up -d mcp backend                            # restaura
```

**PowerShell** (Windows): a variável fica definida na sessão, então remova-a antes de restaurar.

```powershell
$env:DUMMYJSON_URL="http://10.255.255.1"; docker compose up -d mcp   # timeout real da DummyJSON
Remove-Item Env:DUMMYJSON_URL

$env:DUMMYJSON_TIMEOUT="0.001"; docker compose up -d mcp             # timeout imediato
Remove-Item Env:DUMMYJSON_TIMEOUT

docker compose stop mcp                                              # MCP fora do ar

$env:OPENROUTER_API_KEY="invalida"; docker compose up -d backend     # chave recusada
Remove-Item Env:OPENROUTER_API_KEY

docker compose up -d mcp backend                                     # restaura
```

## Configuração

Tudo vem de variáveis de ambiente (veja [.env.example](.env.example)). Só `OPENROUTER_API_KEY` é obrigatória.

| Variável | Padrão | Uso |
|---|---|---|
| `OPENROUTER_API_KEY` | (vazia) | Chave da OpenRouter. Fica só no `.env`, que está no `.gitignore` |
| `OPENROUTER_MODEL` | `anthropic/claude-haiku-5.5` | Modelo com suporte a tool calling |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | API compatível com OpenAI |
| `LLM_TIMEOUT` | `30` | Timeout de cada chamada ao LLM (s) |
| `AGENTE_MAX_ITERACOES` | `8` | Limite do loop de tool calling |
| `MCP_TIMEOUT` | `20` | Timeout das chamadas do backend ao servidor MCP (s) |
| `DUMMYJSON_URL` | `https://dummyjson.com` | Catálogo |
| `DUMMYJSON_TIMEOUT` | `5` | Timeout de cada chamada à DummyJSON (s) |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `compras` | Banco (a `DATABASE_URL` é montada no compose) |

## Estrutura

```
db/init.sql          schema (requisicoes, itens_requisicao)
mcp_server/          FastMCP: buscar_produtos, detalhar_produto, criar_requisicao + testes
backend/             FastAPI: loop do agente, cliente MCP, prompt, endpoints + testes
frontend/            React + Vite + TypeScript, servido por nginx
scripts/avaliar.py   avaliação do agente com 5 pedidos
.github/workflows/   CI: ruff, testes e build do frontend
```

## Como usei IA

Usei IA como par de programação, com dois papéis separados:

- **Claude Code (no VS Code, com Claude Opus 5.5)** escreveu o código, etapa por etapa. Antes de qualquer código, pedi o plano (estrutura, schema, contrato da API e integração com o MCP) e só aprovei depois de revisar. A cada etapa ele testava, eu revisava e fazia o commit.
- **Claude (app desktop, com Claude Opus 5.5)** atuou como revisor independente: lia o código, rodava os testes e o pedido de exemplo por conta própria, testava a tela no navegador e simulava falhas antes de eu aprovar cada etapa.

Decisões e correções que saíram dessa revisão:

- **ZDR:** a chave fornecida tem restrição de Zero Data Retention e bloqueava o `gpt-4o-mini`. Testamos os modelos disponíveis com a chave e trocamos o padrão do código (não só o meu `.env`), já que os avaliadores usam a mesma conta.
- **`criar_requisicao` entrou já no MCP**, para o modelo decidir quando gravar e o preço vir sempre da DummyJSON.
- **Testes também para o `criar_requisicao`** e uma resposta explícita quando nenhuma requisição é criada.
- **O agente não oferece ações futuras**, já que cada pedido é independente, e o texto não repete os itens que o cartão já mostra.

**O que validei pessoalmente:** subi o projeto com `docker compose up --build`, testei pelo chat o pedido de exemplo, um pedido impossível (orçamento baixo) e pedidos meus fora do catálogo, conferi as ferramentas chamadas em cada resposta e li o loop do agente (`agente.py`) e as ferramentas do MCP (`server.py`) para entender cada decisão.

-- Executado automaticamente pelo Postgres na primeira subida
-- (somente quando o volume de dados está vazio).

CREATE TABLE IF NOT EXISTS requisicoes (
    id           SERIAL PRIMARY KEY,
    pedido       TEXT          NOT NULL,          -- texto original do usuário
    valor_total  NUMERIC(12,2) NOT NULL,
    criado_em    TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS itens_requisicao (
    id              SERIAL PRIMARY KEY,
    requisicao_id   INT           NOT NULL REFERENCES requisicoes(id) ON DELETE CASCADE,
    produto_id      INT           NOT NULL,       -- id do produto na DummyJSON
    titulo          TEXT          NOT NULL,
    quantidade      INT           NOT NULL CHECK (quantidade > 0),
    preco_unitario  NUMERIC(10,2) NOT NULL,       -- vem da DummyJSON, nunca do LLM
    subtotal        NUMERIC(12,2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_itens_requisicao_requisicao_id
    ON itens_requisicao (requisicao_id);

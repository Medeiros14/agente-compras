"""Configuração do backend, toda vinda de variáveis de ambiente."""

import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-haiku-5.5")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))

MCP_URL = os.getenv("MCP_URL", "http://localhost:8001/mcp")
MCP_TIMEOUT = float(os.getenv("MCP_TIMEOUT", "20"))

AGENTE_MAX_ITERACOES = int(os.getenv("AGENTE_MAX_ITERACOES", "8"))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://compras:compras@localhost:5432/compras")

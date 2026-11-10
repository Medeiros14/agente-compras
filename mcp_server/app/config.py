"""Configuração do servidor MCP, toda vinda de variáveis de ambiente."""

import os

DUMMYJSON_URL = os.getenv("DUMMYJSON_URL", "https://dummyjson.com")
DUMMYJSON_TIMEOUT = float(os.getenv("DUMMYJSON_TIMEOUT", "5"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://compras:compras@localhost:5432/compras")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))

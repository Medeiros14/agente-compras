class ErroApi(Exception):
    """Falha que impede a API de responder (LLM, MCP ou banco fora do ar).

    É convertida em {"erro": {"codigo", "mensagem"}} pelo handler em main.py.
    """

    def __init__(self, status_http: int, codigo: str, mensagem: str):
        super().__init__(mensagem)
        self.status_http = status_http
        self.codigo = codigo
        self.mensagem = mensagem

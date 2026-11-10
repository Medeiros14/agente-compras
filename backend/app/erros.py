"""Erro da API com status HTTP, código e mensagem para o usuário."""


class ErroApi(Exception):
    """Falha que impede a resposta; main.py a converte em {"erro": {"codigo", "mensagem"}}."""

    def __init__(self, status_http: int, codigo: str, mensagem: str):
        super().__init__(mensagem)
        self.status_http = status_http
        self.codigo = codigo
        self.mensagem = mensagem

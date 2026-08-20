from pydantic import BaseModel


class NovoJogador(BaseModel):
    nome: str
    codigo_partida: str


class NovaResposta(BaseModel):
    jogador_id: int
    rodada: int
    desafio_id: int
    alternativa: str

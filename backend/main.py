from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rotas import (
    admin,
    jogadores,
    painel,
    partidas,
    respostas,
    resultados,
)

app = FastAPI(
    title="Escape Code API",
    description="Projeto SuperDev09",
    version="1.0.0"

)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(admin.router)
app.include_router(jogadores.router)
app.include_router(partidas.router)
app.include_router(respostas.router)
app.include_router(painel.router)
app.include_router(resultados.router)


@app.get("/")
def inicio():
    return {"mensagem": "Escape Code online"}

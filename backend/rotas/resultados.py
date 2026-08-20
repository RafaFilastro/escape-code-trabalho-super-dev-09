from banco import conectar
from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/resultados",
    tags=["Resultados"],
)


@router.get("/{partida_id}")
def obter_resultado(partida_id: int):
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM partidas
        WHERE id = %s
        """,
        (partida_id,),
    )

    partida = cursor.fetchone()

    if partida is None:
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=404,
            detail="Operação não encontrada.",
        )

    if partida["status"] != "FINALIZADA":
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=409,
            detail="A missão não foi concluída com sucesso.",
        )

    cursor.execute(
        """
        SELECT
            id,
            nome,
            pontuacao,
            finalizado_em
        FROM jogadores
        WHERE partida_id = %s
        ORDER BY
            pontuacao DESC,
            finalizado_em IS NULL,
            finalizado_em ASC,
            id ASC
        """,
        (partida_id,),
    )

    jogadores = cursor.fetchall()

    ranking = []

    for posicao, jogador in enumerate(
        jogadores,
        start=1,
    ):
        ranking.append(
            {
                "posicao": posicao,
                "id": jogador["id"],
                "nome": jogador["nome"],
                "pontos": jogador["pontuacao"],
            }
        )

    cursor.close()
    conexao.close()

    if not ranking:
        raise HTTPException(
            status_code=404,
            detail="Nenhum codinome encontrado.",
        )

    return {
        "partida": {
            "id": partida["id"],
            "protocolo": partida["nome_protocolo"],
            "status": partida["status"],
        },
        "chave_mestre": partida["chave_mestre"],
        "fragmentos": list(partida["chave_mestre"]),
        "vencedor": ranking[0],
        "ranking": ranking,
    }

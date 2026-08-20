from banco import conectar
from fastapi import (
    APIRouter,
    HTTPException,
)
from modelos import NovaResposta
from regras_jogo import (
    alternativa_exibida_para_original,
    atualizar_estado_partida,
    pontos_da_tentativa,
    rodada_liberada,
    verificar_andamento_rodada,
)

router = APIRouter(
    prefix="/respostas",
    tags=["Respostas"],
)


def fragmento_da_rodada(
    chave_mestre: str,
    rodada: int,
) -> str:

    if not chave_mestre or rodada < 1 or rodada > len(chave_mestre):
        return ""

    return chave_mestre[rodada - 1]


@router.post("")
def responder(
    dados: NovaResposta,
):

    alternativa_exibida = dados.alternativa.strip().upper()

    if alternativa_exibida not in {
        "A",
        "B",
        "C",
        "D",
        "E",
    }:
        raise HTTPException(
            status_code=400,
            detail=("Alternativa inválida."),
        )

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM jogadores
        WHERE id = %s
        """,
        (dados.jogador_id,),
    )

    jogador = cursor.fetchone()

    if jogador is None:
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=404,
            detail=("Codinome não encontrado."),
        )

    # Atualiza timeout/rodada antes de validar a resposta.
    # Isso evita que um clique atrasado seja aplicado
    # na rodada seguinte.
    partida = atualizar_estado_partida(
        conexao,
        cursor,
        jogador["partida_id"],
    )

    if partida is None or partida["status"] != "EM_ANDAMENTO":
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=409,
            detail=("A missão não está em andamento."),
        )

    cursor.execute(
        """
        SELECT *
        FROM partidas
        WHERE id = %s
        FOR UPDATE
        """,
        (partida["id"],),
    )

    partida = cursor.fetchone()

    cursor.execute(
        """
        SELECT *
        FROM jogadores
        WHERE id = %s
        FOR UPDATE
        """,
        (dados.jogador_id,),
    )

    jogador = cursor.fetchone()

    rodada_atual = int(partida["rodada_atual"])

    if dados.rodada != rodada_atual:
        conexao.rollback()
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=409,
            detail=("A janela desta pergunta já foi encerrada."),
        )

    if not rodada_liberada(
        cursor,
        partida,
    ):
        conexao.rollback()
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=409,
            detail=("A próxima rodada ainda está sincronizando."),
        )

    if int(jogador["rodadas_concluidas"]) >= rodada_atual:
        conexao.rollback()
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=409,
            detail=("Esta rodada já foi concluída."),
        )

    cursor.execute(
        """
        SELECT
            jd.id AS jogador_desafio_id,
            d.id AS desafio_id,
            d.resposta_correta

        FROM jogador_desafios jd

        INNER JOIN desafios d
            ON d.id = jd.desafio_id

        WHERE jd.jogador_id = %s
          AND jd.rodada = %s
        """,
        (
            dados.jogador_id,
            rodada_atual,
        ),
    )

    desafio = cursor.fetchone()

    if desafio is None:
        conexao.rollback()
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=404,
            detail=("Desafio individual não encontrado."),
        )

    if int(desafio["desafio_id"]) != dados.desafio_id:
        conexao.rollback()
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=409,
            detail=("Esta pergunta já não é mais a pergunta ativa."),
        )

    # ==========================================================
    # CONVERSÃO DA LETRA VISÍVEL PARA A LETRA ORIGINAL
    #
    # Exemplo:
    #
    # No banco:
    #   A = resposta correta
    #
    # Na tela deste jogador:
    #   D = texto da alternativa A original
    #
    # Se ele clicar D, convertemos D -> A antes de validar.
    # ==========================================================
    alternativa_original = alternativa_exibida_para_original(
        dados.jogador_id,
        int(desafio["desafio_id"]),
        alternativa_exibida,
    )

    cursor.execute(
        """
        SELECT
            id

        FROM tentativas

        WHERE jogador_id = %s
          AND jogador_desafio_id = %s
          AND alternativa = %s

        LIMIT 1
        """,
        (
            dados.jogador_id,
            desafio["jogador_desafio_id"],
            alternativa_original,
        ),
    )

    if cursor.fetchone() is not None:
        conexao.rollback()
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=400,
            detail=("Esta alternativa já foi bloqueada."),
        )

    cursor.execute(
        """
        SELECT
            COUNT(*) AS quantidade

        FROM tentativas

        WHERE jogador_id = %s
          AND jogador_desafio_id = %s
        """,
        (
            dados.jogador_id,
            desafio["jogador_desafio_id"],
        ),
    )

    numero_tentativa = int(cursor.fetchone()["quantidade"]) + 1

    correta = alternativa_original == desafio["resposta_correta"]

    if not correta:
        # No banco guardamos a letra ORIGINAL.
        cursor.execute(
            """
            INSERT INTO tentativas (
                jogador_id,
                jogador_desafio_id,
                numero_tentativa,
                alternativa,
                correta,
                pontos_ganhos,
                expirou
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                FALSE,
                0,
                FALSE
            )
            """,
            (
                dados.jogador_id,
                desafio["jogador_desafio_id"],
                numero_tentativa,
                alternativa_original,
            ),
        )

        conexao.commit()
        cursor.close()
        conexao.close()

        return {
            "correta": False,
            "numero_tentativa": (numero_tentativa),
            # O frontend precisa bloquear a letra que
            # o jogador realmente clicou.
            "alternativa_bloqueada": (alternativa_exibida),
            "pontos_proxima_tentativa": (pontos_da_tentativa(numero_tentativa + 1)),
            "bloqueio_segundos": 2,
            "mensagem": ("PACOTE CORROMPIDO. ACESSO NEGADO."),
        }

    pontos = pontos_da_tentativa(numero_tentativa)

    cursor.execute(
        """
        INSERT INTO tentativas (
            jogador_id,
            jogador_desafio_id,
            numero_tentativa,
            alternativa,
            correta,
            pontos_ganhos,
            expirou
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            TRUE,
            %s,
            FALSE
        )
        """,
        (
            dados.jogador_id,
            desafio["jogador_desafio_id"],
            numero_tentativa,
            alternativa_original,
            pontos,
        ),
    )

    if rodada_atual == 10:
        cursor.execute(
            """
            UPDATE jogadores
            SET
                pontuacao = (
                    pontuacao + %s
                ),
                rodadas_concluidas = %s,
                finalizado = TRUE,
                finalizado_em = NOW(6)
            WHERE id = %s
            """,
            (
                pontos,
                rodada_atual,
                dados.jogador_id,
            ),
        )

    else:
        cursor.execute(
            """
            UPDATE jogadores
            SET
                pontuacao = (
                    pontuacao + %s
                ),
                rodadas_concluidas = %s
            WHERE id = %s
            """,
            (
                pontos,
                rodada_atual,
                dados.jogador_id,
            ),
        )

    andamento = verificar_andamento_rodada(
        cursor,
        partida,
    )

    conexao.commit()
    cursor.close()
    conexao.close()

    return {
        "correta": True,
        "numero_tentativa": (numero_tentativa),
        "pontos_ganhos": (pontos),
        "fragmento_chave": (
            fragmento_da_rodada(
                partida["chave_mestre"],
                rodada_atual,
            )
        ),
        "mensagem": ("NÓ DESCRIPTOGRAFADO."),
        "andamento": andamento,
    }

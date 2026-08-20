from banco import conectar
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from modelos import NovoJogador
from regras_jogo import (
    alternativa_original_para_exibida,
    atualizar_estado_partida,
    dados_relogio_sincronizado,
    embaralhar_textos_alternativas,
    rodada_liberada,
    segundos_restantes_partida,
    segundos_restantes_rodada,
    sortear_desafios_para_jogador,
)
from seguranca_admin import (
    validar_chave_admin,
)

router = APIRouter(
    prefix="/jogadores",
    tags=["Jogadores"],
)


@router.post("")
def criar_jogador(
    dados: NovoJogador,
):
    nome = dados.nome.strip()

    if len(nome) < 2:
        raise HTTPException(
            status_code=400,
            detail=("O codinome precisa ter pelo menos 2 caracteres."),
        )

    if len(nome) > 50:
        raise HTTPException(
            status_code=400,
            detail=("O codinome pode ter no máximo 50 caracteres."),
        )

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM partidas
        WHERE codigo = %s
        LIMIT 1
        """,
        (dados.codigo_partida.strip().upper(),),
    )

    partida = cursor.fetchone()

    if partida is None:
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=404,
            detail=("Operação não encontrada."),
        )

    if partida["status"] != "AGUARDANDO":
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=400,
            detail=("A operação já foi iniciada."),
        )

    cursor.execute(
        """
        SELECT
            id
        FROM jogadores
        WHERE partida_id = %s
          AND LOWER(nome) = LOWER(%s)
        LIMIT 1
        """,
        (
            partida["id"],
            nome,
        ),
    )

    if cursor.fetchone() is not None:
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=409,
            detail=("Este codinome já está conectado nesta operação."),
        )

    cursor.execute(
        """
        INSERT INTO jogadores (
            partida_id,
            nome
        )
        VALUES (%s, %s)
        """,
        (
            partida["id"],
            nome,
        ),
    )

    jogador_id = cursor.lastrowid

    desafios = sortear_desafios_para_jogador(
        cursor,
        partida["id"],
    )

    cursor.executemany(
        """
        INSERT INTO jogador_desafios (
            jogador_id,
            desafio_id,
            rodada
        )
        VALUES (%s, %s, %s)
        """,
        [
            (
                jogador_id,
                desafio_id,
                rodada,
            )
            for desafio_id, rodada in desafios
        ],
    )

    conexao.commit()

    cursor.execute(
        """
        SELECT
            id,
            partida_id,
            nome,
            pontuacao,
            rodadas_concluidas,
            finalizado
        FROM jogadores
        WHERE id = %s
        """,
        (jogador_id,),
    )

    jogador = cursor.fetchone()

    cursor.close()
    conexao.close()

    return jogador


@router.delete(
    "/{jogador_id}",
    dependencies=[Depends(validar_chave_admin)],
)
def remover_jogador(
    jogador_id: int,
):
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            j.id,
            j.nome,
            p.status

        FROM jogadores j

        INNER JOIN partidas p
            ON p.id = j.partida_id

        WHERE j.id = %s
        """,
        (jogador_id,),
    )

    jogador = cursor.fetchone()

    if jogador is None:
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=404,
            detail=("Codinome não encontrado."),
        )

    if jogador["status"] != "AGUARDANDO":
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=400,
            detail=("Só é possível remover um codinome antes do início."),
        )

    cursor.execute(
        """
        DELETE FROM jogadores
        WHERE id = %s
        """,
        (jogador_id,),
    )

    conexao.commit()
    cursor.close()
    conexao.close()

    return {
        "removido": True,
        "nome": jogador["nome"],
    }


@router.get("/{jogador_id}/estado")
def obter_estado_jogador(
    jogador_id: int,
):
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM jogadores
        WHERE id = %s
        """,
        (jogador_id,),
    )

    jogador = cursor.fetchone()

    if jogador is None:
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=404,
            detail=("Codinome removido ou inexistente."),
        )

    partida = atualizar_estado_partida(
        conexao,
        cursor,
        jogador["partida_id"],
    )

    if partida is None:
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=404,
            detail=("Operação não encontrada."),
        )

    cursor.execute(
        """
        SELECT *
        FROM jogadores
        WHERE id = %s
        """,
        (jogador_id,),
    )

    jogador = cursor.fetchone()

    relogio = dados_relogio_sincronizado(
        cursor,
        partida,
    )

    resposta = {
        "jogador": {
            "id": jogador["id"],
            "nome": jogador["nome"],
            "pontuacao": (jogador["pontuacao"]),
            "rodadas_concluidas": (jogador["rodadas_concluidas"]),
        },
        "partida": {
            "id": partida["id"],
            "status": partida["status"],
            "rodada_atual": (partida["rodada_atual"]),
            "duracao_rodada_segundos": (partida["duracao_rodada_segundos"]),
            "segundos_partida": 0,
            "segundos_rodada": 0,
        },
        "relogio": relogio,
        "aguardando_sincronizacao": (False),
        "desafio": None,
        "ultimo_timeout": None,
    }

    # ==========================================================
    # ÚLTIMO TIMEOUT
    #
    # O banco guarda a alternativa correta ORIGINAL.
    # Aqui convertemos para a letra que o jogador realmente viu.
    # ==========================================================
    cursor.execute(
        """
        SELECT
            jd.rodada,
            jd.desafio_id,
            d.resposta_correta,
            t.pontos_ganhos

        FROM tentativas t

        INNER JOIN jogador_desafios jd
            ON jd.id = t.jogador_desafio_id

        INNER JOIN desafios d
            ON d.id = jd.desafio_id

        WHERE t.jogador_id = %s
          AND t.expirou = TRUE

        ORDER BY
            jd.rodada DESC

        LIMIT 1
        """,
        (jogador_id,),
    )

    ultimo_timeout = cursor.fetchone()

    if ultimo_timeout is not None:
        rodada_timeout = int(ultimo_timeout["rodada"])

        fragmento = ""

        if 1 <= rodada_timeout <= len(partida["chave_mestre"]):
            fragmento = partida["chave_mestre"][rodada_timeout - 1]

        correta_exibida = alternativa_original_para_exibida(
            jogador_id,
            int(ultimo_timeout["desafio_id"]),
            ultimo_timeout["resposta_correta"],
        )

        resposta["ultimo_timeout"] = {
            "rodada": (rodada_timeout),
            "alternativa_correta": (correta_exibida),
            "pontos_ganhos": (ultimo_timeout["pontos_ganhos"]),
            "fragmento_chave": (fragmento),
        }

    if partida["status"] == "EM_ANDAMENTO":
        resposta["partida"]["segundos_partida"] = segundos_restantes_partida(
            cursor,
            partida,
        )

        resposta["partida"]["segundos_rodada"] = segundos_restantes_rodada(
            cursor,
            partida,
        )

        rodada_atual = int(partida["rodada_atual"])

        if not rodada_liberada(
            cursor,
            partida,
        ):
            resposta["aguardando_sincronizacao"] = True

        elif int(jogador["rodadas_concluidas"]) >= rodada_atual:
            resposta["aguardando_sincronizacao"] = True

        else:
            cursor.execute(
                """
                SELECT
                    jd.id AS jogador_desafio_id,
                    jd.rodada,

                    d.id AS desafio_id,
                    d.tema,
                    d.pergunta,
                    d.alternativa_a,
                    d.alternativa_b,
                    d.alternativa_c,
                    d.alternativa_d,
                    d.alternativa_e

                FROM jogador_desafios jd

                INNER JOIN desafios d
                    ON d.id = jd.desafio_id

                WHERE jd.jogador_id = %s
                  AND jd.rodada = %s
                """,
                (
                    jogador_id,
                    rodada_atual,
                ),
            )

            desafio = cursor.fetchone()

            if desafio is not None:
                cursor.execute(
                    """
                    SELECT
                        alternativa

                    FROM tentativas

                    WHERE jogador_id = %s
                      AND jogador_desafio_id = %s
                      AND correta = FALSE

                    ORDER BY id
                    """,
                    (
                        jogador_id,
                        desafio["jogador_desafio_id"],
                    ),
                )

                # As alternativas erradas salvas no banco são
                # letras ORIGINAIS. Precisamos devolver ao frontend
                # as letras que estavam visíveis ao jogador.
                bloqueadas_originais = [
                    item["alternativa"] for item in cursor.fetchall()
                ]

                bloqueadas_exibidas = [
                    alternativa_original_para_exibida(
                        jogador_id,
                        int(desafio["desafio_id"]),
                        alternativa_original,
                    )
                    for alternativa_original in bloqueadas_originais
                ]

                alternativas_originais = {
                    "A": (desafio["alternativa_a"]),
                    "B": (desafio["alternativa_b"]),
                    "C": (desafio["alternativa_c"]),
                    "D": (desafio["alternativa_d"]),
                    "E": (desafio["alternativa_e"]),
                }

                alternativas_exibidas = embaralhar_textos_alternativas(
                    jogador_id,
                    int(desafio["desafio_id"]),
                    alternativas_originais,
                )

                resposta["desafio"] = {
                    "rodada": (desafio["rodada"]),
                    "desafio_id": (desafio["desafio_id"]),
                    "tema": (desafio["tema"]),
                    "pergunta": (desafio["pergunta"]),
                    "alternativas": (alternativas_exibidas),
                    "alternativas_bloqueadas": (bloqueadas_exibidas),
                }

    cursor.close()
    conexao.close()

    return resposta

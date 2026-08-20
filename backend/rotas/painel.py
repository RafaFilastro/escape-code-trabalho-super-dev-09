from banco import conectar
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from regras_jogo import (
    atualizar_estado_partida,
    dados_relogio_sincronizado,
    segundos_restantes_partida,
    segundos_restantes_rodada,
)
from seguranca_admin import (
    validar_chave_admin,
)

router = APIRouter(
    prefix="/painel",
    tags=["Painel"],
)


@router.get(
    "/partida-atual",
    dependencies=[Depends(validar_chave_admin)],
)
def obter_painel():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM partidas
        ORDER BY id DESC
        LIMIT 1
        """
    )

    partida = cursor.fetchone()

    if partida is None:
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=404,
            detail=("Nenhuma operação criada."),
        )

    if partida["status"] == "EM_ANDAMENTO":
        partida = atualizar_estado_partida(
            conexao,
            cursor,
            partida["id"],
        )

    rodada = int(partida["rodada_atual"])

    # ==========================================================
    # TOTAL REAL DE JOGADORES
    #
    # O painel exibe somente os 5 melhores, mas o contador
    # e a sincronização precisam considerar TODOS os jogadores.
    # ==========================================================
    cursor.execute(
        """
        SELECT
            COUNT(*) AS total_jogadores,
            COALESCE(
                SUM(
                    rodadas_concluidas
                ),
                0
            ) AS total_conclusoes

        FROM jogadores

        WHERE partida_id = %s
        """,
        (partida["id"],),
    )

    totais = cursor.fetchone()

    total_jogadores = int(totais["total_jogadores"])

    total_conclusoes = int(totais["total_conclusoes"])

    jogadores_concluidos = 0

    if rodada > 0:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS quantidade

            FROM jogadores

            WHERE partida_id = %s
              AND rodadas_concluidas >= %s
            """,
            (
                partida["id"],
                rodada,
            ),
        )

        jogadores_concluidos = int(cursor.fetchone()["quantidade"])

    progresso_rodada = 0

    if total_jogadores > 0:
        progresso_rodada = round((jogadores_concluidos / total_jogadores) * 100)

    progresso_geral = 0

    if total_jogadores > 0:
        progresso_geral = round((total_conclusoes / (total_jogadores * 10)) * 100)

    # ==========================================================
    # TOP 5
    #
    # Durante a operação:
    #   1) maior pontuação;
    #   2) mais rodadas concluídas;
    #   3) menor ID para estabilidade do empate visual.
    #
    # Antes da partida todos possuem 0 pontos, então aparecem
    # os cinco primeiros que entraram.
    # ==========================================================
    if partida["status"] == "AGUARDANDO":
        # Antes de iniciar, priorizamos os cinco cadastros
        # mais recentes. Isso facilita remover um codinome
        # digitado errado sem poluir o painel com todos.
        cursor.execute(
            """
            SELECT
                id,
                nome,
                pontuacao,
                rodadas_concluidas

            FROM jogadores

            WHERE partida_id = %s

            ORDER BY
                id DESC

            LIMIT 5
            """,
            (partida["id"],),
        )

    else:
        # Durante a operação aparecem somente os cinco
        # melhores colocados pela pontuação atual.
        cursor.execute(
            """
            SELECT
                id,
                nome,
                pontuacao,
                rodadas_concluidas

            FROM jogadores

            WHERE partida_id = %s

            ORDER BY
                pontuacao DESC,
                rodadas_concluidas DESC,
                id ASC

            LIMIT 5
            """,
            (partida["id"],),
        )

    top_cinco_banco = cursor.fetchall()

    codinomios = []

    for posicao, jogador in enumerate(
        top_cinco_banco,
        start=1,
    ):
        sincronizado = False

        if rodada > 0:
            sincronizado = int(jogador["rodadas_concluidas"]) >= rodada

        codinomios.append(
            {
                "posicao": posicao,
                "id": jogador["id"],
                "nome": jogador["nome"],
                "pontuacao": int(jogador["pontuacao"]),
                "sincronizado": (sincronizado),
            }
        )

    segundos_partida = int(partida["duracao_segundos"])

    segundos_rodada = int(partida["duracao_rodada_segundos"])

    if partida["status"] == "EM_ANDAMENTO":
        segundos_partida = segundos_restantes_partida(
            cursor,
            partida,
        )

        segundos_rodada = segundos_restantes_rodada(
            cursor,
            partida,
        )

    quantidade_fragmentos = 0

    if partida["status"] == "FINALIZADA":
        quantidade_fragmentos = 10

    elif rodada > 0:
        quantidade_fragmentos = max(
            0,
            rodada - 1,
        )

    fragmentos = []

    for indice, caractere in enumerate(
        partida["chave_mestre"],
        start=1,
    ):
        if indice <= quantidade_fragmentos:
            fragmentos.append(caractere)
        else:
            fragmentos.append(None)

    # ==========================================================
    # EVENTO DE ERRO
    #
    # Mantido para o tremor do painel quando alguém erra.
    # ==========================================================
    cursor.execute(
        """
        SELECT
            MAX(t.id) AS ultimo_erro_id

        FROM tentativas t

        INNER JOIN jogadores j
            ON j.id = t.jogador_id

        WHERE j.partida_id = %s
          AND t.correta = FALSE
          AND t.expirou = FALSE
        """,
        (partida["id"],),
    )

    erro = cursor.fetchone()

    ultimo_erro_id = (
        int(erro["ultimo_erro_id"]) if (erro["ultimo_erro_id"] is not None) else None
    )

    ultimo_jogador_erro = None

    if ultimo_erro_id is not None:
        cursor.execute(
            """
            SELECT
                j.nome

            FROM tentativas t

            INNER JOIN jogadores j
                ON j.id = t.jogador_id

            WHERE t.id = %s
            """,
            (ultimo_erro_id,),
        )

        registro_erro = cursor.fetchone()

        if registro_erro:
            ultimo_jogador_erro = registro_erro["nome"]

    relogio = dados_relogio_sincronizado(
        cursor,
        partida,
    )

    cursor.close()
    conexao.close()

    return {
        "partida": {
            "id": partida["id"],
            "codigo": partida["codigo"],
            "protocolo": (partida["nome_protocolo"]),
            "status": (partida["status"]),
            "rodada_atual": (partida["rodada_atual"]),
            "total_rodadas": 10,
            "duracao_rodada_segundos": (partida["duracao_rodada_segundos"]),
            "segundos_restantes": (segundos_partida),
            "segundos_rodada": (segundos_rodada),
        },
        "relogio": relogio,
        "rodada": {
            "jogadores_concluidos": (jogadores_concluidos),
            "total_jogadores": (total_jogadores),
            "progresso": (progresso_rodada),
            "total_conclusoes": (total_conclusoes),
        },
        "descriptografia": {
            "progresso": (progresso_geral),
            "fragmentos": (fragmentos),
        },
        "codinomios": (codinomios),
        "evento_erro": {
            "ultimo_erro_id": (ultimo_erro_id),
            "ultimo_jogador": (ultimo_jogador_erro),
        },
    }

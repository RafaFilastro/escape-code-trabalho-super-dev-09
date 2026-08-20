import hashlib
import random
import secrets
import string

PROTOCOLOS = [
    "SEQUESTRO DE DADOS",
    "NÚCLEO CRIPTOGRAFADO",
    "CHAVE MESTRE COMPROMETIDA",
    "ACESSO ROOT BLOQUEADO",
    "SISTEMA SOB ATAQUE",
    "PROTOCOLO RANSOMWARE",
    "NÓ CENTRAL CORROMPIDO",
]


DISTRIBUICAO_TEMAS = {
    "HTML": 1,
    "SCSS": 1,
    "JAVASCRIPT": 1,
    "TYPESCRIPT": 1,
    "ANGULAR": 2,
    "PYTHON": 2,
    "MYSQL": 2,
}


PONTOS_POR_TENTATIVA = {
    1: 1000,
    2: 800,
    3: 600,
    4: 400,
}


LETRAS_ALTERNATIVAS = [
    "A",
    "B",
    "C",
    "D",
    "E",
]


def pontos_da_tentativa(
    numero_tentativa: int,
) -> int:
    return PONTOS_POR_TENTATIVA.get(
        numero_tentativa,
        200,
    )


def gerar_codigo_partida() -> str:
    alfabeto = string.ascii_uppercase + string.digits

    return "".join(secrets.choice(alfabeto) for _ in range(6))


def gerar_chave_mestre() -> str:
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    return "".join(secrets.choice(alfabeto) for _ in range(10))


# ==============================================================
# EMBARALHAMENTO DAS ALTERNATIVAS
# ==============================================================
#
# O banco pode guardar uma pergunta assim:
#
# A = resposta correta
# B = errada
# C = errada
# D = errada
# E = errada
#
# Isso NÃO significa mais que a resposta correta será mostrada
# visualmente na posição A.
#
# Para cada combinação jogador + desafio é criado um embaralhamento
# determinístico. Ou seja:
#
# - o jogador vê as alternativas em posições aleatórias;
# - a ordem continua igual durante toda aquela pergunta;
# - atualizar a página não muda a posição;
# - jogadores diferentes podem receber ordens diferentes;
# - nenhuma alteração no banco de dados é necessária.
# ==============================================================


def mapa_alternativas_exibidas(
    jogador_id: int,
    desafio_id: int,
):
    """
    Retorna um mapa no formato:

        {
            "A": "C",
            "B": "A",
            "C": "E",
            "D": "B",
            "E": "D",
        }

    A chave é a letra EXIBIDA ao jogador.
    O valor é a letra ORIGINAL salva no banco.
    """

    material = (f"escape-code-v10:{jogador_id}:{desafio_id}").encode("utf-8")

    digest = hashlib.sha256(material).digest()

    semente = int.from_bytes(
        digest[:8],
        "big",
    )

    gerador = random.Random(semente)

    originais = LETRAS_ALTERNATIVAS.copy()

    gerador.shuffle(originais)

    return {
        letra_exibida: letra_original
        for letra_exibida, letra_original in zip(
            LETRAS_ALTERNATIVAS,
            originais,
        )
    }


def alternativa_exibida_para_original(
    jogador_id: int,
    desafio_id: int,
    alternativa_exibida: str,
) -> str:
    mapa = mapa_alternativas_exibidas(
        jogador_id,
        desafio_id,
    )

    return mapa[alternativa_exibida]


def alternativa_original_para_exibida(
    jogador_id: int,
    desafio_id: int,
    alternativa_original: str,
) -> str:
    mapa = mapa_alternativas_exibidas(
        jogador_id,
        desafio_id,
    )

    for (
        letra_exibida,
        letra_original,
    ) in mapa.items():
        if letra_original == alternativa_original:
            return letra_exibida

    raise ValueError("Alternativa original inválida.")


def embaralhar_textos_alternativas(
    jogador_id: int,
    desafio_id: int,
    alternativas_originais: dict,
):
    """
    Recebe:
        {
            "A": "...",
            "B": "...",
            ...
        }

    Retorna as mesmas opções em posições embaralhadas.
    """

    mapa = mapa_alternativas_exibidas(
        jogador_id,
        desafio_id,
    )

    return {
        letra_exibida: (alternativas_originais[letra_original])
        for (
            letra_exibida,
            letra_original,
        ) in mapa.items()
    }


def sortear_desafios_para_jogador(
    cursor,
    partida_id: int,
):
    """
    Sorteia 10 perguntas para um jogador.

    Regras:
    - mantém a distribuição por tema;
    - não repete pergunta para o mesmo jogador;
    - tenta evitar a mesma pergunta para dois jogadores
      na mesma rodada.
    """

    temas = []

    for tema, quantidade in DISTRIBUICAO_TEMAS.items():
        temas.extend([tema] * quantidade)

    random.shuffle(temas)

    cursor.execute(
        """
        SELECT
            id,
            UPPER(tema) AS tema
        FROM desafios
        WHERE ativo = TRUE
        """
    )

    desafios_banco = cursor.fetchall()

    desafios_por_tema = {}

    for desafio in desafios_banco:
        desafios_por_tema.setdefault(
            desafio["tema"],
            [],
        ).append(desafio["id"])

    escolhidos = []
    usados_pelo_jogador = set()

    for rodada, tema in enumerate(
        temas,
        start=1,
    ):
        candidatos_tema = list(
            desafios_por_tema.get(
                tema,
                [],
            )
        )

        if not candidatos_tema:
            raise RuntimeError((f"Não existem desafios ativos para o tema {tema}."))

        cursor.execute(
            """
            SELECT
                jd.desafio_id
            FROM jogador_desafios jd

            INNER JOIN jogadores j
                ON j.id = jd.jogador_id

            WHERE j.partida_id = %s
              AND jd.rodada = %s
            """,
            (
                partida_id,
                rodada,
            ),
        )

        usados_mesma_rodada = {item["desafio_id"] for item in cursor.fetchall()}

        candidatos = [
            desafio_id
            for desafio_id in candidatos_tema
            if desafio_id not in usados_pelo_jogador
            and desafio_id not in usados_mesma_rodada
        ]

        if not candidatos:
            candidatos = [
                desafio_id
                for desafio_id in candidatos_tema
                if desafio_id not in usados_pelo_jogador
            ]

        if not candidatos:
            candidatos = candidatos_tema

        desafio_id = random.choice(candidatos)

        escolhidos.append(
            (
                desafio_id,
                rodada,
            )
        )

        usados_pelo_jogador.add(desafio_id)

    return escolhidos


def segundos_restantes_partida(
    cursor,
    partida,
) -> int:

    if partida["status"] != "EM_ANDAMENTO" or partida["iniciado_em"] is None:
        return int(partida["duracao_segundos"])

    cursor.execute(
        """
        SELECT
            GREATEST(
                0,
                CEIL(
                    TIMESTAMPDIFF(
                        MICROSECOND,
                        NOW(6),
                        TIMESTAMPADD(
                            SECOND,
                            %s,
                            %s
                        )
                    )
                    / 1000000
                )
            ) AS segundos
        """,
        (
            partida["duracao_segundos"],
            partida["iniciado_em"],
        ),
    )

    return int(cursor.fetchone()["segundos"])


def rodada_liberada(
    cursor,
    partida,
) -> bool:

    if partida["status"] != "EM_ANDAMENTO" or partida["rodada_iniciada_em"] is None:
        return False

    cursor.execute(
        """
        SELECT
            NOW(6) >= %s AS liberada
        """,
        (partida["rodada_iniciada_em"],),
    )

    return bool(cursor.fetchone()["liberada"])


def segundos_restantes_rodada(
    cursor,
    partida,
) -> int:

    duracao = int(partida["duracao_rodada_segundos"])

    if partida["status"] != "EM_ANDAMENTO" or partida["rodada_iniciada_em"] is None:
        return duracao

    cursor.execute(
        """
        SELECT
            LEAST(
                %s,
                GREATEST(
                    0,
                    CEIL(
                        TIMESTAMPDIFF(
                            MICROSECOND,
                            NOW(6),
                            TIMESTAMPADD(
                                SECOND,
                                %s,
                                %s
                            )
                        )
                        / 1000000
                    )
                )
            ) AS segundos
        """,
        (
            duracao,
            duracao,
            partida["rodada_iniciada_em"],
        ),
    )

    return int(cursor.fetchone()["segundos"])


def _epoch_ms(
    valor,
):
    if valor is None:
        return None

    return int(float(valor) * 1000)


def dados_relogio_sincronizado(
    cursor,
    partida,
):
    """
    Retorna timestamps absolutos calculados pelo MySQL.
    """

    cursor.execute(
        """
        SELECT
            UNIX_TIMESTAMP(
                NOW(6)
            ) AS servidor_agora,

            CASE
                WHEN %s IS NULL
                    THEN NULL
                ELSE UNIX_TIMESTAMP(
                    %s
                )
            END AS partida_inicia_em,

            CASE
                WHEN %s IS NULL
                    THEN NULL
                ELSE UNIX_TIMESTAMP(
                    TIMESTAMPADD(
                        SECOND,
                        %s,
                        %s
                    )
                )
            END AS partida_termina_em,

            CASE
                WHEN %s IS NULL
                    THEN NULL
                ELSE UNIX_TIMESTAMP(
                    %s
                )
            END AS rodada_inicia_em,

            CASE
                WHEN %s IS NULL
                    THEN NULL
                ELSE UNIX_TIMESTAMP(
                    TIMESTAMPADD(
                        SECOND,
                        %s,
                        %s
                    )
                )
            END AS rodada_termina_em
        """,
        (
            partida["iniciado_em"],
            partida["iniciado_em"],
            partida["iniciado_em"],
            partida["duracao_segundos"],
            partida["iniciado_em"],
            partida["rodada_iniciada_em"],
            partida["rodada_iniciada_em"],
            partida["rodada_iniciada_em"],
            partida["duracao_rodada_segundos"],
            partida["rodada_iniciada_em"],
        ),
    )

    relogio = cursor.fetchone()

    return {
        "servidor_agora_ms": (_epoch_ms(relogio["servidor_agora"])),
        "partida_inicia_em_ms": (_epoch_ms(relogio["partida_inicia_em"])),
        "partida_termina_em_ms": (_epoch_ms(relogio["partida_termina_em"])),
        "rodada_inicia_em_ms": (_epoch_ms(relogio["rodada_inicia_em"])),
        "rodada_termina_em_ms": (_epoch_ms(relogio["rodada_termina_em"])),
    }


def verificar_andamento_rodada(
    cursor,
    partida,
    atraso_inicio_segundos: int = 1,
):
    rodada = int(partida["rodada_atual"])

    cursor.execute(
        """
        SELECT
            COUNT(*) AS total
        FROM jogadores
        WHERE partida_id = %s
        """,
        (partida["id"],),
    )

    total_jogadores = int(cursor.fetchone()["total"])

    cursor.execute(
        """
        SELECT
            COUNT(*) AS prontos
        FROM jogadores
        WHERE partida_id = %s
          AND rodadas_concluidas >= %s
        """,
        (
            partida["id"],
            rodada,
        ),
    )

    jogadores_prontos = int(cursor.fetchone()["prontos"])

    todos_concluiram = total_jogadores > 0 and jogadores_prontos == total_jogadores

    if not todos_concluiram:
        return {
            "todos_concluiram": False,
            "jogadores_prontos": (jogadores_prontos),
            "total_jogadores": (total_jogadores),
            "partida_finalizada": False,
            "nova_rodada": rodada,
        }

    if rodada < 10:
        nova_rodada = rodada + 1

        atraso = max(
            0,
            int(atraso_inicio_segundos),
        )

        cursor.execute(
            """
            UPDATE partidas
            SET
                rodada_atual = %s,
                rodada_iniciada_em = TIMESTAMPADD(
                    SECOND,
                    %s,
                    NOW(6)
                )
            WHERE id = %s
            """,
            (
                nova_rodada,
                atraso,
                partida["id"],
            ),
        )

        return {
            "todos_concluiram": True,
            "jogadores_prontos": (jogadores_prontos),
            "total_jogadores": (total_jogadores),
            "partida_finalizada": False,
            "nova_rodada": (nova_rodada),
        }

    cursor.execute(
        """
        UPDATE partidas
        SET
            status = 'FINALIZADA',
            motivo_fim = 'MISSAO_CONCLUIDA',
            finalizado_em = NOW(6)
        WHERE id = %s
        """,
        (partida["id"],),
    )

    return {
        "todos_concluiram": True,
        "jogadores_prontos": (jogadores_prontos),
        "total_jogadores": (total_jogadores),
        "partida_finalizada": True,
        "nova_rodada": 10,
    }


def processar_timeout_rodada(
    cursor,
    partida,
):
    """
    Ao acabar a janela de 20 segundos:
    - jogadores pendentes recebem a resposta correta;
    - recebem 200 pontos;
    - a tentativa fica marcada como timeout;
    - a rodada é concluída.
    """

    rodada = int(partida["rodada_atual"])

    cursor.execute(
        """
        SELECT
            id
        FROM jogadores
        WHERE partida_id = %s
          AND rodadas_concluidas < %s
        FOR UPDATE
        """,
        (
            partida["id"],
            rodada,
        ),
    )

    jogadores_pendentes = cursor.fetchall()

    for jogador in jogadores_pendentes:
        cursor.execute(
            """
            SELECT
                jd.id AS jogador_desafio_id,
                jd.desafio_id,
                d.resposta_correta

            FROM jogador_desafios jd

            INNER JOIN desafios d
                ON d.id = jd.desafio_id

            WHERE jd.jogador_id = %s
              AND jd.rodada = %s
            """,
            (
                jogador["id"],
                rodada,
            ),
        )

        desafio = cursor.fetchone()

        if desafio is None:
            continue

        cursor.execute(
            """
            SELECT
                id
            FROM tentativas
            WHERE jogador_id = %s
              AND jogador_desafio_id = %s
              AND correta = TRUE
            LIMIT 1
            """,
            (
                jogador["id"],
                desafio["jogador_desafio_id"],
            ),
        )

        if cursor.fetchone() is not None:
            continue

        cursor.execute(
            """
            SELECT
                COUNT(*) AS quantidade
            FROM tentativas
            WHERE jogador_id = %s
              AND jogador_desafio_id = %s
            """,
            (
                jogador["id"],
                desafio["jogador_desafio_id"],
            ),
        )

        numero_tentativa = int(cursor.fetchone()["quantidade"]) + 1

        # No banco guardamos sempre a letra ORIGINAL.
        # A conversão para a letra que apareceu na tela
        # acontece na rota de estado do jogador.
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
                200,
                TRUE
            )
            """,
            (
                jogador["id"],
                desafio["jogador_desafio_id"],
                numero_tentativa,
                desafio["resposta_correta"],
            ),
        )

        if rodada == 10:
            cursor.execute(
                """
                UPDATE jogadores
                SET
                    pontuacao = (
                        pontuacao + 200
                    ),
                    rodadas_concluidas = %s,
                    finalizado = TRUE,
                    finalizado_em = NOW(6)
                WHERE id = %s
                """,
                (
                    rodada,
                    jogador["id"],
                ),
            )

        else:
            cursor.execute(
                """
                UPDATE jogadores
                SET
                    pontuacao = (
                        pontuacao + 200
                    ),
                    rodadas_concluidas = %s
                WHERE id = %s
                """,
                (
                    rodada,
                    jogador["id"],
                ),
            )


def atualizar_estado_partida(
    conexao,
    cursor,
    partida_id: int,
):
    cursor.execute(
        """
        SELECT *
        FROM partidas
        WHERE id = %s
        FOR UPDATE
        """,
        (partida_id,),
    )

    partida = cursor.fetchone()

    if partida is None:
        conexao.rollback()
        return None

    if partida["status"] != "EM_ANDAMENTO":
        conexao.commit()
        return partida

    if (
        segundos_restantes_partida(
            cursor,
            partida,
        )
        <= 0
    ):
        cursor.execute(
            """
            UPDATE partidas
            SET
                status = 'FALHOU',
                motivo_fim = 'TEMPO_GERAL_ESGOTADO',
                finalizado_em = NOW(6)
            WHERE id = %s
            """,
            (partida_id,),
        )

        conexao.commit()

        cursor.execute(
            """
            SELECT *
            FROM partidas
            WHERE id = %s
            """,
            (partida_id,),
        )

        return cursor.fetchone()

    if (
        segundos_restantes_rodada(
            cursor,
            partida,
        )
        <= 0
    ):
        processar_timeout_rodada(
            cursor,
            partida,
        )

        verificar_andamento_rodada(
            cursor,
            partida,
            atraso_inicio_segundos=3,
        )

    conexao.commit()

    cursor.execute(
        """
        SELECT *
        FROM partidas
        WHERE id = %s
        """,
        (partida_id,),
    )

    return cursor.fetchone()

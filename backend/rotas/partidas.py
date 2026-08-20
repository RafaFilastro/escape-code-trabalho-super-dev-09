import os
import random

from banco import conectar
from fastapi import APIRouter, Depends, HTTPException
from regras_jogo import (
    PROTOCOLOS,
    atualizar_estado_partida,
    gerar_chave_mestre,
    gerar_codigo_partida,
)
from seguranca_admin import validar_chave_admin

router = APIRouter(tags=["Partidas"])


@router.post(
    "/partidas",
    dependencies=[Depends(validar_chave_admin)],
)
def criar_partida():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id
        FROM partidas
        WHERE status IN ('AGUARDANDO', 'EM_ANDAMENTO')
        LIMIT 1
        """
    )

    if cursor.fetchone() is not None:
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=409,
            detail="Já existe uma operação aguardando ou em andamento.",
        )

    duracao_partida = int(
        os.getenv(
            "DURACAO_PARTIDA_SEGUNDOS",
            "180",
        )
    )

    duracao_rodada = int(
        os.getenv(
            "DURACAO_RODADA_SEGUNDOS",
            "20",
        )
    )

    codigo = gerar_codigo_partida()
    protocolo = random.choice(PROTOCOLOS)
    chave_mestre = gerar_chave_mestre()

    cursor.execute(
        """
        INSERT INTO partidas (
            codigo,
            nome_protocolo,
            duracao_segundos,
            duracao_rodada_segundos,
            chave_mestre
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            codigo,
            protocolo,
            duracao_partida,
            duracao_rodada,
            chave_mestre,
        ),
    )

    partida_id = cursor.lastrowid
    conexao.commit()

    cursor.execute(
        """
        SELECT *
        FROM partidas
        WHERE id = %s
        """,
        (partida_id,),
    )

    partida = cursor.fetchone()

    cursor.close()
    conexao.close()

    return partida


@router.post(
    "/partidas/{partida_id}/iniciar",
    dependencies=[Depends(validar_chave_admin)],
)
def iniciar_partida(partida_id: int):
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

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
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=404,
            detail="Operação não encontrada.",
        )

    if partida["status"] != "AGUARDANDO":
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=400,
            detail="A operação não está aguardando início.",
        )

    cursor.execute(
        """
        SELECT COUNT(*) AS quantidade
        FROM jogadores
        WHERE partida_id = %s
        """,
        (partida_id,),
    )

    total_jogadores = int(cursor.fetchone()["quantidade"])

    if total_jogadores == 0:
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=400,
            detail="Cadastre pelo menos um codinome antes de iniciar.",
        )

    cursor.execute(
        """
        UPDATE partidas
        SET
            status = 'EM_ANDAMENTO',
            rodada_atual = 1,
            iniciado_em = NOW(6),
            rodada_iniciada_em = NOW(6)
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

    partida = cursor.fetchone()

    cursor.close()
    conexao.close()

    return partida


@router.get("/partidas/ativa")
def obter_partida_ativa():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM partidas
        WHERE status IN ('AGUARDANDO', 'EM_ANDAMENTO')
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
            detail="Nenhuma operação disponível.",
        )

    if partida["status"] == "EM_ANDAMENTO":
        partida = atualizar_estado_partida(
            conexao,
            cursor,
            partida["id"],
        )

    if partida["status"] not in (
        "AGUARDANDO",
        "EM_ANDAMENTO",
    ):
        cursor.close()
        conexao.close()

        raise HTTPException(
            status_code=404,
            detail="Nenhuma operação disponível.",
        )

    cursor.execute(
        """
        SELECT COUNT(*) AS quantidade
        FROM jogadores
        WHERE partida_id = %s
        """,
        (partida["id"],),
    )

    partida["quantidade_jogadores"] = int(cursor.fetchone()["quantidade"])

    cursor.close()
    conexao.close()

    return partida

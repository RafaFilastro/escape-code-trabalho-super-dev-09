import os
import secrets
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()


def validar_chave_admin(
    x_admin_key: Annotated[
        str | None,
        Header(alias="X-Admin-Key"),
    ] = None,
):
    chave_configurada = os.getenv("ADMIN_CHAVE")

    if not chave_configurada:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_CHAVE não foi configurada no backend.",
        )

    if x_admin_key is None or not secrets.compare_digest(
        x_admin_key,
        chave_configurada,
    ):
        raise HTTPException(
            status_code=401,
            detail="Acesso administrativo não autorizado.",
        )

    return True

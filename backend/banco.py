import os

from dotenv import load_dotenv
from mysql import connector

load_dotenv()


def conectar():
    return connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(
            os.getenv(
                "DB_PORT",
                "3306",
            )
        ),
        user=os.getenv(
            "DB_USUARIO",
            "root",
        ),
        password=os.getenv(
            "DB_SENHA",
            "",
        ),
        database=os.getenv(
            "DB_BANCO",
            "escape_code",
        ),
    )

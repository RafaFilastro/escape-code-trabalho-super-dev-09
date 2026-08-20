from fastapi import APIRouter, Depends
from seguranca_admin import validar_chave_admin

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get(
    "/validar",
    dependencies=[Depends(validar_chave_admin)],
)
def validar_admin():
    return {"autorizado": True}

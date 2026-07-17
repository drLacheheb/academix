from fastapi import APIRouter, Depends, Request
from api.dependencies import get_status_usecase, GetDatabaseStatusUseCase
from api.limiter_config import limiter

router = APIRouter()


@router.get("/status")
@limiter.limit("120/minute")
async def health_status(
    request: Request, usecase: GetDatabaseStatusUseCase = Depends(get_status_usecase)
):
    return usecase.execute()

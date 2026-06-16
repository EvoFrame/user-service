from fastapi import APIRouter

from src.routers.users import router as users_router

router = APIRouter()
router.include_router(users_router)

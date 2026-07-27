from fastapi import APIRouter

from app.api.v1 import auth, coach, entrenamientos, ingesta, metricas, usuarios

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(usuarios.router)
api_router.include_router(entrenamientos.router)
api_router.include_router(metricas.router)
api_router.include_router(ingesta.router)
api_router.include_router(coach.router)

"""
API Routes Package Initialization
Aggregates all sub-routers under a unified api_router.
"""

from fastapi import APIRouter
from backend.api.routes.cells import router as cells_router
from backend.api.routes.health import router as health_router
from backend.api.routes.mining import router as mining_router
from backend.api.routes.network import router as network_router
from backend.api.routes.olap import router as olap_router
from backend.api.routes.simulation import router as simulation_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(cells_router)
api_router.include_router(network_router)
api_router.include_router(olap_router)
api_router.include_router(mining_router)
api_router.include_router(simulation_router)

__all__ = ["api_router"]

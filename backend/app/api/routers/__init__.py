"""Routenmodule, ein Modul je fachlichem Bereich."""

from fastapi import APIRouter

from app.api.routers import (
    admin,
    assets,
    auth,
    bewertungen,
    cockpit,
    integration,
    lenkung,
    organisation,
    prozesse,
    verpflichtung,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(organisation.router)
api_router.include_router(prozesse.router)
api_router.include_router(bewertungen.router)
api_router.include_router(assets.router)
api_router.include_router(verpflichtung.router)
api_router.include_router(lenkung.router)
api_router.include_router(cockpit.router)
api_router.include_router(integration.router)

__all__ = ["api_router"]

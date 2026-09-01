"""FastAPI-Anwendung der Governance-Plattform.

Die API ist der Vertrag nach aussen: sie wird automatisch als OpenAPI
dokumentiert und dient damit zugleich als Vertrag fuer die Adapter- und die
Governance-Query-API (Architektur Abschnitt 7).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import api_router
from app.config import get_settings
from app.core.permissions import Verboten
from app.services.prozess import NichtGefunden, Ungueltig


def erstelle_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(
        title="Governance-Plattform",
        version="0.1.0",
        description=(
            "Verwaltungsschicht der Governance: Prozess-, Tool- und Datenobjekte, "
            "Bewertungen, Selbstverpflichtungen, Gates, Lenkung und Cockpit."
        ),
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Verboten)
    async def _verboten(_: Request, exc: Verboten) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.detail})

    @app.exception_handler(NichtGefunden)
    async def _nicht_gefunden(_: Request, exc: NichtGefunden) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.detail})

    @app.exception_handler(Ungueltig)
    async def _ungueltig(_: Request, exc: Ungueltig) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.detail})

    @app.get("/health", tags=["Betrieb"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router)
    return app


app = erstelle_app()

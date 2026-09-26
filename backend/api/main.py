"""
Main FastAPI Application Module
Telecom Churn & Network Analysis API Service Layer.
Configures CORS, centralized exception handlers, documentation metadata, and routes.
"""

import os
from typing import List
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.routes import api_router
from backend.api.schemas import ApiErrorResponse, ErrorDetail

# -----------------------------------------------------------------------------
# APPLICATION CONFIGURATION & METADATA
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Telecom Churn & Network Analysis API",
    description=(
        "Production-grade REST API service connecting SQLite Star Schema Data Warehouse, "
        "Multidimensional OLAP Engine, Supervised & Unsupervised Data Mining Models, "
        "and In-Memory Telecom Network Simulation Engine to interactive frontend dashboards."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# -----------------------------------------------------------------------------
# CORS CONFIGURATION
# -----------------------------------------------------------------------------
raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175",
)
allowed_origins: List[str] = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# STRUCTURED EXCEPTION HANDLERS
# -----------------------------------------------------------------------------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Formats HTTP exceptions into the uniform ApiErrorResponse envelope."""
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        error_detail = exc.detail
    else:
        error_detail = {
            "code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
        }

    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": error_detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats Pydantic request validation errors into uniform error response."""
    error_messages = []
    for err in exc.errors():
        field_loc = " -> ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid parameter")
        error_messages.append(f"{field_loc}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "; ".join(error_messages),
            },
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catches unhandled exceptions and shields internal stack traces from clients."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred. Please contact the administrator.",
            },
        },
    )


# -----------------------------------------------------------------------------
# ROUTER MOUNTING
# -----------------------------------------------------------------------------
app.include_router(api_router, prefix="/api")


@app.get("/", tags=["Root"])
def root_service_info():
    """Returns top-level API service metadata and documentation links."""
    return {
        "service": "Telecom Churn & Network Analysis API",
        "version": "1.0.0",
        "documentation": "/docs",
        "redoc": "/redoc",
        "health": "/api/health",
        "status": "online",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8000, reload=True)

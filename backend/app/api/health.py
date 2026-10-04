import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from app.database.connection import check_database

router = APIRouter()
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    database: str


@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
def health(request: Request):
    try:
        check_database(request.app.state.engine)
    except SQLAlchemyError:
        # Avoid logging connection strings or database exception details.
        logger.warning("database_healthcheck_failed")
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "disconnected"})
    return HealthResponse(status="ok", database="connected")

from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.menus import router as menus_router
from app.api.menu_items import router as menu_items_router
from app.api.search import router as search_router
from app.api.images import router as images_router
from app.api.places import router as places_router
from app.api.demo import router as demo_router
from app.core.errors import ServiceError
from app.core.upload_limit import UploadLimitMiddleware
from app.models import Base
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.connection import create_database_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    app.state.engine = create_database_engine()
    try:
        Base.metadata.create_all(app.state.engine)
        from app.services.extraction_service import recover_interrupted
        recover_interrupted(app.state.engine)
        from app.services.explanation_service import recover_explanations
        recover_explanations(app.state.engine)
        from app.services.image_service import recover_images
        recover_images(app.state.engine)
        if get_settings().seed_demo:
            from app.services.demo_service import seed_demo
            seed_demo(app.state.engine, get_settings())
        yield
    finally:
        app.state.engine.dispose()


app = FastAPI(title="MenuLens API", version="0.1.0", lifespan=lifespan)
app.add_middleware(UploadLimitMiddleware, max_bytes=get_settings().max_upload_bytes + 1024 * 1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(router)

app.include_router(menus_router)
app.include_router(menu_items_router)
app.include_router(search_router)
app.include_router(images_router)
app.include_router(places_router)
app.include_router(demo_router)


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    import logging
    logging.getLogger(__name__).warning("database_request_failed")
    return JSONResponse(status_code=503, content={"detail": "The menu service is temporarily unavailable. Please try again."})

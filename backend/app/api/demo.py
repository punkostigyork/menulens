from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database.session import get_session
from app.services.demo_service import DATA_DIR, DEMO_ID
from app.models import Menu

router = APIRouter(prefix="/api/demo", tags=["demo"])

@router.get("")
def demo_info(session: Session = Depends(get_session)):
    menu = session.get(Menu, DEMO_ID)
    return {"menu_id": str(DEMO_ID) if menu else None}

@router.get("/source")
def demo_source():
    return FileResponse(DATA_DIR / "hungarian-menu.pdf", media_type="application/pdf", filename="menulens-hungarian-sample.pdf")

from fastapi import APIRouter

# DB entegrasyonu hazır olunca aktif edilecek:
# from fastapi import Depends
# from sqlalchemy import text
# from sqlalchemy.orm import Session
# from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health", summary="Uygulama ayakta mi")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# DB entegrasyonu hazır olunca aktif edilecek:
# @router.get("/health/db", summary="Veritabani baglantisi calisiyor mu")
# async def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
#     db.execute(text("SELECT 1"))
#     return {"status": "ok", "database": "reachable"}

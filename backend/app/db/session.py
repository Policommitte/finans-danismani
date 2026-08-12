"""DB oturum yonetimi — DB entegrasyonu hazir olunca asagidaki kod aktif edilecek.

Aktif etmeden once yapilmasi gerekenler:
- requirements.txt'e sqlalchemy ve psycopg geri eklenmeli
- config.py'deki database_url alani ve .env.example'daki DATABASE_URL acilmali
- api/routes/health.py icindeki /health/db endpoint'i acilmali
"""

# from collections.abc import Generator
# from functools import lru_cache
#
# from sqlalchemy import create_engine
# from sqlalchemy.engine import Engine
# from sqlalchemy.orm import Session, sessionmaker
#
# from app.config import settings
#
#
# @lru_cache
# def get_engine() -> Engine:
#     """Engine'i ilk kullanimda olusturur. Import aninda olusturulsaydi,
#     DB surucusu kurulu olmayan gelistiricide uygulama hic acilmazdi."""
#     return create_engine(settings.database_url, pool_pre_ping=True)
#
#
# def get_db() -> Generator[Session, None, None]:
#     session_factory = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
#     db = session_factory()
#     try:
#         yield db
#     finally:
#         db.close()

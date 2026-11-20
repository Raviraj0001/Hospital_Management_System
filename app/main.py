from contextlib import asynccontextmanager
from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, engine, SessionLocal
from . import models  # Import models before creating database tables.
from .security import hash_password
from .auth import router as auth_router
from .hospital import router as hospital_router
from .care import router as care_router
from .models import User


def prepare_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin_email = os.getenv("HMS_ADMIN_EMAIL", "admin@gmail.com").strip().lower()
        admin_password = os.getenv("HMS_ADMIN_PASSWORD", "Admin@123")
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            db.add(User(
                email=admin_email,
                password_hash=hash_password(admin_password),
                role="admin",
                is_active=True,
            ))
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    prepare_database()
    yield


app = FastAPI(
    title="Hospital Management Portal",
    version="2.0.0",
    description="Role-based hospital management portal built with FastAPI and SQLite.",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(hospital_router)
app.include_router(care_router)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "dashboard.html")

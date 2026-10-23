from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import STORAGE_DIR, FRONTEND_DIR
from app.database import engine
from app.models import Base
from app.services.scheduler import start_scheduler
from app.api import auth, bots, tournaments, matches, leaderboard, admin, seasons


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield


app = FastAPI(title="OTTv2 Bot Arena API", version="2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")

app.include_router(auth.router)
app.include_router(bots.router)
app.include_router(tournaments.router)
app.include_router(matches.router)
app.include_router(leaderboard.router)
app.include_router(admin.router)
app.include_router(seasons.router)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend_static")

    @app.get("/")
    def serve_index():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"status": "online", "message": "Backend sẵn sàng. Hãy tạo file index.html trong thư mục frontend."}

    @app.get("/admin")
    def serve_admin():
        admin_file = FRONTEND_DIR / "admin.html"
        if admin_file.exists():
            return FileResponse(admin_file)
        return {"status": "error", "message": "Chưa có file admin.html"}
else:
    @app.get("/")
    def health_check():
        return {"status": "online", "system": "OTTv2 Arena Engine"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
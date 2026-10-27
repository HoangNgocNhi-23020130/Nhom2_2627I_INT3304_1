import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent

STORAGE_DIR = ROOT_DIR / "storage"
BOTS_DIR = STORAGE_DIR / "bots"
REPLAYS_DIR = STORAGE_DIR / "replays"
SHARED_DIR = ROOT_DIR / "shared"
FRONTEND_DIR = ROOT_DIR / "frontend"

RULES_FILE = SHARED_DIR / "rules.json"
RULES_PATH = RULES_FILE

BOTS_DIR.mkdir(parents=True, exist_ok=True)
REPLAYS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SQLITE_URL = f"sqlite:///{BACKEND_DIR}/arena.db"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URL)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SECRET_KEY = os.environ.get("SECRET_KEY", "ottv2_dev_secret_key_default_32chars_long")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = {".py", ".cpp", ".js"}

DEFAULT_BOT_TIMEOUT = float(os.environ.get("DEFAULT_BOT_TIMEOUT", "0.5"))
DEFAULT_MAX_TURNS = int(os.environ.get("DEFAULT_MAX_TURNS", "200"))
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Bot, User, Match, TournamentStanding
from app.services.compiler import prepare_bot, CompilerError
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/bots", tags=["Bots"])


class BotUpdateRequest(BaseModel):
    name: str


@router.get("/system-bots")
def get_system_bots(db: Session = Depends(get_db)):
    system_user = db.query(User).filter(User.role == "system").first()
    query = db.query(Bot)
    if system_user:
        query = query.filter(Bot.user_id == system_user.id)
    return [
        {"id": b.id, "name": b.name, "language": b.language}
        for b in query.all()
    ]


@router.get("/my")
def get_my_bots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "admin":
        return []

    db.expire_all()
    bots = db.query(Bot).filter(Bot.user_id == current_user.id).order_by(Bot.created_at.desc()).all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "language": b.language,
            "is_active": bool(b.is_active),
            "created_at": b.created_at.strftime("%d/%m/%Y %H:%M")
        }
        for b in bots
    ]


@router.post("/{bot_id}/set-active")
def set_active_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "admin":
        raise HTTPException(status_code=403, detail="Tài khoản Admin không tham gia thi đấu.")

    target_bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == current_user.id).first()
    if not target_bot:
        raise HTTPException(status_code=404, detail="Bot không tồn tại hoặc không thuộc sở hữu của bạn.")

    db.query(Bot).filter(Bot.user_id == current_user.id).update({"is_active": False}, synchronize_session=False)
    db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == current_user.id).update({"is_active": True}, synchronize_session=False)
    db.commit()

    return {"message": f"Đã kích hoạt '{target_bot.name}' làm bot thi đấu chính thức!", "bot_id": bot_id}


@router.put("/{bot_id}")
def update_bot(
    bot_id: int,
    req: BotUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == current_user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot không tồn tại hoặc không thuộc sở hữu của bạn.")

    new_name = req.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Tên bot không được để trống.")

    existing = db.query(Bot).filter(Bot.name == new_name, Bot.id != bot_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên bot này đã tồn tại.")

    bot.name = new_name
    db.commit()
    return {"message": f"Đã đổi tên bot thành '{new_name}' thành công!"}


@router.delete("/{bot_id}")
def delete_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == current_user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot không tồn tại hoặc không thuộc sở hữu của bạn.")

    was_active = bot.is_active
    bot_name = bot.name

    if bot.source_path and Path(bot.source_path).exists():
        try:
            Path(bot.source_path).unlink()
        except Exception:
            pass

    if bot.binary_path and Path(bot.binary_path).exists():
        try:
            Path(bot.binary_path).unlink()
        except Exception:
            pass

    db.query(Match).filter((Match.bot1_id == bot_id) | (Match.bot2_id == bot_id)).delete()
    db.query(TournamentStanding).filter(TournamentStanding.bot_id == bot_id).delete()

    db.delete(bot)
    db.commit()

    if was_active:
        remaining_bot = db.query(Bot).filter(Bot.user_id == current_user.id).first()
        if remaining_bot:
            remaining_bot.is_active = True
            db.commit()

    return {"message": f"Đã xóa bot '{bot_name}' thành công!"}


@router.post("/upload")
async def upload_bot(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "admin":
        raise HTTPException(status_code=403, detail="Tài khoản Admin không được phép nộp bot thi đấu.")

    content = await file.read()
    code_text = content.decode("utf-8", errors="ignore")

    try:
        base_name, language, binary_path = prepare_bot(file.filename, content)
    except CompilerError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user_bot_count = db.query(Bot).filter(Bot.user_id == current_user.id).count()
    is_first = (user_bot_count == 0)

    bot = Bot(
        user_id=current_user.id,
        name=base_name,
        language=language,
        code=code_text,
        source_path=f"storage/bots/{file.filename}",
        binary_path=binary_path,
        is_active=is_first
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)

    return {"message": f"Nộp bot '{base_name}' thành công!", "bot_id": bot.id, "is_active": is_first}
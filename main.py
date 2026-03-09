# -*- coding: utf-8 -*-

import os
from typing import Optional

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Depends,
    Body,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, UsageLog
from schemas import UserSignup, UserLogin
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_access_token,
)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client: Optional[OpenAI] = None
if OpenAI and OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)


app = FastAPI(
    title="AI FastAPI Server",
    description="Whisper STT + 회원가입/로그인/관리자 API",
    version="2.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

security = HTTPBearer()

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a"}
MAX_FILE_SIZE = 25 * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)


def validate_audio_file(filename: str):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 허용 형식: {', '.join(ALLOWED_EXTENSIONS)}"
        )


def save_upload_file(upload_file: UploadFile, contents: bytes) -> str:
    file_path = os.path.join(UPLOAD_DIR, upload_file.filename)
    with open(file_path, "wb") as f:
        f.write(contents)
    return file_path


def get_today_usage_count(db: Session, user_id: int) -> int:
    count = (
        db.query(func.count(UsageLog.id))
        .filter(
            UsageLog.user_id == user_id,
            func.date(UsageLog.created_at) == func.current_date(),
            UsageLog.status == "success"
        )
        .scalar()
    )
    return count or 0


def check_user_can_use_stt(db: Session, user: User):
    if not user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다.")

    if not user.can_use_stt:
        raise HTTPException(status_code=403, detail="STT 사용 권한이 없습니다.")

    if user.is_unlimited:
        return

    today_usage_count = get_today_usage_count(db, user.id)

    if today_usage_count >= user.daily_limit:
        raise HTTPException(status_code=403, detail="오늘 사용 한도를 초과했습니다.")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = verify_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="토큰에 사용자 정보가 없습니다.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return user


def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")
    return current_user


@app.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/login-page", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/signup-page", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@app.get("/admin-page", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/stt-page", response_class=HTMLResponse)
def stt_page(request: Request):
    return templates.TemplateResponse("stt.html", {"request": request})


@app.get("/health")
def health():
    return {"message": "FastAPI 서버 실행 중"}


@app.post("/signup")
def signup(user: UserSignup, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")

    new_user = User(
        email=user.email,
        password_hash=hash_password(user.password),
        is_admin=False,
        is_active=True,
        can_use_stt=False,
        is_unlimited=False,
        daily_limit=10
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "회원가입 완료",
        "email": new_user.email
    }


@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    try:
        password_ok = verify_password(user.password, db_user.password_hash)
    except Exception:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    if not password_ok:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    access_token = create_access_token(
        data={
            "sub": db_user.email,
            "is_admin": db_user.is_admin
        }
    )

    return {
        "message": "로그인 성공",
        "access_token": access_token,
        "token_type": "bearer",
        "email": db_user.email,
        "is_admin": db_user.is_admin,
        "is_active": db_user.is_active,
        "can_use_stt": db_user.can_use_stt,
        "is_unlimited": db_user.is_unlimited,
        "daily_limit": db_user.daily_limit
    }


@app.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active,
        "can_use_stt": current_user.can_use_stt,
        "is_unlimited": current_user.is_unlimited,
        "daily_limit": current_user.daily_limit
    }


@app.get("/my/usage/today")
def get_my_today_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today_count = get_today_usage_count(db, current_user.id)

    return {
        "email": current_user.email,
        "today_usage_count": today_count,
        "daily_limit": current_user.daily_limit,
        "is_unlimited": current_user.is_unlimited
    }


@app.get("/admin/users")
def get_users(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()

    result = []
    for user in users:
        result.append({
            "id": user.id,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "can_use_stt": user.can_use_stt,
            "is_unlimited": user.is_unlimited,
            "daily_limit": user.daily_limit
        })

    return result


@app.post("/admin/users/enable")
def enable_user(
    email: str = Body(..., embed=True),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    user.can_use_stt = True
    db.commit()
    db.refresh(user)

    return {
        "message": "사용자 STT 사용 승인 완료",
        "email": user.email,
        "can_use_stt": user.can_use_stt
    }


@app.post("/admin/users/disable")
def disable_user(
    email: str = Body(..., embed=True),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    user.can_use_stt = False
    db.commit()
    db.refresh(user)

    return {
        "message": "사용자 STT 사용 차단 완료",
        "email": user.email,
        "can_use_stt": user.can_use_stt
    }


@app.post("/admin/users/set-unlimited")
def set_unlimited_user(
    email: str = Body(..., embed=True),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    user.can_use_stt = True
    user.is_unlimited = True
    db.commit()
    db.refresh(user)

    return {
        "message": "무제한 사용자 설정 완료",
        "email": user.email,
        "is_unlimited": user.is_unlimited
    }


@app.post("/admin/users/set-limited")
def set_limited_user(
    email: str = Body(..., embed=True),
    daily_limit: int = Body(..., embed=True),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    if daily_limit < 1:
        raise HTTPException(status_code=400, detail="daily_limit는 1 이상이어야 합니다.")

    user.is_unlimited = False
    user.daily_limit = daily_limit
    db.commit()
    db.refresh(user)

    return {
        "message": "일일 제한 사용자 설정 완료",
        "email": user.email,
        "is_unlimited": user.is_unlimited,
        "daily_limit": user.daily_limit
    }


@app.get("/admin/usage/today")
def get_today_usage(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()

    result = []
    for user in users:
        today_count = get_today_usage_count(db, user.id)
        result.append({
            "email": user.email,
            "today_usage_count": today_count,
            "daily_limit": user.daily_limit,
            "is_unlimited": user.is_unlimited
        })

    return result


@app.post("/stt")
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_user_can_use_stt(db, current_user)

    validate_audio_file(file.filename)

    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일 크기가 제한을 초과했습니다.")

    file_path = save_upload_file(file, contents)

    if client is None:
        raise HTTPException(
            status_code=500,
            detail="OpenAI 클라이언트가 준비되지 않았습니다. OPENAI_API_KEY 또는 openai 패키지를 확인하세요."
        )

    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file
            )

        usage_log = UsageLog(
            user_id=current_user.id,
            file_name=file.filename,
            status="success"
        )
        db.add(usage_log)
        db.commit()

        return {
            "message": "STT 변환 완료",
            "email": current_user.email,
            "filename": file.filename,
            "text": transcript.text
        }

    except Exception as e:
        usage_log = UsageLog(
            user_id=current_user.id,
            file_name=file.filename,
            status="failed"
        )
        db.add(usage_log)
        db.commit()

        raise HTTPException(status_code=500, detail=f"STT 변환 실패: {str(e)}")
# -*- coding: utf-8 -*-

import os
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db
from models import User, UsageLog
from schemas import UserSignup, UserLogin
from auth import hash_password, verify_password

# OpenAI SDK를 쓰는 경우에만 필요
# openai 패키지 버전이 1.x 이상일 때 사용
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# =========================
# 환경변수
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI SDK 사용 가능하고 키가 있으면 client 생성
client: Optional[OpenAI] = None
if OpenAI and OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)


# =========================
# FastAPI 앱 생성
# =========================
app = FastAPI(
    title="AI FastAPI Server",
    description="Whisper STT + 회원가입/로그인/관리자 API",
    version="2.0.0"
)

# 필요하면 프론트엔드 연동용 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# 파일 업로드 설정
# =========================
UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a"}
MAX_FILE_SIZE = 25 * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================
# 공통 함수
# =========================
def validate_audio_file(filename: str):
    """
    업로드 파일 확장자 검사
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 허용 형식: {', '.join(ALLOWED_EXTENSIONS)}"
        )


def save_upload_file(upload_file: UploadFile, contents: bytes) -> str:
    """
    업로드된 파일을 uploads 폴더에 저장
    """
    file_path = os.path.join(UPLOAD_DIR, upload_file.filename)
    with open(file_path, "wb") as f:
        f.write(contents)
    return file_path


def get_admin_user(db: Session = Depends(get_db)):
    """
    현재 단계에서는 관리자 계정을 이메일로 고정해서 확인
    나중에는 JWT 로그인 기반으로 교체해야 함
    """
    admin_user = db.query(User).filter(User.email == "namtaeyang@gmail.com").first()

    if not admin_user:
        raise HTTPException(status_code=404, detail="관리자 계정을 찾을 수 없습니다.")

    if not admin_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")

    return admin_user


def get_today_usage_count(db: Session, user_id: int) -> int:
    """
    오늘 성공한 사용 횟수 조회
    """
    from sqlalchemy import func

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
    """
    STT 사용 가능 여부 검사
    """
    if not user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다.")

    if not user.can_use_stt:
        raise HTTPException(status_code=403, detail="STT 사용 권한이 없습니다.")

    if user.is_unlimited:
        return

    today_usage_count = get_today_usage_count(db, user.id)

    if today_usage_count >= user.daily_limit:
        raise HTTPException(status_code=403, detail="오늘 사용 한도를 초과했습니다.")


# =========================
# 기본 확인용
# =========================
@app.get("/")
def root():
    return {"message": "FastAPI 서버 실행 중"}


# =========================
# 회원가입 API
# =========================
@app.post("/signup")
def signup(user: UserSignup, db: Session = Depends(get_db)):
    """
    회원가입
    - 같은 이메일이 있으면 가입 불가
    - 가입 직후에는 STT 사용 불가
    """
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


# =========================
# 로그인 API
# =========================
@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    """
    로그인
    - 이메일/비밀번호 확인
    """
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    return {
        "message": "로그인 성공",
        "email": db_user.email,
        "is_admin": db_user.is_admin,
        "is_active": db_user.is_active,
        "can_use_stt": db_user.can_use_stt,
        "is_unlimited": db_user.is_unlimited,
        "daily_limit": db_user.daily_limit
    }


# =========================
# 관리자 - 전체 사용자 목록 조회
# =========================
@app.get("/admin/users")
def get_users(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    전체 사용자 목록 조회
    현재는 관리자 계정 이메일 고정 방식으로 보호
    """
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


# =========================
# 관리자 - 특정 사용자 STT 사용 승인
# =========================
@app.post("/admin/users/enable")
def enable_user(
    email: str = Body(..., embed=True),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    특정 사용자의 STT 사용 승인
    """
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


# =========================
# 관리자 - 특정 사용자 STT 사용 차단
# =========================
@app.post("/admin/users/disable")
def disable_user(
    email: str = Body(..., embed=True),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    특정 사용자의 STT 사용 차단
    """
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


# =========================
# 관리자 - 특정 사용자 무제한 사용 설정
# =========================
@app.post("/admin/users/set-unlimited")
def set_unlimited_user(
    email: str = Body(..., embed=True),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    특정 사용자를 무제한 사용자로 변경
    """
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


# =========================
# 관리자 - 특정 사용자 일일 제한 사용자로 변경
# =========================
@app.post("/admin/users/set-limited")
def set_limited_user(
    email: str = Body(..., embed=True),
    daily_limit: int = Body(..., embed=True),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    특정 사용자를 제한 사용자로 변경
    """
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


# =========================
# 관리자 - 사용자별 오늘 사용량 조회
# =========================
@app.get("/admin/usage/today")
def get_today_usage(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    오늘 사용자별 STT 사용량 조회
    """
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


# =========================
# STT API
# =========================
@app.post("/stt")
async def transcribe_audio(
    email: str = Body(..., embed=True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    음성 파일 업로드 후 STT 변환
    현재는 로그인 토큰 없이 email로 사용자 식별
    나중에는 JWT 인증으로 바꿔야 함
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    check_user_can_use_stt(db, user)

    validate_audio_file(file.filename)

    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일 크기가 제한을 초과했습니다.")

    file_path = save_upload_file(file, contents)

    # OpenAI 클라이언트 준비 안 된 경우
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

        # 사용 성공 로그 저장
        usage_log = UsageLog(
            user_id=user.id,
            file_name=file.filename,
            status="success"
        )
        db.add(usage_log)
        db.commit()

        return {
            "message": "STT 변환 완료",
            "email": user.email,
            "filename": file.filename,
            "text": transcript.text
        }

    except Exception as e:
        # 실패 로그 저장
        usage_log = UsageLog(
            user_id=user.id,
            file_name=file.filename,
            status="failed"
        )
        db.add(usage_log)
        db.commit()

        raise HTTPException(status_code=500, detail=f"STT 변환 실패: {str(e)}")

@app.get("/my/usage/today")
def get_my_today_usage(
    email: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    today_count = get_today_usage_count(db, user.id)

    return {
        "email": user.email,
        "today_usage_count": today_count,
        "daily_limit": user.daily_limit,
        "is_unlimited": user.is_unlimited
    }
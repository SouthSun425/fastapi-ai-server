from database import SessionLocal
from models import User
from auth import verify_password

email = "test2@test.com"
password = "4321"

db = SessionLocal()

try:
    user = db.query(User).filter(User.email == email).first()

    if not user:
        print("사용자 없음")
    else:
        print("이메일:", user.email)
        print("저장된 해시:", user.password_hash)
        print("검증 결과:", verify_password(password, user.password_hash))
finally:
    db.close()
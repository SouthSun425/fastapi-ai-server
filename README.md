FastAPI 서버 실행

cd C:\fastapi-ai-server
venv\Scripts\activate
uvicorn main:app --reload

로컬 웹 서버 실행
cd C:\fastapi-ai-server
python -m http.server 5500

로컬 웹 주소
http://localhost:8000/

로그인: http://127.0.0.1:8000/login-page
회원가입: http://127.0.0.1:8000/signup-page
관리자: http://127.0.0.1:8000/admin-page
STT 페이지: http://127.0.0.1:8000/stt-page
)
postgre db 구성해야함
개인 api키와 postgre url값 .env를 만들어서 넣어야함
해당 프로젝트는 개발 환경 문제로 환경변수에 값을 넣어 불러오도록 설계하였음

26.03.09
api 서버와 로컬 웹 연결해서 테스트 성공


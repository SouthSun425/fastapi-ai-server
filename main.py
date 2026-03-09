# -*- coding: utf-8 -*-

import os
import io
import openai
from fastapi import FastAPI, UploadFile, File, HTTPException

# ==========================
# OpenAI API Key (Legacy)
# ==========================
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

# ==========================
# FastAPI App
# ==========================
app = FastAPI(
    title="AI FastAPI Server",
    description="Whisper STT + 요약 API (Legacy)",
    version="1.2.0"
)

# ==========================
# 설정
# ==========================
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

# ==========================
# 헬스 체크
# ==========================
@app.get("/health")
def health():
    return {"status": "ok"}

# ==========================
# STT + 요약 API
# ==========================
@app.post("/stt-summary")
async def speech_to_text_and_summary(file: UploadFile = File(...)):

    # -------- 파일 검증 --------
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 없습니다.")

    _, ext = os.path.splitext(file.filename)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="허용되지 않은 파일 형식")

    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일 용량 초과")

    # -------- 1️⃣ Whisper STT --------
    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = file.filename  # 🔥 Whisper가 필요로 하는 핵심

        stt_result = openai.Audio.transcribe(
            model="whisper-1",
            file=audio_file
        )
        stt_text = stt_result["text"]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT 실패: {str(e)}")

    # -------- 2️⃣ 요약 --------
    try:
        summary_prompt = f"""
아래는 음성 인식(STT) 결과입니다.
핵심 내용만 간결하게 요약하고,
필요하다면 할 일(Action Items)을 bullet point로 정리하세요.

[음성 텍스트]
{stt_text}
"""

        summary_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 회의 요약을 전문으로 하는 비서입니다."},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.3
        )

        summary_text = summary_response["choices"][0]["message"]["content"]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요약 실패: {str(e)}")

    # -------- 결과 반환 --------
    return {
        "stt_text": stt_text,
        "summary_text": summary_text
    }

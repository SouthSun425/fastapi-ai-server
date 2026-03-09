# -*- coding: utf-8 -*-

import os
import openai
from fastapi import FastAPI, HTTPException

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

app = FastAPI(
    title="AI FastAPI Server",
    description="Whisper STT + 요약 API",
    version="1.3.0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a"}
MAX_FILE_SIZE = 20 * 1024 * 1024


@app.get("/health")
def health():
    return {"status": "ok"}


def validate_audio_file(file_path: str):
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="허용되지 않은 파일 형식입니다.")

    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일 용량 초과입니다.")


def transcribe_audio(file_path: str) -> str:
    try:
        with open(file_path, "rb") as audio_file:
            stt_result = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file
            )
        return stt_result["text"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT 실패: {str(e)}")


def summarize_text(text: str) -> str:
    try:
        summary_prompt = f"""
아래는 음성 인식(STT) 결과입니다.
핵심 내용만 간결하게 요약하고,
필요하다면 할 일(Action Items)을 bullet point로 정리하세요.

[음성 텍스트]
{text}
"""

        summary_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 회의 요약을 전문으로 하는 비서입니다."},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.3
        )

        return summary_response["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요약 실패: {str(e)}")


@app.post("/stt-summary/{filename}")
def speech_to_text_and_summary(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)

    validate_audio_file(file_path)

    stt_text = transcribe_audio(file_path)
    summary_text = summarize_text(stt_text)

    return {
        "filename": filename,
        "file_path": file_path,
        "stt_text": stt_text,
        "summary_text": summary_text
    }
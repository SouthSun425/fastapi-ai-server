# -*- coding: utf-8 -*-

import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(
    title="AI FastAPI Server",
    description="Whisper STT API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a"}
MAX_FILE_SIZE = 25 * 1024 * 1024


@app.get("/")
def root():
    return {"message": "STT server is running"}


@app.post("/stt")
async def stt(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 없습니다.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 허용 형식: {sorted(ALLOWED_EXTENSIONS)}"
        )

    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일 크기가 너무 큽니다. 25MB 이하만 가능합니다.")

    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    try:
        with open(save_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        text = transcript.text if hasattr(transcript, "text") else str(transcript)

        return {
            "filename": file.filename,
            "saved_path": str(save_path),
            "text": text
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT 처리 중 오류가 발생했습니다: {str(e)}")


@app.post("/stt/from-uploads")
async def stt_from_uploads(filename: str):
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="uploads 폴더에 해당 파일이 없습니다.")

    ext = file_path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 허용 형식: {sorted(ALLOWED_EXTENSIONS)}"
        )

    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        text = transcript.text if hasattr(transcript, "text") else str(transcript)

        return {
            "filename": filename,
            "saved_path": str(file_path),
            "text": text
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT 처리 중 오류가 발생했습니다: {str(e)}")
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import re
import requests
import logging

# ===== FIX Redis (KHÔNG crash nữa) =====
try:
    from redis import asyncio as aioredis
except Exception:
    aioredis = None

# ===== CONFIG =====
app = FastAPI()
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:10000")
REDIS_URL = os.getenv("REDIS_URL", "")

# ===== LOG =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== STATIC =====
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_FOLDER), name="downloads")

# ===== REDIS =====
redis_client = None

@app.on_event("startup")
async def startup():
    global redis_client

    if aioredis is None:
        logger.warning("⚠️ Không có Redis → dùng memory")
        redis_client = None
        return

    try:
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis lỗi: {e}")
        redis_client = None


# ===== VALIDATE URL =====
def is_valid_url(url):
    return re.match(r'https?://', url)


# ===== DOWNLOAD API =====
@app.get("/download")
async def download(url: str):
    if not is_valid_url(url):
        raise HTTPException(status_code=400, detail="URL không hợp lệ")

    try:
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'format': 'best',
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # ===== FIX URL (QUAN TRỌNG) =====
        file_url = f"{BASE_URL}/downloads/{os.path.basename(filename)}"

        return {
            "status": "success",
            "title": info.get("title"),
            "download_url": file_url
        }

    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail="Download lỗi")


# ===== HEALTH CHECK =====
@app.get("/")
def home():
    return {"message": "Server OK"}
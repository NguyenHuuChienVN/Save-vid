"""
SaveVid Backend - Production Ready
Stack: FastAPI + yt-dlp + Redis
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import re
import time
import logging
from redis import asyncio as aioredis  # type: ignore[attr-defined]
import validators
import requests


# CONFIG — đổi theo môi trường của bạn

BASE_URL = os.getenv("BASE_URL", "https://kindle-landslide-revenue.ngrok-free.dev")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DOWNLOAD_FOLDER = os.getenv("DOWNLOAD_FOLDER", "downloads")
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "5"))
RATE_LIMIT_WINDOW   = int(os.getenv("RATE_LIMIT_WINDOW",   "60"))
MAX_DURATION_SEC    = int(os.getenv("MAX_DURATION_SEC",    "600"))  # 10 phút   

TRUSTED_PROXIES = {"127.0.0.1"}  # Thêm IP proxy/nginx của bạn vào đây

# APP SETUP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("savevid")

app = FastAPI(title="SaveVid API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    # ⚠️ Production: đổi "*" thành domain frontend của bạn, VD: ["https://savevid.com"]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_FOLDER), name="downloads")


# REDIS CLIENT

redis_client: aioredis.Redis = None

@app.on_event("startup")
async def startup():
    global redis_client
    try:
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis không kết nối được: {e}. Dùng in-memory fallback.")
        redis_client = None

@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.aclose()


# RATE LIMITER — Redis-backed với in-memory fallback

from collections import defaultdict
import threading

_mem_lock  = threading.Lock()
_mem_store: dict[str, list[float]] = defaultdict(list)

async def check_rate_limit(ip: str) -> bool:
    """
    Trả về True nếu request được phép, False nếu bị giới hạn.
    Ưu tiên Redis; nếu Redis down thì dùng in-memory.
    """
    if redis_client:
        return await _redis_rate_limit(ip)
    return _memory_rate_limit(ip)

async def _redis_rate_limit(ip: str) -> bool:
    now  = time.time()
    key  = f"rl:{ip}"
    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, now - RATE_LIMIT_WINDOW)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, RATE_LIMIT_WINDOW)
    _, _, count, _ = await pipe.execute()
    return count <= RATE_LIMIT_REQUESTS

def _memory_rate_limit(ip: str) -> bool:
    now = time.time()
    with _mem_lock:
        _mem_store[ip] = [t for t in _mem_store[ip] if now - t < RATE_LIMIT_WINDOW]
        if len(_mem_store[ip]) >= RATE_LIMIT_REQUESTS:
            return False
        _mem_store[ip].append(now)
        return True

def get_real_ip(request: Request) -> str:
    """Lấy IP thật, tránh spoof qua X-Forwarded-For."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = request.client.host if request.client else "unknown"
    if forwarded_for and client_ip in TRUSTED_PROXIES:
        return forwarded_for.split(",")[0].strip()
    return client_ip


# PLATFORM DETECTION

PLATFORM_PATTERNS = {
    "youtube":  re.compile(r"(youtube\.com/watch|youtu\.be/|youtube\.com/shorts/)"),
    "tiktok":   re.compile(r"tiktok\.com"),
    "instagram": re.compile(r"instagram\.com/(p|reel|reels)/"),
    "facebook": re.compile(r"(facebook\.com|fb\.watch)"),
    "twitter":  re.compile(r"(twitter\.com|x\.com)/\w+/status/"),
    "douyin":   re.compile(r"douyin\.com"),
}

def detect_platform(url: str) -> str:
    for name, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(url):
            return name
    return "unknown"

def is_tiktok_photo(url: str) -> bool:
    return "tiktok.com" in url and "/photo/" in url


# HELPERS

def remove_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"🗑️ Đã xóa file: {path}")
    except Exception as e:
        logger.warning(f"Không xóa được file {path}: {e}")

FORMAT_MAP = {
    "360":  "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "480":  "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "720":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "best": "bestvideo+bestaudio/best",
}

def build_ydl_opts(quality: str) -> dict:
    return {
        "outtmpl":            f"{DOWNLOAD_FOLDER}/%(id)s.%(ext)s",  # dùng id tránh tên file dài/lạ
        "format":             FORMAT_MAP.get(quality, FORMAT_MAP["1080"]),
        "merge_output_format": "mp4",
        "quiet":              True,
        "no_warnings":        True,
        "socket_timeout":     30,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer":    "https://www.tiktok.com/",
        },
        # Giới hạn thời lượng video
        "match_filter": yt_dlp.utils.match_filter_func(f"duration < {MAX_DURATION_SEC}"),
    }


# TIKTOK PHOTO HANDLER

def handle_tiktok_photo(url: str, background_tasks: BackgroundTasks):
    match = re.search(r'/photo/(\d+)', url)
    if not match:
        raise HTTPException(status_code=400, detail="Không tìm thấy post ID")

    post_id = match.group(1)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer":    "https://www.tiktok.com/",
    }

    endpoints = [
        f"https://api22-normal-c-useast2a.tiktokv.com/aweme/v1/feed/?aweme_id={post_id}",
        f"https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/feed/?aweme_id={post_id}",
    ]

    data = None
    for ep in endpoints:
        try:
            res = requests.get(ep, headers=headers, timeout=10)
            res.raise_for_status()
            data = res.json()
            if data.get("aweme_list"):
                break
        except Exception as e:
            logger.warning(f"TikTok photo endpoint failed: {ep} — {e}")

    if not data or not data.get("aweme_list"):
        raise HTTPException(status_code=404, detail="Không lấy được dữ liệu ảnh TikTok")

    images = data["aweme_list"][0].get("image_post_info", {}).get("images", [])
    if not images:
        raise HTTPException(status_code=404, detail="Bài đăng không có ảnh")

    files = []
    for i, img in enumerate(images):
        url_list = img.get("display_image", {}).get("url_list") or []
        if not url_list:
            continue
        try:
            r = requests.get(url_list[0], headers=headers, timeout=15)
            r.raise_for_status()
            path = os.path.join(DOWNLOAD_FOLDER, f"{post_id}_{i}.jpg")
            with open(path, "wb") as f:
                f.write(r.content)
            files.append(f"{BASE_URL}/downloads/{os.path.basename(path)}")
            background_tasks.add_task(remove_file, path)
        except Exception as e:
            logger.warning(f"Không tải được ảnh {i}: {e}")

    if not files:
        raise HTTPException(status_code=500, detail="Không tải được ảnh nào")

    return {"type": "images", "files": files}


# ROUTES

@app.get("/")
def home():
    return {"message": "SaveVid API v2.0 - Server OK"}


@app.get("/info")
async def get_info(url: str, request: Request):
    """
    Lấy thông tin video mà KHÔNG download.
    Frontend có thể dùng để hiển thị thumbnail, title, duration trước khi download.
    """
    ip = get_real_ip(request)
    if not await check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Quá nhiều request, thử lại sau 60 giây")

    url = url.strip()
    if not validators.url(url):
        raise HTTPException(status_code=400, detail="URL không hợp lệ")

    ydl_opts = {**build_ydl_opts("720"), "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return {
            "title":     info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration":  info.get("duration"),
            "platform":  detect_platform(url),
            "uploader":  info.get("uploader"),
        }
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=f"Không hỗ trợ URL này: {str(e)[:200]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:300])


@app.get("/download")
async def download(
    url: str,
    request: Request,
    background_tasks: BackgroundTasks,
    quality: str = "1080",
):
    # 1. Rate limit
    ip = get_real_ip(request)
    if not await check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Quá nhiều request, thử lại sau 60 giây")

    # 2. Validate URL
    url = url.strip()
    if not validators.url(url):
        raise HTTPException(status_code=400, detail="URL không hợp lệ")

    # 3. Validate quality
    if quality not in FORMAT_MAP:
        raise HTTPException(status_code=400, detail=f"quality phải là một trong: {list(FORMAT_MAP.keys())}")

    # 4. TikTok Photo
    if is_tiktok_photo(url):
        return handle_tiktok_photo(url, background_tasks)

    # 5. Video download (YouTube, TikTok video, Reels, Shorts, v.v.)
    platform = detect_platform(url)
    logger.info(f"[{ip}] Download {platform}: {url[:80]}")

    try:
        with yt_dlp.YoutubeDL(build_ydl_opts(quality)) as ydl:
            info     = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Đảm bảo đuôi .mp4
            base     = os.path.splitext(filename)[0]
            filename = base + ".mp4"

        if not os.path.exists(filename):
            raise HTTPException(status_code=404, detail="File không tồn tại sau khi download")

        file_url = f"{BASE_URL}downloads/{os.path.basename(filename)}"
        background_tasks.add_task(remove_file, filename)

        return {
            "type":      "video",
            "url":       file_url,
            "title":     info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration":  info.get("duration"),
            "platform":  platform,
        }

    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        if "duration" in err.lower():
            raise HTTPException(status_code=400, detail=f"Video quá dài (giới hạn {MAX_DURATION_SEC//60} phút)")
        raise HTTPException(status_code=400, detail=f"Không tải được: {err[:300]}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Lỗi server, thử lại sau")
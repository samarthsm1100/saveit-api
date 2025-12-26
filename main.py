from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse
import yt_dlp
import subprocess
import tempfile
import os
from typing import Optional

app = FastAPI()

# Global variable to store uploaded cookies path
COOKIES_PATH = None


@app.post("/upload-cookies")
async def upload_cookies(file: UploadFile = File(...)):
    """
    Upload your YouTube cookies.txt file.
    """
    global COOKIES_PATH
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Please upload a valid cookies.txt file")
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    content = await file.read()
    tmp.write(content)
    tmp.close()
    
    COOKIES_PATH = tmp.name
    return {"detail": "Cookies uploaded successfully"}


@app.get("/download/mp3")
def download_mp3(url: str = Query(...)):
    """
    Download YouTube video as MP3 using uploaded cookies (if any)
    """
    try:
        ydl_opts = {
            "format": "bestaudio",
            "quiet": True,
            "no_warnings": True,
            "geo_bypass": True
        }

        if COOKIES_PATH:
            ydl_opts["cookiefile"] = COOKIES_PATH

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info["url"]

        ffmpeg = subprocess.Popen(
            [
                "ffmpeg",
                "-i", stream_url,
                "-vn",
                "-acodec", "libmp3lame",
                "-ab", "128k",
                "-f", "mp3",
                "-"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        return StreamingResponse(
            ffmpeg.stdout,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": 'attachment; filename="audio.mp3"'
            }
        )

    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "Sign in to confirm" in msg or "LOGIN_REQUIRED" in msg:
            raise HTTPException(
                status_code=400,
                detail="Bot detection / login required. Upload cookies to download this video."
            )
        raise HTTPException(status_code=500, detail=msg)


@app.get("/download/mp4")
def download_mp4(url: str = Query(...)):
    """
    Download YouTube video as MP4 using uploaded cookies (if any)
    """
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tmp.close()

        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": tmp.name,
            "quiet": True,
            "no_warnings": True,
            "geo_bypass": True
        }

        if COOKIES_PATH:
            ydl_opts["cookiefile"] = COOKIES_PATH

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        def file_stream():
            with open(tmp.name, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    yield chunk
            os.remove(tmp.name)

        return StreamingResponse(
            file_stream(),
            media_type="video/mp4",
            headers={
                "Content-Disposition": 'attachment; filename="video.mp4"'
            }
        )

    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "Sign in to confirm" in msg or "LOGIN_REQUIRED" in msg:
            raise HTTPException(
                status_code=400,
                detail="Bot detection / login required. Upload cookies to download this video."
            )
        raise HTTPException(status_code=500, detail=msg)

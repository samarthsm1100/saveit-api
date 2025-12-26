from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
import yt_dlp
import subprocess
import tempfile
import os

app = FastAPI()

@app.get("/")
def health():
    return {"status": "ok"}

# ================= MP3 =================
@app.get("/download/mp3")
def download_mp3(url: str = Query(...)):
    try:
        # Attempt without cookies first
        ydl_opts = {
            "format": "bestaudio",
            "quiet": True,
            "no_warnings": True,
            "geo_bypass": True
        }

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
        # Detect bot‑block pattern
        msg = str(e)
        if "Sign in to confirm" in msg or "LOGIN_REQUIRED" in msg:
            raise HTTPException(
                status_code=400,
                detail="YouTube bot detection: try using a cookies upload or use a different video."
            )
        raise HTTPException(status_code=500, detail=msg)

# ================= MP4 =================
@app.get("/download/mp4")
def download_mp4(url: str = Query(...)):
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
                detail="YouTube bot detection: try using a cookies upload or use a different video."
            )
        raise HTTPException(status_code=500, detail=msg)
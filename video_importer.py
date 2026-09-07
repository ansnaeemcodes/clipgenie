import os
import json
import logging
import shutil
import re
import yt_dlp
import config
import groq_transcription
import concept_detector

logger = logging.getLogger(__name__)

LECTURES_INDEX_FILE = os.path.join(config.CACHE_DIR, "lectures_index.json")

def get_lectures_index():
    """Returns list of registered lectures."""
    default_lectures = [
        {
            "id": "tedtalk",
            "title": "The Coming Wave: AI as a Digital Species (Mustafa Suleyman)",
            "filename": "tedtalk.mp4",
            "video_url": "/static/tedtalk.mp4",
            "duration_str": "6:50",
            "source": "demo_preset",
            "concepts_count": 5
        }
    ]
    if os.path.exists(LECTURES_INDEX_FILE):
        try:
            with open(LECTURES_INDEX_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and isinstance(data, list):
                    return data
        except Exception as e:
            logger.warning(f"Error reading lectures index: {e}")
            
    # Save default if not existing
    with open(LECTURES_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(default_lectures, f, indent=2)
    return default_lectures

def register_lecture(lecture_meta):
    """Registers a new lecture in the index."""
    lectures = get_lectures_index()
    # Remove existing if same ID
    lectures = [l for l in lectures if l.get("id") != lecture_meta.get("id")]
    lectures.insert(0, lecture_meta)
    with open(LECTURES_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(lectures, f, indent=2)
    logger.info(f"Registered lecture: {lecture_meta.get('title')}")

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-.]', '_', name)

def download_video_from_url(url, progress_callback=None):
    """
    Downloads video from YouTube, Facebook, Vimeo, or web links using yt-dlp.
    Returns dictionary with file paths, video ID, and title.
    """
    logger.info(f"Starting video download from URL: {url}")
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    os.makedirs(config.STATIC_DIR, exist_ok=True)

    # yt-dlp configuration for fast, clean MP4 extraction
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(config.UPLOADS_DIR, '%(id)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': True,
        'noplaylist': True,
        'retries': 3
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = sanitize_filename(info.get('id', 'imported_video'))
        title = info.get('title', 'Imported Lecture Video')
        duration = info.get('duration', 0)
        
        # Expected downloaded path
        downloaded_path = os.path.join(config.UPLOADS_DIR, f"{video_id}.mp4")
        if not os.path.exists(downloaded_path):
            # Check if file has another extension or was saved with title
            for f in os.listdir(config.UPLOADS_DIR):
                if f.startswith(video_id) and f.endswith('.mp4'):
                    downloaded_path = os.path.join(config.UPLOADS_DIR, f)
                    break

    if not os.path.exists(downloaded_path):
        raise FileNotFoundError(f"Downloaded video file not found for ID: {video_id}")

    # Copy to static for browser playback
    static_video_path = os.path.join(config.STATIC_DIR, f"{video_id}.mp4")
    shutil.copy2(downloaded_path, static_video_path)
    logger.info(f"Copied video to static: {static_video_path}")

    # Format duration
    mins = int(duration // 60)
    secs = int(duration % 60)
    duration_str = f"{mins}:{secs:02d}"

    return {
        "id": video_id,
        "title": title,
        "upload_path": downloaded_path,
        "static_path": static_video_path,
        "static_url": f"/static/{video_id}.mp4",
        "duration_str": duration_str,
        "source": "url_import"
    }

def process_and_index_lecture(video_path, custom_title=None, video_id=None, source="local_upload"):
    """
    End-to-End Processing:
    1. Transcribe speech using Groq whisper-large-v3-turbo (or fallback)
    2. Critique transcript & extract concepts using Groq LLM
    3. Register lecture in index
    """
    if video_id is None:
        video_id = sanitize_filename(os.path.splitext(os.path.basename(video_path))[0])
        
    if custom_title is None:
        custom_title = video_id.replace('_', ' ').title()

    logger.info(f"Processing lecture: {custom_title} ({video_id})")

    # 1. Transcribe
    segments = groq_transcription.get_or_create_transcript(video_path, force_live=True)

    # 2. Extract concepts with Groq LLM
    concepts = concept_detector.get_lecture_concepts(video_path, segments, force_auto=True)

    # 3. Copy to static if not already there
    static_video_path = os.path.join(config.STATIC_DIR, f"{video_id}.mp4")
    if not os.path.exists(static_video_path):
        shutil.copy2(video_path, static_video_path)

    # Determine duration
    duration_str = "0:00"
    if segments:
        total_sec = segments[-1]['end']
        duration_str = f"{int(total_sec // 60)}:{int(total_sec % 60):02d}"

    lecture_meta = {
        "id": video_id,
        "title": custom_title,
        "filename": f"{video_id}.mp4",
        "video_url": f"/static/{video_id}.mp4",
        "duration_str": duration_str,
        "source": source,
        "concepts_count": len(concepts)
    }

    register_lecture(lecture_meta)
    return {
        "success": True,
        "lecture": lecture_meta,
        "concepts": concepts
    }

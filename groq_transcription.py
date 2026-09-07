import os
import json
import logging
import re
from moviepy import VideoFileClip
import config

logger = logging.getLogger(__name__)

def extract_audio_from_video(video_path, output_audio_path=None):
    """Extracts MP3 audio from a video file using MoviePy."""
    if output_audio_path is None:
        base = os.path.splitext(video_path)[0]
        output_audio_path = f"{base}_audio.mp3"
    
    logger.info(f"Extracting audio from {video_path} to {output_audio_path}")
    with VideoFileClip(video_path) as clip:
        if clip.audio is None:
            raise ValueError("The uploaded video contains no audio track. Please upload a lecture or video with spoken audio.")
        # Use 32k mono to keep long 60-90 min lectures safely under Groq Whisper's 25MB limit
        clip.audio.write_audiofile(output_audio_path, bitrate="32k", ffmpeg_params=["-ac", "1"], logger=None)
    return output_audio_path

def parse_txt_transcript(txt_path):
    """Parses standard ClipGenie format: '0.00s 2.44s  transcript text' into structured segments."""
    segments = []
    pattern = re.compile(r"^\s*([0-9.]+)s\s+([0-9.]+)s\s+(.*)$")
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = pattern.match(line)
            if m:
                start = float(m.group(1))
                end = float(m.group(2))
                text = m.group(3).strip()
                segments.append({"start": start, "end": end, "text": text})
    return segments

def transcribe_with_groq(audio_path):
    """Transcribes an audio file using Groq's whisper-large-v3-turbo API."""
    import groq
    client = groq.Groq(api_key=config.GROQ_API_KEY)
    
    logger.info(f"Calling Groq Whisper API ({config.GROQ_TRANSCRIPTION_MODEL}) for {audio_path}...")
    with open(audio_path, "rb") as file_obj:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), file_obj.read()),
            model=config.GROQ_TRANSCRIPTION_MODEL,
            response_format="verbose_json",
        )
    
    segments = []
    if hasattr(transcription, "segments") and transcription.segments:
        for seg in transcription.segments:
            segments.append({
                "start": round(seg.get("start", 0.0), 2),
                "end": round(seg.get("end", 0.0), 2),
                "text": seg.get("text", "").strip()
            })
    else:
        # Fallback if raw text returned
        text = getattr(transcription, "text", str(transcription))
        segments.append({"start": 0.0, "end": 30.0, "text": text.strip()})
        
    logger.info(f"Groq transcription completed: {len(segments)} segments extracted.")
    return segments

def transcribe_with_local_whisper(audio_path):
    """Fallback to local whisper model."""
    logger.info("Attempting local Whisper fallback...")
    import whisper
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, fp16=False)
    segments = []
    for s in result.get("segments", []):
        segments.append({
            "start": round(s["start"], 2),
            "end": round(s["end"], 2),
            "text": s["text"].strip()
        })
    return segments

def get_or_create_transcript(video_path, force_live=False):
    """
    Demo-Safe & Robust Transcription Pipeline:
    1. Check local cache (demo_cache/ or uploads/ *_transcription.txt)
    2. If force_live or not cached:
       a. Extract audio
       b. Try Groq API (whisper-large-v3-turbo)
       c. Fallback to local whisper if Groq fails
       d. Cache result to demo_cache/<filename>_cache.json
    """
    filename = os.path.basename(video_path)
    base_name = os.path.splitext(filename)[0]
    cache_file = os.path.join(config.CACHE_DIR, f"{base_name}_cache.json")
    
    # 1. Check if cached JSON exists
    if not force_live and os.path.exists(cache_file):
        logger.info(f"Using cached transcript from {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("segments", [])
            
    # 2. Check if existing .txt transcript exists in uploads
    txt_file = os.path.join(config.UPLOADS_DIR, f"{base_name}_transcription.txt")
    if not force_live and os.path.exists(txt_file):
        logger.info(f"Loading pre-existing TXT transcript from {txt_file}")
        segments = parse_txt_transcript(txt_file)
        if segments:
            # Save to demo cache for faster structured access
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"video_file": filename, "segments": segments}, f, indent=2)
            return segments

    # 3. Live extraction & transcription
    audio_path = os.path.join(config.UPLOADS_DIR, f"{base_name}_audio.mp3")
    if not os.path.exists(audio_path):
        audio_path = extract_audio_from_video(video_path, audio_path)
        
    try:
        segments = transcribe_with_groq(audio_path)
    except Exception as e:
        logger.warning(f"Groq API transcription failed ({e}). Falling back to local Whisper...")
        try:
            segments = transcribe_with_local_whisper(audio_path)
        except Exception as local_err:
            logger.error(f"Local whisper also failed ({local_err}).")
            raise RuntimeError(f"Transcription failed both online and locally: {e} / {local_err}")
            
    # Cache result
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({"video_file": filename, "segments": segments}, f, indent=2)
        
    return segments

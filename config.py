import os

# Suppress verbose TensorFlow / oneDNN logs
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
SECRET_KEY = os.environ.get('SECRET_KEY', 'clipgenie-hackathon-2026-secret-key')

# LLM Models on Groq
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b')
GROQ_BACKUP_MODEL = os.environ.get('GROQ_BACKUP_MODEL', 'qwen/qwen3.8-27b')
GROQ_TRANSCRIPTION_MODEL = os.environ.get('GROQ_TRANSCRIPTION_MODEL', 'whisper-large-v3-turbo')

# Demo Safety Mode: If True, uses cached/pre-computed data for lightning-fast, zero-fail demo presentation
DEMO_SAFE_MODE = os.environ.get('DEMO_SAFE_MODE', 'true').lower() in ('true', '1', 'yes')

# Base Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, 'demo_cache')
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')
SUMMARIZED_DIR = os.path.join(BASE_DIR, 'summarized_uploads')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(SUMMARIZED_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

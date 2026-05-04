import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("MODEL_NAME", "DeepPavlov/rubert-base-cased")
os.environ.setdefault("MODEL_CACHE_DIR", "/opt/hf-cache")
os.environ.setdefault("MAX_TEXT_LENGTH", "4000")
os.environ.setdefault("BATCH_SIZE", "8")

import os
import shutil

DEFAULT_VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.mov', '.m4v', '.avi', '.wmv', '.flv', '.mpg', '.mpeg'}

DEFAULT_W = min(4, os.cpu_count() or 1)

DEFAULT_W_SSD = min(32, os.cpu_count() or 1)

MAX_W = 128

FFPROBE_PATH = shutil.which('ffprobe') or ""
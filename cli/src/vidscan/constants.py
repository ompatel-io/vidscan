import os
import shutil

# Default extensions if not provided --extensions flag
DEFAULT_VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.mov', '.m4v', '.avi', '.wmv', '.flv', '.mpg', '.mpeg'}

# Default if not provided --workers flag
DEFAULT_W = min(4, os.cpu_count() or 1)

# Default for SSDs (if provided --workers ssd)
DEFAULT_W_SSD = min(32, os.cpu_count() or 1)

MAX_W = 128

FFPROBE_PATH = shutil.which('ffprobe') or ""
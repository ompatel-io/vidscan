import os
import re
from typing import Callable

from ..models import FolderData, VideoFile

def natural_sort_key(s: str) -> list[str | int]:
    parts = re.split(r"(\d+)", s)
    return [int(p) if p.isdigit() else p.lower() for p in parts]

def sort_results(
        folders: list[FolderData],
        sort_folders_by: str,
        folder_reverse: bool,
        sort_videos_by: str,
        video_reverse: bool
):
    
    folder_sort_keys: dict[str, Callable[[FolderData], str | float | int | list[str | int]]] = {
        'name':     lambda f: natural_sort_key(os.path.basename(f.path)),
        'duration': lambda f: f.total_seconds,
        'videos':   lambda f: f.video_count,
        'size':     lambda f: f.total_size,
        'date':     lambda f: f.last_modified
    }

    video_sort_keys: dict[str, Callable[[VideoFile], str | float | int | list[str | int]]] = {
        'name':     lambda v: natural_sort_key(v.name),
        'duration': lambda v: v.duration,
        'size':     lambda v: v.size,
        'date':     lambda v: v.mtime
    }

    folders.sort(key=folder_sort_keys[sort_folders_by], reverse=folder_reverse)

    for folder in folders:
        folder.videos.sort(key=video_sort_keys[sort_videos_by], reverse=video_reverse)
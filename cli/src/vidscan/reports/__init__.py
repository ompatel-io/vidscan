import os
from typing import Callable

from ..models import FolderData, VideoFile

def sort_results(
        folders: list[FolderData],
        sort_folders_by: str,
        folder_reverse: bool,
        sort_videos_by: str,
        video_reverse: bool
):
    
    folder_sort_keys: dict[str, Callable[[FolderData], str | float | int]] = {
        'name':     lambda f: os.path.basename(f.path).lower(),
        'duration': lambda f: f.total_seconds,
        'videos':   lambda f: f.video_count,
        'size':     lambda f: f.total_size,
        'date':     lambda f: f.last_modified
    }

    video_sort_keys: dict[str, Callable[[VideoFile], str | float | int | list[str | int]]] = {
        'name':     lambda v: v.name,
        'duration': lambda v: v.duration,
        'size':     lambda v: v.size,
        'date':     lambda v: v.mtime
    }

    folders.sort(key=folder_sort_keys[sort_folders_by], reverse=folder_reverse)

    for folder in folders:
        folder.videos.sort(key=video_sort_keys[sort_videos_by], reverse=video_reverse)
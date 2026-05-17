import os
from typing import Callable

from ..models import FolderData

def get_sorted_data(folders: list[FolderData], sort_by: str, reverse: bool) -> list[FolderData]:
    sort_keys: dict[str, Callable[[FolderData], str | float | int]] = {
        'name':     lambda f: os.path.basename(f.path).lower(),
        'duration': lambda f: f.total_seconds,
        'videos':   lambda f: f.video_count,
        'size':     lambda f: f.total_size,
        'date':     lambda f: f.last_modified
    }

    key_func = sort_keys.get(sort_by, lambda f: f.path)
    
    return sorted(folders, key=key_func, reverse=reverse)
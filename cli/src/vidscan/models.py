from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class VideoFile:
    name: str
    duration: float
    mtime: float
    size: int

@dataclass(frozen=True, slots=True)
class FailedVideo:
    path: str
    size: int
    error: str = ""

@dataclass(frozen=True, slots=True)
class DiscoveredFile:
    path: str
    dirpath: str
    name: str
    mtime: float
    size: int
    error: str = ""

@dataclass(slots=True)
class FolderData:
    path: str
    videos: list[VideoFile] = field(default_factory=list[VideoFile])
    total_seconds: float = 0
    total_size: int = 0
    video_count: int = 0
    last_modified: float = 0
    
@dataclass(frozen=True, slots=True)
class ScanResult:
    folders: list[FolderData] = field(default_factory=list[FolderData])
    total_videos: int = 0
    success_count: int = 0
    failed_videos_data: list[FailedVideo] = field(default_factory=list[FailedVideo])
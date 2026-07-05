import json
import datetime
from typing import TypedDict

from ..models import ScanResult
from ..utils import format_bytes, format_seconds_hms

class VideoJSON(TypedDict):
    name: str
    duration: float
    mtime: float
    size: int
    size_formatted: str
    duration_formatted: str

class FolderJSON(TypedDict):
    folder_path: str
    video_count: int
    total_seconds: float
    total_duration_formatted: str
    total_videos_size_bytes: int
    total_videos_size_formatted: str
    last_modified_timestamp: float
    last_modified_formatted: str
    videos: list[VideoJSON]

class FailedVideoJSON(TypedDict):
    path: str
    size: int
    error: str
    size_formatted: str

class ReportSummaryJSON(TypedDict):
    total_folders: int
    total_videos_discovered: int
    successful_videos: int
    failed_videos_count: int
    total_duration_seconds: float
    total_duration_formatted: str
    total_successful_videos_size_bytes: int
    total_successful_videos_size_formatted: str
    total_failed_videos_size_bytes: int
    total_failed_videos_size_formatted: str
    total_videos_size_bytes: int
    total_videos_size_formatted: str
    generated_at: str

class ReportJSON(TypedDict):
    summary: ReportSummaryJSON
    details: list[FolderJSON]
    failed_videos: list[FailedVideoJSON]

def write_json_report(scan_result:ScanResult, output_path: str, timestamp: datetime.datetime):
    total_vid_size_successful = 0
    total_seconds = 0.0
    details_list: list[FolderJSON] = []
    
    for folder in scan_result.folders:
        videos_formatted: list[VideoJSON] = []
        for video_data in sorted(folder.videos, key=lambda x: x.name):
            videos_formatted.append(VideoJSON(
                name=video_data.name,
                duration=video_data.duration,
                mtime=video_data.mtime,
                size=video_data.size,
                size_formatted=format_bytes(video_data.size),
                duration_formatted=format_seconds_hms(video_data.duration),
            ))
        
        total_seconds += folder.total_seconds
        total_vid_size_successful += folder.total_size

        details_list.append(FolderJSON(
            folder_path=folder.path,
            video_count=folder.video_count,
            total_seconds=folder.total_seconds,
            total_duration_formatted=format_seconds_hms(folder.total_seconds),
            total_videos_size_bytes=folder.total_size,
            total_videos_size_formatted=format_bytes(folder.total_size),
            last_modified_timestamp=folder.last_modified,
            last_modified_formatted=datetime.datetime.fromtimestamp(folder.last_modified).isoformat(),
            videos=videos_formatted,
        ))
    
    total_vid_size_failed = 0
    failed_videos_formatted: list[FailedVideoJSON] = []
    
    for failed_video in sorted(scan_result.failed_videos_data, key=lambda x: x.path):
        failed_videos_formatted.append(FailedVideoJSON(
            path=failed_video.path,
            size=failed_video.size,
            error=failed_video.error,
            size_formatted=format_bytes(failed_video.size),
        ))
        total_vid_size_failed += failed_video.size

    report_structure = ReportJSON(
        summary=ReportSummaryJSON(
            total_folders=len(scan_result.folders),
            total_videos_discovered=scan_result.total_videos,
            successful_videos=scan_result.success_count,
            failed_videos_count=len(scan_result.failed_videos_data),
            total_duration_seconds=round(total_seconds, 2),
            total_duration_formatted=format_seconds_hms(total_seconds),
            total_successful_videos_size_bytes=total_vid_size_successful,
            total_successful_videos_size_formatted=format_bytes(total_vid_size_successful),
            total_failed_videos_size_bytes=total_vid_size_failed,
            total_failed_videos_size_formatted=format_bytes(total_vid_size_failed),
            total_videos_size_bytes=total_vid_size_successful + total_vid_size_failed,
            total_videos_size_formatted=format_bytes(total_vid_size_successful + total_vid_size_failed),
            generated_at=timestamp.isoformat(),
        ),
        details=details_list,
        failed_videos=failed_videos_formatted,
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_structure, f, indent=4)
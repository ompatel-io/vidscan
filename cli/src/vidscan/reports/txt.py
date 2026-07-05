import os

from ..models import FailedVideo, ScanResult
from ..utils import format_bytes, format_seconds_hms

def get_txt_report_summary_lines(scan_result: ScanResult, include_size: bool) -> list[str]:
    divide_line_length = 60 if include_size else 45

    lines = [
        "Video Duration (Summary)", 
        "=" * divide_line_length,
        ""
    ]
    
    grand_total_seconds = 0.0
    grand_total_vid_size = 0
    grand_total_videos = 0

    for folder in scan_result.folders:
        folder_name = os.path.basename(folder.path) or os.path.basename(os.path.normpath(folder.path))

        lines.append(f"Folder: {folder_name}")

        size_str = f" | Size: {format_bytes(folder.total_size)}" if include_size else ""
        lines.append(f"  -> Videos: {folder.video_count:>3} | Duration: {format_seconds_hms(folder.total_seconds)}{size_str}")
        lines.append("-" * divide_line_length)
        
        grand_total_seconds += folder.total_seconds
        grand_total_vid_size += folder.total_size
        grand_total_videos += folder.video_count
    
    totals_lines = [
        "\nTOTALS",
        f"  -> Total Folders: {len(scan_result.folders)}",
        f"  -> Total Videos: {grand_total_videos}",
        f"  -> Total Duration: {format_seconds_hms(grand_total_seconds)}"
    ]
    
    if include_size:
        totals_lines.append(f"  -> Total Videos Size: {format_bytes(grand_total_vid_size)}")
        
    totals_lines.append("=" * divide_line_length)
    lines.extend(totals_lines)

    if scan_result.failed_videos_data:
        lines.extend([
            "",
            "---",
            f"[!] NOTE: Scanning failed for {len(scan_result.failed_videos_data)} videos and are excluded from this report."
        ])

    return lines

def get_txt_report_detailed_lines(scan_result: ScanResult, include_size: bool) -> list[str]:
    divide_line_length = 75 if include_size else 60

    lines = [
        "Video Duration (Detailed)", 
        "=" * divide_line_length,
        ""
    ]
    
    grand_total_seconds = 0.0
    grand_total_vid_size = 0
    grand_total_videos = 0

    for folder in scan_result.folders:
        folder_name = os.path.basename(folder.path) or os.path.basename(os.path.normpath(folder.path))

        lines.append(f"Folder: {folder_name}")
        
        sub_total_size_str = f" | Subtotal Size: {format_bytes(folder.total_size)}" if include_size else ""
        lines.append(f"  [ Videos: {folder.video_count:>3} | Subtotal Duration: {format_seconds_hms(folder.total_seconds)}{sub_total_size_str} ]")
        
        sorted_videos = sorted(folder.videos, key=lambda x: x.name)
        for vid_info in sorted_videos:
            size_str = f" | {format_bytes(vid_info.size)}" if include_size else ""
            lines.append(f"    - {vid_info.name} ({format_seconds_hms(vid_info.duration)}{size_str})")
            
        lines.append("-" * divide_line_length)
        
        grand_total_seconds += folder.total_seconds
        grand_total_vid_size += folder.total_size
        grand_total_videos += folder.video_count
    
    totals_lines = [
        "\nGRAND TOTAL",
        f"  -> Total Folders: {len(scan_result.folders)}",
        f"  -> Total Videos: {grand_total_videos}",
        f"  -> Total Duration: {format_seconds_hms(grand_total_seconds)}"
    ]
    
    if include_size:
        totals_lines.append(f"  -> Total Videos Size: {format_bytes(grand_total_vid_size)}")
    
    totals_lines.append("=" * divide_line_length)
    lines.extend(totals_lines)

    if scan_result.failed_videos_data:
        lines.extend([
            "",
            "---",
            f"[!] Note: Scanning failed for {len(scan_result.failed_videos_data)} videos and are excluded from this report."
        ])

    return lines

def get_failed_videos_report_lines(failed_videos_data: list[FailedVideo]) -> list[str]:
    divide_line_length = 60

    lines = [
        "FAILED VIDEO FILES",
        "=" * divide_line_length,
        "These videos could not be read by ffprobe.",
        ""
    ]

    total_failed_vid_size = 0

    for failed_video in sorted(failed_videos_data, key=lambda x: x.path):
        lines.append(f"- {failed_video.path}")
        lines.append(f"  Reason: {failed_video.error}")
        lines.append(f"  Size: {format_bytes(failed_video.size)}\n")

        total_failed_vid_size += failed_video.size

    totals_lines = [
        "\nTOTALS",
        f"  -> Total Failed Videos: {len(failed_videos_data)}",
        f"  -> Total Size: {format_bytes(total_failed_vid_size)}"
    ]

    totals_lines.append("=" * divide_line_length)
    lines.extend(totals_lines)
    
    return lines

def write_txt_report(lines: list[str], output_path: str, timestamp_str: str) -> str:
    lines.append(timestamp_str)
    report_content = "\n".join(lines)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    return report_content
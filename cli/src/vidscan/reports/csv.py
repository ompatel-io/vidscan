import os
import csv
import datetime

from ..models import ScanResult
from ..utils import format_bytes, format_seconds_hms

def write_csv_report(scan_result: ScanResult, output_path: str, root_folder: str, timestamp: datetime.datetime):
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Folder Path', 'Relative Path', 'File Name', 'Duration (Seconds)', 'Duration (Formatted)', 'Size (Bytes)', 'Size (Formatted)'])
        
        total_vid_size_successful = 0
        for folder in scan_result.folders:
            try:
                relative_path = os.path.relpath(folder.path, root_folder)
            except ValueError:
                relative_path = folder.path
                
            sorted_videos = sorted(folder.videos, key=lambda x: x.name)
            
            for vid_info in sorted_videos:
                writer.writerow([
                    folder.path,
                    relative_path,
                    vid_info.name,
                    f"{vid_info.duration:.2f}",
                    format_seconds_hms(vid_info.duration),
                    vid_info.size,
                    format_bytes(vid_info.size)
                ])

            total_vid_size_successful += folder.total_size

        total_vid_size_failed = 0
        if scan_result.failed_videos_data:
            for failed_video in sorted(scan_result.failed_videos_data, key=lambda x: x.path):
                folder_path = os.path.dirname(failed_video.path)
                try:
                    relative_path = os.path.relpath(folder_path, root_folder)
                except ValueError:
                    relative_path = folder_path
                file_name = os.path.basename(failed_video.path)
                
                writer.writerow([
                    folder_path,
                    relative_path,
                    file_name,
                    'FAILED',
                    failed_video.error,
                    failed_video.size,
                    format_bytes(failed_video.size)
                ])

                total_vid_size_failed += failed_video.size

        writer.writerow([])
        writer.writerow(['--- SCAN SUMMARY ---', '', '', '', '', '', ''])
        writer.writerow(['Total Videos Discovered', scan_result.total_videos, '', '', '', '', ''])
        writer.writerow(['Successful', scan_result.success_count, '', '', '', '', ''])
        writer.writerow(['Failed', len(scan_result.failed_videos_data), '', '', '', '', ''])
        writer.writerow(['Total Size (Successful Videos)', total_vid_size_successful, format_bytes(total_vid_size_successful), '', '', '', ''])
        writer.writerow(['Total Size (Failed Videos)', total_vid_size_failed, format_bytes(total_vid_size_failed), '', '', '', ''])
        writer.writerow(['Total Size (All Videos)', total_vid_size_successful + total_vid_size_failed, format_bytes(total_vid_size_successful + total_vid_size_failed), '', '', '', ''])
        writer.writerow(['Report Generated At', timestamp.strftime('%Y-%m-%d %H:%M:%S'), '', '', '', '', ''])
import os
import subprocess
import concurrent.futures
import time
from collections.abc import Iterator

from .constants import FFPROBE_PATH
from .models import VideoFile, FailedVideo, DiscoveredFile, FolderData, ScanResult
from .ui import UI

def stream_video_files(root_folder: str, video_extensions: set[str], excluded_folders: set[str]) -> Iterator[DiscoveredFile]:
    stack = [root_folder]
    while stack:
        current_dir = stack.pop()

        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in excluded_folders:
                            stack.append(entry.path)
                    
                    elif entry.is_file(follow_symlinks=False):
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in video_extensions:
                            try:
                                stat = entry.stat()
                                yield DiscoveredFile(
                                    path=entry.path, 
                                    dirpath=current_dir, 
                                    name=entry.name, 
                                    mtime=stat.st_mtime, 
                                    size=stat.st_size,
                                )
                                
                            except OSError as e:
                                yield DiscoveredFile(
                                    path=entry.path, 
                                    dirpath=current_dir, 
                                    name=entry.name, 
                                    mtime=0.0, 
                                    size=0, 
                                    error=f"OS Error: {str(e)}"
                                )
        except OSError:
            continue

def get_video_duration(video_path: str, ffprobe_timeout_sec: float) -> tuple[float, str]:
    try:
        command = [ # type: ignore
            FFPROBE_PATH, 
            "-v", "error", 
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", 
            video_path
        ]
        
        run_kwargs = { # type: ignore
            "capture_output": True,
            "text": True,
            "check": True,
            "timeout": ffprobe_timeout_sec
        }

        if os.name == 'nt':
            run_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(command, **run_kwargs) # type: ignore
        
        return float(result.stdout), "" # type: ignore
        
    except subprocess.TimeoutExpired:
        return 0.0, f"Process timed out after {ffprobe_timeout_sec} seconds"
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Corrupted or unreadable file"
        return 0.0, error_msg
    except Exception as e:
        return 0.0, str(e)

def scan_videos_concurrently(
    root_folder: str,
    video_extensions: set[str],
    excluded_folders: set[str],
    num_workers: int,
    ffprobe_timeout_sec: float,
    fast_start_mode: bool,
    ui: UI
) -> ScanResult:

    folder_data: dict[str, FolderData] = {}
    total_videos = 0

    start_time = time.time()

    if not fast_start_mode:
        print(ui.warning("Scanning directory structure..."))
        total_videos = sum(1 for _ in stream_video_files(root_folder, video_extensions, excluded_folders))

        if total_videos == 0:
            return ScanResult()
        
        print(f"Found {ui.info(total_videos)} video files.", end=" ")

    print(f"Processing with {num_workers} workers...")
    
    videos_processed = 0
    failed_videos_data: list[FailedVideo] = []

    last_print_time = 0.0
    progress_update_interval = 0.1

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_workers)
    future_to_video: dict[concurrent.futures.Future[tuple[float, str]], DiscoveredFile] = {}

    try:
        for file_metadata in stream_video_files(root_folder, video_extensions, excluded_folders):
            
            if file_metadata.error:
                failed_videos_data.append(
                    FailedVideo(
                        path=file_metadata.path, 
                        error=file_metadata.error,
                        size=file_metadata.size
                    )
                )
                continue
                
            future = executor.submit(get_video_duration, file_metadata.path, ffprobe_timeout_sec)
            future_to_video[future] = file_metadata

        for future in concurrent.futures.as_completed(future_to_video):
            file_metadata = future_to_video[future]
            duration, error_msg = future.result()
            
            videos_processed += 1

            if duration > 0:
                if file_metadata.dirpath not in folder_data:
                    folder_data[file_metadata.dirpath] = FolderData(path=file_metadata.dirpath)
                
                folder_data[file_metadata.dirpath].videos.append(
                    VideoFile(
                        name=file_metadata.name, 
                        duration=duration, 
                        mtime=file_metadata.mtime, 
                        size=file_metadata.size
                    )
                )
            else:
                failed_videos_data.append(
                    FailedVideo(
                        path=file_metadata.path, 
                        error=error_msg,
                        size=file_metadata.size
                    )
                )

            if ui.is_terminal:
                current_time = time.time()
                if current_time - last_print_time >= progress_update_interval or videos_processed == total_videos:
                    if fast_start_mode:
                        print(f"\r[{next(ui.spinner)}] Videos processed: {ui.info(videos_processed)}", end="", flush=True)
                    else:
                        progress = videos_processed / total_videos
                        bar_length = 40
                        filled = int(bar_length * progress)
                        
                        bar = (ui.bar_fill * filled) + (ui.bar_empty * (bar_length - filled))
                        percent = int(progress * 100)

                        print(f"\rProgress: [{bar}] {percent}% ({videos_processed}/{total_videos})", end="", flush=True)

                    last_print_time = current_time

    except KeyboardInterrupt:
        print(ui.warning("\n\n[!] Exiting gracefully"))
        print(ui.info("Cancelling and saving partial data..."))

    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    print(f"\nProcessing complete in {time.time() - start_time:.2f} seconds.")

    success_count = 0
    for folder_stats in folder_data.values():
        total_seconds, total_size, m_time = 0.0, 0, 0.0
        
        for video in folder_stats.videos:
            total_seconds += video.duration
            total_size += video.size
            if video.mtime > m_time:
                m_time = video.mtime

        folder_stats.total_seconds = total_seconds
        folder_stats.total_size = total_size
        folder_stats.last_modified = m_time
        folder_stats.video_count = len(folder_stats.videos)
        success_count += folder_stats.video_count

    if fast_start_mode:
        total_videos = videos_processed

    return ScanResult(
        folders=list(folder_data.values()),
        total_videos=total_videos,
        success_count=success_count,
        failed_videos_data=failed_videos_data
    )
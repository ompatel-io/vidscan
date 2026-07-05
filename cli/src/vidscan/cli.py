import os
import subprocess
import argparse
import sys
import datetime

from .constants import DEFAULT_VIDEO_EXTENSIONS, DEFAULT_W, DEFAULT_W_SSD, MAX_W, FFPROBE_PATH
from .utils import format_windows_max_path
from .ui import get_ui
from .scanner import scan_videos_concurrently
from .reports import sort_results
from .reports.txt import write_txt_and_failed_videos_report
from .reports.csv import write_csv_report
from .reports.json import write_json_report

def parse_w_flag(value: str) -> int:
    try:
        w = int(value)
        if w <= 0:
            raise argparse.ArgumentTypeError("--workers must be atleast 1")
        
        return min(w, MAX_W)
        
    except ValueError:
        if value.strip().lower() == 'ssd':
            return DEFAULT_W_SSD
        
        raise argparse.ArgumentTypeError(f"--workers must be a number or 'ssd'.")

def parse_sort_flag(value: str, sort_options: list[str], flag_name: str) -> tuple[str, str]:
    split_values = value.split(':', 1)
    sort_by = split_values[0].strip()
    order = split_values[1].strip() if len(split_values) > 1 else 'asc'

    if sort_by not in sort_options:
        raise argparse.ArgumentTypeError(f"Invalid option '{sort_by}' for {flag_name} Choose from: {', '.join(sort_options)}")
    if order not in ('asc', 'desc'):
        raise argparse.ArgumentTypeError(f"Invalid order '{order}'. Choose asc or desc.")
    return sort_by, order

def main():
    try:
        parser = argparse.ArgumentParser(
            description="Scan media libraries across nested folders and generate reports.",
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument(
            "folder_path",
            help="The full path to the main folder you want to scan."
        )
        parser.add_argument(
            "-e", "--exclude",
            nargs='+',
            default=[],
            help="Space separated list of folder names to exclude from the scan (case sensitive)."
        )
        parser.add_argument(
            "-ext", "--extensions",
            nargs='+',
            help=(
                "Space separated list of file extensions to scan (e.g. mp4 mkv webm).\n"
                f"(default: {DEFAULT_VIDEO_EXTENSIONS})."
            )
        )
        parser.add_argument(
            "-w", "--workers",
            type=parse_w_flag,
            default=DEFAULT_W,
            help=(
                f"Number of parallel threads to use (default: {DEFAULT_W} for your system)\n"
                f"-w ssd : Uses an optimal {DEFAULT_W_SSD} for your system, provide it if you have an SSD\n"
                "-w <n> : Manually provide threads (e.g. -w 6)\n"
            )
        )
        parser.add_argument(
            "-f", "--format",
            choices=['txt', 'csv', 'json', 'all'],
            default='txt',
            help="Output file format (default: txt).")
        parser.add_argument(
            "-t", "--template", 
            choices=['summary', 'detailed'], 
            default='summary',
            help="Text report template (default: summary)."
        )
        parser.add_argument(
            "--include-size-txt",
            action="store_true",
            help="Include video size in the txt reports."
        )
        parser.add_argument(
            '-sf', '--sort-folders',
            type=lambda v: parse_sort_flag(v, ['name', 'duration', 'videos', 'size', 'date'], '--sort-folders'),
            default=('name', 'asc'),
            help=(
                "Sort folders by: name, duration, videos, size, date\n"
                "Optionally include sort order with colon: duration:desc\n"
                "Sort order is asc if not provided (default: name:asc)"
            )
        )
        parser.add_argument(
            '-sv', '--sort-videos',
            type=lambda v: parse_sort_flag(v, ['name', 'duration', 'size', 'date'], '--sort-videos'),
            default=('name', 'asc'),
            help=(
                "Sort folders by: name, duration, size, date\n"
                "Optionally include sort order with colon: duration:desc\n"
                "Sort order is asc if not provided (default: name:asc)"
            )
        )
        parser.add_argument(
            "--fast-start",
            action="store_true",
            help="Directly start processing (Recommended for network drives).\n"
                "Note: Only processed count will be displayed, not progress bar."
        )
        parser.add_argument(
            "--ffprobe-timeout",
            type=float,
            default=15.0,
            help="Maximum seconds to wait for a video before marking as failed (default: 15.0).\n"
                "Increase this for slow network drives."
        )
        args = parser.parse_args()

        ui = get_ui()

        if not FFPROBE_PATH:
            print(ui.error("\nERROR: ffprobe not found in system PATH"))
            print("This script requires FFmpeg to work.")
            print("Install FFmpeg from https://ffmpeg.org/download.html and add it to your system's PATH.")
            sys.exit(1)

        try:
            # Validate ffprobe is executable, not just present on path
            subprocess.run(
                [FFPROBE_PATH, "-version"], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                check=True
            )
        except Exception as e:
            print(ui.error(f"ERROR: ffprobe was found, but failed to execute. {e}"))
            sys.exit(1)

        root_folder = format_windows_max_path(args.folder_path) # Handle long paths on Windows

        if not os.path.isdir(root_folder):
            print(ui.error(f"ERROR: The path '{root_folder}' is not a valid directory."))
            sys.exit(1)

        excluded_folders = set(args.exclude)

        if args.extensions:
            video_extensions = {ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in args.extensions}
        else:
            video_extensions = DEFAULT_VIDEO_EXTENSIONS

        print(f"Scanning folder: {ui.info(root_folder)}")
        if excluded_folders:
            print(f"Excluding folders: {ui.info(', '.join(excluded_folders))}")

        scan_result = scan_videos_concurrently(
            root_folder,
            video_extensions,
            excluded_folders,
            args.workers,
            args.ffprobe_timeout,
            args.fast_start,
            ui
        )

        failed_count = len(scan_result.failed_videos_data)

        if not scan_result.folders:
            if failed_count > 0:
                print(ui.warning(f"\n[!] NOTE: Found {failed_count} videos, but all of them failed."))
            else:
                print(ui.warning("\nNo video files found with the default extensions:"))
                print(ui.info(', '.join(sorted(DEFAULT_VIDEO_EXTENSIONS))))
                print(f"To include other formats, or scan for specific formats only, please provide them in {ui.info('--extensions')} flag.")
            sys.exit(0)

        sort_folders_by, sort_order_folders = args.sort_folders
        sort_videos_by, sort_order_videos = args.sort_videos

        sort_results(
            scan_result.folders,
            sort_folders_by,
            sort_order_folders == 'desc',
            sort_videos_by,
            sort_order_videos == 'desc'
        )
        
        folder_name = os.path.basename(os.path.normpath(root_folder))
        timestamp = datetime.datetime.now()
        report_format = args.format

        try:
            if report_format in ['csv', 'all']:
                csv_output_filename = f"{folder_name}_vidscan_report.csv"
                csv_output_path = os.path.join(root_folder, csv_output_filename)

                write_csv_report(
                    scan_result,
                    csv_output_path,
                    root_folder,
                    timestamp
                )
                print(ui.success("\nSuccess! CSV file saved to:"))
                print(ui.info(csv_output_path))
                
                if failed_count > 0 and report_format != 'all':
                    print(ui.warning(f"\n[!] NOTE: Scanning failed for {failed_count} videos. Check the 'FAILED' rows in the CSV."))

            if report_format in ['json', 'all']:
                json_output_filename = f"{folder_name}_vidscan_report.json"
                json_output_path = os.path.join(root_folder, json_output_filename)

                write_json_report(
                    scan_result,
                    json_output_path,
                    timestamp
                )
                print(ui.success(f"\nSuccess! JSON file saved to:"))
                print(ui.info(json_output_path))
                
                if failed_count > 0 and report_format != 'all':
                    print(ui.warning(f"\n[!] NOTE: Scanning failed for {failed_count} videos. Check the 'failed_files' array in the JSON."))
                
            if report_format in ['txt', 'all']:
                txt_output_filename = f"{folder_name} - vidscan Report.txt"
                txt_output_path = os.path.join(root_folder, txt_output_filename)

                failed_videos_report_filename = f"{folder_name} - vidscan Failed Files.txt"
                failed_videos_report_path = os.path.join(root_folder, failed_videos_report_filename)

                txt_report_template = 'detailed' if report_format == 'all' else args.template

                report_content, failed_videos_report_content = write_txt_and_failed_videos_report(
                    scan_result,
                    txt_output_path,
                    txt_report_template,
                    failed_videos_report_path,
                    timestamp,
                    args.include_size_txt
                )

                print(ui.warning("\n--- File Preview ---"))
                print(report_content)
                print(ui.success("\nSuccess! Text file saved to:"))
                print(ui.info(txt_output_path))

                if failed_count > 0:
                    print(ui.warning(f"\n[!] NOTE: Scanning failed for {failed_count} videos."))
                    print(ui.warning("\n--- Failed Videos File Preview ---"))
                    print(failed_videos_report_content)
                    print(ui.warning("\nFailed videos file has been saved to:"))
                    print(ui.info(failed_videos_report_path))

                    if report_format == 'all':
                        print(ui.warning("\nFailed videos and error messages can be found here in csv, json:"))
                        print(ui.warning("-'FAILED' rows in CSV."))
                        print(ui.warning("-'failed_videos' array in JSON."))

        except Exception as e:
            print(ui.error(f"\nERROR: Could not save the file. Reason: {e}"))

    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
        sys.exit(130)
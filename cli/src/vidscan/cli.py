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
from .reports.txt import write_txt_report, get_txt_report_summary_lines, get_txt_report_detailed_lines, get_failed_videos_report_lines
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
            description="Scan media libraries across nested folders and generate reports",
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument(
            "folder_path",
            help="The full path to the main folder you want to scan"
        )
        parser.add_argument(
            "-e", "--exclude",
            nargs='+',
            default=[],
            help="Space separated list of folder names to exclude from the scan (case sensitive)"
        )
        parser.add_argument(
            "-ext", "--extensions",
            nargs='+',
            help=(
                "Space separated list of file extensions to scan (e.g. mp4 mkv webm)\n"
                f"(default: {' '.join(DEFAULT_VIDEO_EXTENSIONS)})"
            )
        )
        parser.add_argument(
            "-w", "--workers",
            type=parse_w_flag,
            default=DEFAULT_W,
            help=(
                f"Number of parallel threads to use (default: '{DEFAULT_W}' for your system).\n"
                f"-w ssd : Uses an optimal '{DEFAULT_W_SSD}' for your system, provide it if you have an SSD\n"
                "-w <n> : Manually provide threads (e.g. -w 6)\n"
            )
        )
        parser.add_argument(
            "-f", "--format",
            choices=['txt-summary', 'txt-detailed', 'csv', 'json', 'all'],
            default='txt-detailed',
            help="Output report format (default: txt-detailed)"
        )
        parser.add_argument(
            "-o", "--output-dir",
            default=None,
            help=(
                "Path of folder to save reports to.\n"
                "Defaults to scanned folder if not provided."
            )
        )
        parser.add_argument(
            "-sf", "--sort-folders",
            type=lambda v: parse_sort_flag(v, ['name', 'duration', 'videos', 'size', 'date'], '--sort-folders'),
            default=('name', 'asc'),
            help=(
                "Sort folders by: name, duration, videos, size, date\n"
                "Optionally provide sort order with colon: duration:desc\n"
                "Sort order is asc if not provided (default: name:asc)"
            )
        )
        parser.add_argument(
            "-sv", "--sort-videos",
            type=lambda v: parse_sort_flag(v, ['name', 'duration', 'size', 'date'], '--sort-videos'),
            default=('name', 'asc'),
            help=(
                "Sort videos by: name, duration, size, date\n"
                "Optionally provide sort order with colon: duration:desc\n"
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

        scan_folder_path = format_windows_max_path(args.folder_path) # Handle long paths on Windows

        if not os.path.isdir(scan_folder_path):
            print(ui.error(f"ERROR: Path provided for scanning is not a directory: '{scan_folder_path}'"))
            sys.exit(1)
        
        if args.output_dir:
            output_dir = format_windows_max_path(args.output_dir)
            
            if not os.path.exists(output_dir):
                print(ui.error(f"ERROR: Provided output directory does not exist: '{output_dir}'"))
                sys.exit(1)
            
            if not os.path.isdir(output_dir):
                print(ui.error(f"ERROR: Provided output path is not a directory: '{output_dir}'"))
                sys.exit(1)
            
            test_file = os.path.join(output_dir, '.vidscan_write_test')

            try:
                with open(test_file, 'w') as f:
                    f.write('')
                os.remove(test_file)
            except PermissionError:
                print(ui.error(f"ERROR: No write permission for provided output directory: '{output_dir}'"))
                sys.exit(1)
            except OSError as e:
                print(ui.error(f"ERROR: Cannot write to provided output directory: '{output_dir}'. Reason: {e}"))
                sys.exit(1)
        else:
            output_dir = scan_folder_path

        excluded_folders = set(args.exclude)

        if args.extensions:
            video_extensions = {ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in args.extensions}
        else:
            video_extensions = DEFAULT_VIDEO_EXTENSIONS

        print(f"Scanning folder: {ui.info(scan_folder_path)}")
        if excluded_folders:
            print(f"Excluding folders: {ui.info(', '.join(excluded_folders))}")

        scan_result = scan_videos_concurrently(
            scan_folder_path,
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
        
        folder_name = os.path.basename(os.path.normpath(scan_folder_path))
        timestamp = datetime.datetime.now()
        report_format = args.format
        
        is_txt_summary = report_format == 'txt-summary'
        is_txt_detailed = report_format == 'txt-detailed'
        is_csv = report_format == 'csv'
        is_json = report_format == 'json'
        is_all = report_format == 'all'

        try:
            if is_csv or is_all:
                csv_output_filename = f"{folder_name}_vidscan_report.csv"
                csv_output_path = os.path.join(output_dir, csv_output_filename)

                write_csv_report(
                    scan_result,
                    csv_output_path,
                    scan_folder_path,
                    timestamp
                )
                print(ui.success("\nSuccess! CSV file saved to:"))
                print(ui.info(csv_output_path))
                
                if failed_count > 0 and not is_all:
                    print(ui.warning(f"\n[!] NOTE: Scanning failed for {failed_count} videos. Check the 'FAILED' rows in the CSV."))

            if is_json or is_all:
                json_output_filename = f"{folder_name}_vidscan_report.json"
                json_output_path = os.path.join(output_dir, json_output_filename)

                write_json_report(
                    scan_result,
                    json_output_path,
                    timestamp
                )
                print(ui.success(f"\nSuccess! JSON file saved to:"))
                print(ui.info(json_output_path))
                
                if failed_count > 0 and not is_all:
                    print(ui.warning(f"\n[!] NOTE: Scanning failed for {failed_count} videos. Check the 'failed_files' array in the JSON."))
                
            if is_txt_summary or is_txt_detailed or is_all:
                txt_summary_output_filename = f"{folder_name} - vidscan Summary Report.txt"
                txt_detailed_output_filename = f"{folder_name} - vidscan Detailed Report.txt"
                failed_videos_report_filename = f"{folder_name} - vidscan Failed Files.txt"
                
                txt_summary_output_path = os.path.join(output_dir, txt_summary_output_filename)
                txt_detailed_output_path = os.path.join(output_dir, txt_detailed_output_filename)
                failed_videos_report_path = os.path.join(output_dir, failed_videos_report_filename)

                timestamp_str = f"Generated on: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

                if is_txt_summary or is_all:
                    report_content = write_txt_report(
                        get_txt_report_summary_lines(scan_result),
                        txt_summary_output_path,
                        timestamp_str
                    )

                    print(ui.warning("\n--- Txt Summary File Preview ---"))
                    print(report_content)
                    print(ui.success("\n\nSuccess! Text file saved to:"))
                    print(ui.info(txt_summary_output_path))

                if is_txt_detailed or is_all:
                    report_content = write_txt_report(
                        get_txt_report_detailed_lines(scan_result),
                        txt_detailed_output_path,
                        timestamp_str
                    )

                    print(ui.warning("\n--- Txt Detailed File Preview ---"))
                    print(report_content)
                    print(ui.success("\n\nSuccess! Text file saved to:"))
                    print(ui.info(txt_detailed_output_path))

                if failed_count > 0:
                    failed_report_content = write_txt_report(
                        get_failed_videos_report_lines(scan_result.failed_videos_data),
                        failed_videos_report_path,
                        timestamp_str
                    )

                    print(ui.warning("\n--- Failed Videos File Preview ---"))
                    print(failed_report_content)

                    print(ui.warning(f"\n\n[!] NOTE: Scanning failed for {failed_count} videos."))
                    print(ui.warning("\nFailed videos file has been saved to:"))
                    print(ui.info(failed_videos_report_path))

                    if is_all:
                        print(ui.warning("\nFailed videos and error messages can be found here in csv, json:"))
                        print(ui.warning("-'FAILED' rows in CSV."))
                        print(ui.warning("-'failed_videos' array in JSON."))

        except Exception as e:
            print(ui.error(f"\nERROR: Could not save the file. Reason: {e}"))

    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
        sys.exit(130)
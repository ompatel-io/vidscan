import os
import subprocess
import shutil
import sys

def get_restricted_paths():
    return [
        os.path.normcase(os.path.abspath(os.sep)),
        os.path.normcase(os.path.abspath(os.path.expanduser("~"))),
        os.path.normcase(os.path.abspath(os.getcwd())),
    ]

def check_output_path_safe(output_path, restrict_paths):
    if os.path.normcase(output_path) in restrict_paths:
        print(f"\n'{output_path}' is a system or working directory.")
        print("Aborting...")
        sys.exit(1)

def confirm_overwrite_if_exists(output_path):
    if os.path.exists(output_path):
        if os.path.isdir(output_path) and len(os.listdir(output_path)) > 0:
            print(f"\nWARNING: The destination '{output_path}' already exists and contains files.")
            print("Continuing will PERMANENTLY DELETE everything inside it.")

            prompt = input("Are you absolutely sure you want to delete this folder? [y/N]: ")
            if prompt.lower() not in ["y", "yes"]:
                print("Not deleted. Aborting...")
                sys.exit(0)

            shutil.rmtree(output_path)

def cleanup_output(output_path, restrict_paths, is_success):
    if not is_success and output_path and os.path.exists(output_path):
        if os.path.normcase(output_path) not in restrict_paths:
            shutil.rmtree(output_path)
            print(f" - Removed --output folder: {output_path}")

def get_duration(ffprobe_path, video_path, ffprobe_timeout_sec=15.0):
    try:
        command = [
            ffprobe_path, 
            "-v", "error", 
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", 
            video_path
        ]

        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=ffprobe_timeout_sec)

        try:
            duration = float(result.stdout.strip())
            if duration > 0:
                return duration, ""
            return 0.0, f"ffprobe returned invalid duration: {duration}"
        except ValueError:
            return 0.0, f"ffprobe returned: {result.stdout.strip()}"
        
    except subprocess.TimeoutExpired:
        return 0.0, f"Process timed out after {ffprobe_timeout_sec} seconds"
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Corrupted or unreadable file"
        return 0.0, error_msg
    except Exception as e:
        return 0.0, str(e)
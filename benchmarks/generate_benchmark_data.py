import os
import random
import subprocess
import argparse
import shutil
import math
import sys

FFMPEG_PATH = shutil.which('ffmpeg')
FFPROBE_PATH = shutil.which("ffprobe")

FORMATS = ["mp4_start", "mp4_end", "mkv"]

def parse_formats(format_str):
    formats = []
    weights = []
    
    if ':' not in format_str:
        raw_formats = format_str.split(',')
        formats = [f.strip().lower() for f in raw_formats]
        weights = [100.0 / len(formats)] * len(formats)
        return formats, weights

    parts = format_str.split(',')
    for part in parts:
        if ':' not in part:
            print(f"ERROR: Invalid syntax '{part}'. Provide 'format:weight'.")
            sys.exit(1)
        fmt, weight = part.split(':')
        formats.append(fmt.strip().lower())
        weights.append(float(weight))
        
    return formats, weights

def generate_seed_video(output_path, target_size_mb, duration_sec, format):
    if format not in FORMATS:
        print(f"ERROR: Format not supported '{format}'")
        print(f"Supported: {FORMATS}")
        sys.exit(1)
    
    movflags = []
    if format == "mp4_start":
        movflags = ["-movflags", "+faststart"]        

    audio_bitrate_kbps = 128

    total_kbps = (target_size_mb * 1000 * 8) / duration_sec
    video_bitrate_kbps = max(total_kbps - audio_bitrate_kbps, 100)

    bitrate_str = f"{int(video_bitrate_kbps)}k"
    bufsize_str = f"{int(video_bitrate_kbps / 2)}k"

    print(f"Generating Seed Video ({format}): ~{target_size_mb} MB, ~{duration_sec}s "
          f"(bitrate ~{video_bitrate_kbps:.0f} kbps)")

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "nullsrc=s=640x360:r=30",
        "-f", "lavfi", "-i", "anoisesrc=c=white:r=48000:a=0.5",
        "-vf", "noise=alls=100:allf=t+u",
        "-t", str(duration_sec),
        "-c:v", "libx264",
        "-b:v", bitrate_str, "-maxrate", bitrate_str, "-bufsize", bufsize_str,
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
    ]
    cmd.extend(movflags)
    cmd.append(output_path)
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(output_path):
        print(f"ERROR: Failed to generate for {output_path}")
        sys.exit(1)

def verify_seed_video(video_path, expected_duration_sec=None, max_diff_percentage=0.15):
    cmd = [
        FFPROBE_PATH, 
        "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        video_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            return False
            
        duration = float(result.stdout.strip())
        if duration <= 0:
            return False

        if expected_duration_sec is not None:
            diff_percentage = abs(duration - expected_duration_sec) / expected_duration_sec
            if diff_percentage > max_diff_percentage:
                print(f"WARNING: '{video_path}' duration {duration:.1f}s "
                      f"deviates >{max_diff_percentage*100:.0f}% from target {expected_duration_sec}s")
                return False

        return True
    except Exception:
        return False

def manual_copy(src_path, dest_path, chunk_size=1024*1024*8):
    with open(src_path, 'rb') as fsrc:
        with open(dest_path, 'wb') as fdest:
            while True:
                chunk = fsrc.read(chunk_size)
                if not chunk:
                    break
                fdest.write(chunk)

def build_directory_tree(root_dir, max_depth, max_branch):    
    os.makedirs(root_dir, exist_ok=True)
    
    folders = [root_dir]
    current_depth_folders = [root_dir]
    
    if max_depth == 0:
        return folders
        
    for depth in range(1, max_depth + 1):
        next_depth_folders = []
        for parent in current_depth_folders:
            for i in range(random.randint(0, max_branch)):
                folder_name = f"Folder_{depth}_{i}"
                path = os.path.join(parent, folder_name)
                os.makedirs(path, exist_ok=True)
                folders.append(path)
                next_depth_folders.append(path)
        current_depth_folders = next_depth_folders
        
    return folders

def main():
    target_path = ""
    seed_videos = {}
    is_target_folder_created = False
    is_success = False
    is_user_abort = False

    restrict_paths = [
        os.path.normcase(os.path.abspath(os.sep)), 
        os.path.normcase(os.path.abspath(os.path.expanduser("~"))), 
        os.path.normcase(os.path.abspath(os.getcwd()))
    ]

    try:
        parser = argparse.ArgumentParser(
            description="VidScan Benchmark Data Generator",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        parser.add_argument(
            '-c', '--count',
            type=int,
            default=200,
            help="Number of videos per copy"
        )
        parser.add_argument(
            '-s', '--size',
            type=float,
            default=10.0,
            help="Size in MB per video"
        )
        parser.add_argument(
            '-d', '--duration',
            type=float,
            default=60.0,
            help="Duration in seconds per video"
        )
        parser.add_argument(
            '-f', '--formats',
            type=str,
            default="mp4_start:40,mp4_end:40,mkv:20", 
            help=f"Formats with weights"
        )
        parser.add_argument(
            '--max-depth',
            type=int,
            default=3,
            help="Maximum nesting depth for folder"
        )
        parser.add_argument(
            '--max-branch',
            type=int,
            default=3,
            help="Maximum number of subfolders per folder"
        )
        parser.add_argument(
            '--copies',
            type=int,
            default=1,
            help="Number of copies to generate of benchmark data folder"
        )
        parser.add_argument(
            '--dest',
            type=str,
            default="vidscan_benchmark_data",
            help="Destination path"
        )
        args = parser.parse_args()

        if not FFMPEG_PATH or not FFPROBE_PATH:
            print("\n--- ERROR: FFmpeg not found in system PATH ---")
            print("Install FFmpeg from https://ffmpeg.org/download.html and add it to your system's PATH.")
            sys.exit(1)
        
        try:
            subprocess.run(
                [FFMPEG_PATH, "-version"], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                check=True
            )
            subprocess.run(
                [FFPROBE_PATH, "-version"], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                check=True
            )
        except Exception as e:
            print(f"ERROR: FFmpeg and ffprobe were found, but failed to execute. {e}")
            sys.exit(1)
        
        formats, weights = parse_formats(args.formats)
        total_weight = sum(weights)

        if not math.isclose(total_weight, 100.0, rel_tol=1e-4):
            print(f"ERROR: Invalid weights. Must add up to 100. Input weights: '{args.formats}'")
            sys.exit(1)

        print("------------- CONFIGURATION -------------")
        print(f"Videos per copy    : {args.count}")
        print(f"Size per video     : ~{args.size} MB/file")
        print(f"Duration per video : ~{args.duration}s")
        print(f"Formats            : {list(zip(formats, weights))}")
        print(f"Max Depth          : {args.max_depth}")
        print(f"Max Branch         : {args.max_branch}")
        print(f"Total Copies       : {args.copies}")
        print("-----------------------------------------")

        required_mb = args.count * args.size * args.copies
        required_bytes = required_mb * 1024 * 1024 
        required_gb = required_mb / 1024

        _, _, free = shutil.disk_usage(os.getcwd())
        free_gb = free / (1024 * 1024 * 1024)

        print(f"\n-------- DISK SPACE --------")
        print(f"Required Space: ~{required_gb:.2f} GB")
        print(f"Available Space: {free_gb:.2f} GB")
        print(f"-----------------------------\n")

        if required_bytes > free:
            print(f"\nERROR: Insufficient disk space!")
            print(f"Need ~{required_gb:.2f} GB, but have {free_gb:.2f} GB available.")
            sys.exit(1)

        prompt = input(f"WARNING: This will generate ~{required_gb:.2f} GB of data. Continue? [y/N]: ")
        if prompt.lower() not in ['y', 'yes']:
            print("No files were created. Aborting... ")
            sys.exit(0)
        
        target_path = os.path.abspath(os.path.expanduser(args.dest))

        if target_path in restrict_paths:
            print(f"\n[!]'{target_path}' is a system or working directory.")
            print("Aborting...")
            sys.exit(1)

        if os.path.exists(target_path):
            if os.path.isdir(target_path) and len(os.listdir(target_path)) > 0:
                print(f"\nWARNING: The destination '{target_path}' already exists and contains files.")
                print("Continuing will PERMANENTLY DELETE everything inside it.")
                prompt = input("Are you absolutely sure you want to delete this folder? [y/N]: ")
                if prompt.lower() not in ['y', 'yes']:
                    print("Not deleted. Aborting...")
                    sys.exit(0)
                
                shutil.rmtree(target_path)
    
        os.makedirs(target_path, exist_ok=True)
        is_target_folder_created = True

        print("\nGenerating Seed Videos...\n")
        for fmt in formats:
            seed_video_path = f"seed_video_{fmt}{'.mp4' if 'mp4' in fmt else '.mkv'}"
            seed_videos[fmt] = seed_video_path
            generate_seed_video(seed_video_path, args.size, args.duration, fmt)

        print("\nValidating Seed Videos...")
        for fmt, seed_video_path in seed_videos.items():
            if not os.path.exists(seed_video_path):
                print(f"ERROR: Failed to generate '{seed_video_path}'")
                sys.exit(1)

            if not verify_seed_video(seed_video_path, expected_duration_sec=args.duration):
                print(f"ERROR: '{seed_video_path}' generated, but container is corrupted or duration off-target!")
                print("FFmpeg failed to write valid video headers. Aborting...")
                sys.exit(1)
            
        print("\nBuilding Directory Tree and Copies...")
        bytes_written = 0

        for copy_idx in range(1, args.copies + 1):
            run_dir = os.path.join(target_path, f"Run_{copy_idx}")
            
            folders = build_directory_tree(run_dir, args.max_depth, args.max_branch)
            
            print(f"\nGenerating Folder: {run_dir}")
            for i in range(1, args.count + 1):
                target_folder = random.choice(folders)
                chosen_format = random.choices(formats, weights=weights, k=1)[0]

                ext = ".mp4" if "mp4" in chosen_format else ".mkv"
                file_name = f"Vid_{i:04d}_{chosen_format}{ext}"
                video_dest_path = os.path.join(target_folder, file_name)
                video_src_path = seed_videos[chosen_format]

                manual_copy(video_src_path, video_dest_path)
                bytes_written += os.path.getsize(video_dest_path)
                
                sys.stdout.write(f"\rProgress: [{i}/{args.count}] files.")
                sys.stdout.flush()

        print(f"\n\nSUCCESS! Generated {args.copies} data folders.")
        print(f"Total size on disk: {(bytes_written / (1024 * 1024 * 1024)):.2f} GB.")
        is_success = True

    except KeyboardInterrupt:
        is_user_abort = True
        print("\n\n[!] Interrupted by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
    finally:
        print("\nInitiating cleanup...")
        for file in list(seed_videos.values()):
            if os.path.exists(file):
                os.remove(file)
                print(f" - Removed seed file: {file}")

        if not is_success and is_target_folder_created and target_path:
            if target_path not in restrict_paths and os.path.exists(target_path):
                shutil.rmtree(target_path)
                print(f" - Removed --dest folder: {target_path}")
        
        if not is_success and not is_user_abort:
            sys.exit(1)

if __name__ == "__main__":
    main()
import os
import subprocess
import argparse
import shutil
import sys

from common import check_output_path_safe, cleanup_output, confirm_overwrite_if_exists, get_duration, get_restricted_paths

FFMPEG_PATH = shutil.which("ffmpeg") or ""
FFPROBE_PATH = shutil.which("ffprobe") or ""

FORMATS = {"mp4_start", "mp4_end", "mkv"}

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
        print(f"Supported: {sorted(FORMATS)}")
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
          f"(bitrate ~{video_bitrate_kbps:.0f} kbps)...")
    
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

def verify_seed_video(video_path, expected_duration_sec, max_diff_percentage=0.15):
    duration, err_msg = get_duration(FFPROBE_PATH, video_path)
    if err_msg:
        print(f"ERROR: ffrobe failed for '{video_path}'.", err_msg)
        return False
    
    diff_percentage = abs(duration - expected_duration_sec) / expected_duration_sec
    if diff_percentage > max_diff_percentage:
        print(f"WARNING: '{video_path}' duration {duration:.1f}s "
              f"deviates >{max_diff_percentage*100:.0f}% from target {expected_duration_sec}s")
        return False
    return True

def main():
    output_dir = ""
    generated_paths = []
    is_success = False
    is_user_abort = False
    restrict_paths = get_restricted_paths()

    try:
        parser = argparse.ArgumentParser(
            description="Benchmark Seed Videos Generator",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser.add_argument(
            "-f", "--formats",
            type=str,
            default="mp4_start,mp4_end,mkv",
            help=f"Comma separated formats"
                f"(from: {FORMATS})"
        )
        parser.add_argument(
            "-s", "--size",
            type=float,
            default=10.0,
            help="Size in MB per seed video"
        )
        parser.add_argument(
            "-d", "--duration",
            type=float,
            default=60.0,
            help="Duration in seconds per seed video"
        )
        parser.add_argument(
            "-o", "--output",
            type=str,
            default="vidscan_benchmark_synthetic_seeds",
            help="Output path for generated seed files"
        )
        args = parser.parse_args()

        if not FFMPEG_PATH or not FFPROBE_PATH:
            print("\n--- ERROR: FFmpeg not found in system PATH ---")
            print("Install FFmpeg from https://ffmpeg.org/download.html and add it to your system's PATH.")
            sys.exit(1)

        try:
            subprocess.run(
                [FFMPEG_PATH, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
            )
            subprocess.run(
                [FFPROBE_PATH, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
            )

        except Exception as e:
            print(f"ERROR: FFmpeg and ffprobe were found, but failed to execute. {e}")
            sys.exit(1)

        formats = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
        for fmt in formats:
            if fmt not in FORMATS:
                print(f"ERROR: Unknown format '{fmt}'. Supported: {sorted(FORMATS)}")
                sys.exit(1)
        if not formats:
            print("ERROR: No formats given.")
            sys.exit(1)

        output_dir = os.path.abspath(os.path.expanduser(args.output))

        check_output_path_safe(output_dir, restrict_paths)

        confirm_overwrite_if_exists(output_dir)

        os.makedirs(output_dir, exist_ok=True)

        print("\nGenerating Seed Videos...\n")
        for fmt in formats:
            ext = ".mp4" if "mp4" in fmt else ".mkv"
            seed_path = os.path.join(output_dir, f"{fmt}{ext}")
            generate_seed_video(seed_path, args.size, args.duration, fmt)
            generated_paths.append(seed_path)

        print("\nValidating Seed Videos...")
        for path in generated_paths:
            if not verify_seed_video(path, args.duration):
                print(f"ERROR: '{path}' generated, but container is corrupted or duration off-target")
                sys.exit(1)

        print(f"\nSUCCESS! Generated {len(generated_paths)} seed file(s) in '{output_dir}'.")
        is_success = True

    except KeyboardInterrupt:
        is_user_abort = True
        print("\n[!] Interrupted by user")

    except Exception as e:
        print(f"\nERROR: {e}")

    finally:
        cleanup_output(output_dir, restrict_paths, is_success)
        if not is_success and not is_user_abort:
            sys.exit(1)

if __name__ == "__main__":
    main()
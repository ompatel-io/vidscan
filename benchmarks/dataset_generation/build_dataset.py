import os
import random
import argparse
import shutil
import sys

from common import check_output_path_safe, cleanup_output, confirm_overwrite_if_exists, get_duration, get_restricted_paths

FFPROBE_PATH = shutil.which("ffprobe") or ""

DEFAULT_EXTENSIONS = ".mp4,.mkv,.mov,.avi,.webm,.wmv,.flv,.mpg,.mpeg,.m4v"

def parse_manual_seeds_cli(cli_seeds):
    """'path:weight,path:weight,...' -> [(path, weight), ...]."""
    seeds = []
    for part in cli_seeds.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            print(f"ERROR: Invalid syntax '{part}'. Provide 'path:weight'.")
            sys.exit(1)
        # rsplit because of windows paths (C:\)
        path, weight_str = part.rsplit(":", 1)
        path = path.strip()
        try:
            weight = float(weight_str)
            if weight <= 0:
                print("ERROR: Weights must be positive.")
                sys.exit(1)
        except ValueError:
            print(f"ERROR: Invalid weight in entry '{part}'.")
            sys.exit(1)
        seeds.append((path, weight))
    return seeds

def parse_manual_seeds_file(file_path):
    """One 'path:weight' per line. '#' comments and blank lines skipped."""
    if not os.path.isfile(file_path):
        print(f"ERROR: --seeds-file not found: '{file_path}'")
        sys.exit(1)

    seeds = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                print(f"ERROR: Invalid syntax at line {line_num} of '{file_path}': '{line}'")
                sys.exit(1)
            seed_path, weight_str = line.rsplit(":", 1)
            seed_path = seed_path.strip()
            try:
                weight = float(weight_str)
                if weight <= 0:
                    print("ERROR: Weights must be positive.")
                    sys.exit(1)
            except ValueError:
                print(f"ERROR: Invalid weight at line {line_num} of '{file_path}': '{line}'")
                sys.exit(1)
            seeds.append((seed_path, weight))
    return seeds

def seeds_from_dir_equal_weights(seeds_dir, extensions_str):
    if not os.path.isdir(seeds_dir):
        print(f"ERROR: --seeds-dir not found: '{seeds_dir}'")
        sys.exit(1)

    exts = tuple(e.strip().lower() for e in extensions_str.split(","))
    select_seeds = []
    for root, _, files in os.walk(seeds_dir):
        for f in files:
            if f.lower().endswith(exts):
                select_seeds.append(os.path.join(root, f))

    if not select_seeds:
        print(f"ERROR: No video files found in '{seeds_dir}' matching extensions {exts}")
        sys.exit(1)

    return [(p, 1) for p in select_seeds]

def validate_seeds_ffprobe(arg_seeds):
    if not FFPROBE_PATH:
        print("NOTE: ffprobe not found on PATH. Skipping seed validation.")
        return
    
    for path, _ in arg_seeds:
        _, err_msg = get_duration(FFPROBE_PATH, path)
        if err_msg:
            print(f"ERROR: '{path}' failed validation.", err_msg)
            sys.exit(1)

def build_seed_entries(arg_seeds, total_weight):
    """arg_seeds: [(path, weight), ...] -> entry dicts"""
    seed_entries = []
    seen = {}
    for path, weight in arg_seeds:
        label = os.path.splitext(os.path.basename(path))[0]
        if label in seen:
            seen[label] += 1
            label = f"{label}_{seen[label]}"
        else:
            seen[label] = 0

        seed_entries.append({
            "label": label,
            "path": path,
            "weight": weight * 100 / total_weight,
            "ext": os.path.splitext(path)[1],
            "size_bytes": os.path.getsize(path)
        })

    return seed_entries

def estimate_size_and_confirm(seed_entries, count, copies, output_path):
    """seed_entries: dicts with 'weight' and 'size_bytes'.
    Exits on insufficient space."""
    required_bytes = sum(
        (s["weight"] / 100) * count * copies * s["size_bytes"] for s in seed_entries
    )
    required_gb = required_bytes / (1024 * 1024 * 1024)

    check_dir = output_path
    while not os.path.exists(check_dir):
        parent = os.path.dirname(check_dir)
        if parent == check_dir:
            break
        check_dir = parent

    _, _, free = shutil.disk_usage(check_dir)
    free_gb = free / (1024 * 1024 * 1024)

    print(f"\n-------- DISK SPACE --------")
    print(f"Estimated Required Space: ~{required_gb:.2f} GB")
    print(f"Available Space: {free_gb:.2f} GB")
    print(f"-----------------------------\n")

    if required_bytes > free:
        print(f"\nERROR: Insufficient disk space")
        print(f"Need ~{required_gb:.2f} GB, but have {free_gb:.2f} GB available.")
        sys.exit(1)

    prompt = input(f"WARNING: This will generate ~{required_gb:.2f} GB of data. Continue? [y/N]: ")
    if prompt.lower() not in ["y", "yes"]:
        print("No files were created. Aborting... ")
        sys.exit(0)

def manual_copy(src_path, dest_path, chunk_size=1024 * 1024 * 8):
    with open(src_path, "rb") as fsrc:
        with open(dest_path, "wb") as fdest:
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

def duplicate_seeds(seed_entries, output_path, count, copies, max_depth, max_branch):
    """seed_entries: dicts with 'label', 'weight', 'path', 'ext'.
    Returns total bytes written."""
    bytes_written = 0

    entry_labels = [s["label"] for s in seed_entries]
    entry_weights = [s["weight"] for s in seed_entries]
    entries_by_label = {s["label"]: s for s in seed_entries}

    for copy_idx in range(1, copies + 1):
        run_dir = os.path.join(output_path, f"Run_{copy_idx}")
        folders = build_directory_tree(run_dir, max_depth, max_branch)

        print(f"\nGenerating Folder: {run_dir}")
        for i in range(1, count + 1):
            target_folder = random.choice(folders)
            chosen_label = random.choices(entry_labels, weights=entry_weights, k=1)[0]
            chosen = entries_by_label[chosen_label]

            file_name = f"Vid_{i:04d}_{chosen_label}{chosen['ext']}"
            video_dest_path = os.path.join(target_folder, file_name)

            manual_copy(chosen["path"], video_dest_path)
            bytes_written += os.path.getsize(video_dest_path)

            print(f"\rProgress: [{i}/{count}] files.", end="", flush=True)

    return bytes_written

def main():
    output_path = ""
    seed_entries = []
    is_success = False
    is_user_abort = False
    restrict_paths = get_restricted_paths()

    try:
        parser = argparse.ArgumentParser(
            description="Benchmark Dataset Builder",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser.add_argument(
            "-c", "--count",
            type=int,
            default=200,
            help="Number of videos per copy"
        )
        parser.add_argument(
            "--copies",
            type=int,
            default=1,
            help="Number of copies to generate of dataset"
        )
        parser.add_argument(
            "--seeds-dir",
            type=str,
            default="",
            help="Folder of seed video files, equally weighted"
        )
        parser.add_argument(
            "--seeds",
            type=str,
            default="",
            help="Manual seeds via CLI: 'path:weight,path:weight,...'"
        )
        parser.add_argument(
            "--seeds-file",
            type=str,
            default="",
            help="Manual seeds via file, one 'path:weight' per line "
                "('#' comments and blank lines skipped)"
        )
        parser.add_argument(
            "-ext", "--extensions", 
            type=str,
            default=DEFAULT_EXTENSIONS,
            help="Extensions considered when scanning --seeds-dir"
        )
        parser.add_argument(
            "--max-depth",
            type=int,
            default=3,
            help="Maximum nesting depth for folder"
        )
        parser.add_argument(
            "--max-branch",
            type=int,
            default=3,
            help="Maximum number of subfolders per folder"
        )
        parser.add_argument(
            "--no-validate-seeds",
            action="store_true",
            help="Skip given seeds validation"
        )
        parser.add_argument(
            "-o", "--output",
            type=str,
            default="vidscan_benchmark_dataset",
            help="Output path for benchmark dataset"
        )
        args = parser.parse_args()

        dir_given = bool(args.seeds_dir)
        manual_given = bool(args.seeds) or bool(args.seeds_file)

        if args.seeds and args.seeds_file:
            print("ERROR: Provide either --seeds or --seeds-file, not both.")
            sys.exit(1)
        if dir_given and manual_given:
            print("ERROR: Provide either --seeds-dir or manual seeds (--seeds/--seeds-file), not both.")
            sys.exit(1)
        if not dir_given and not manual_given:
            print("ERROR: Provide seeds via --seeds-dir, --seeds, or --seeds-file.")
            sys.exit(1)

        if args.seeds:
            arg_seeds = parse_manual_seeds_cli(args.seeds)
        elif args.seeds_file:
            arg_seeds = parse_manual_seeds_file(args.seeds_file)
        else:
            arg_seeds = seeds_from_dir_equal_weights(args.seeds_dir, args.extensions)

        total_weight = 0
        for path, weight in arg_seeds:
            if not os.path.isfile(path):
                print(f"ERROR: Seed file not found: '{path}'")
                sys.exit(1)
            total_weight += weight

        if not args.no_validate_seeds:
            validate_seeds_ffprobe(arg_seeds)

        output_path = os.path.abspath(os.path.expanduser(args.output))
        check_output_path_safe(output_path, restrict_paths)

        seed_entries = build_seed_entries(arg_seeds, total_weight)

        print("------------- CONFIGURATION -------------")
        print(f"Videos per copy    : {args.count}")
        print(f"Total Copies       : {args.copies}")
        print(f"Seeds              :")
        for s in seed_entries:
            print(f"  - {os.path.basename(s['path'])}  weight={s['weight']:.1f}")
        print(f"Max Depth          : {args.max_depth}")
        print(f"Max Branch         : {args.max_branch}")
        print("-----------------------------------------")

        estimate_size_and_confirm(seed_entries, args.count, args.copies, output_path)

        confirm_overwrite_if_exists(output_path)

        os.makedirs(output_path, exist_ok=True)

        print("\nBuilding Directory Tree and Copies...")
        bytes_written = duplicate_seeds(
            seed_entries, output_path, args.count, args.copies, args.max_depth, args.max_branch
        )

        print(f"\nSUCCESS! Generated {args.copies} data folders.")
        print(f"Total size on disk: {(bytes_written / (1024 * 1024 * 1024)):.2f} GB.")
        is_success = True

    except KeyboardInterrupt:
        is_user_abort = True
        print("\n[!] Interrupted by user")

    except Exception as e:
        print(f"\nERROR: {e}")

    finally:
        cleanup_output(output_path, restrict_paths, is_success)
        if not is_success and not is_user_abort:
            sys.exit(1)

if __name__ == "__main__":
    main()
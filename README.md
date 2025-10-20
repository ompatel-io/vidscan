# VidScan

A Python script to scan nested folders of video files, calculate the total duration for each folder, and generate text report.

---

## Features

- Recursively scans all nested subfolders.
- Calculates the total duration and video count for each folder.
- Excludes provided folders.
- Generates a text report saved in the scanned directory.

---

## Prerequisites

This script requires these two to be installed on your system.

1. **Python (3.8+):** You can download it from [python.org](https://www.python.org/downloads/).
2. **FFmpeg:** This script **requires FFmpeg** to be installed and accessible from your system's PATH. FFmpeg is used to read the video file metadata.
   - You can download FFmpeg from the [official website](https://ffmpeg.org/download.html).
   - After downloading, you must add the location of the `bin` folder (which contains `ffprobe.exe`) to your system's PATH environment variable.

---

## Installation & Configuration

1. Download `vidscan.py`.
2. Open it in a text editor.
3. At the top of the file, set the following 3:
   - `ROOT_FOLDER`: Set this to the full path of the directory you want to scan.
   - `EXCLUDED_FOLDERS`: Add the names of any folders you want to exclude in the scan.
   - `VIDEO_EXTENSIONS`: Add or remove the file extensions you want the script to scan.

---

## Usage

Run this in terminal from the location where the script is saved:

   ```bash
   python vidscan.py
   ```

The script will then scan the `ROOT_FOLDER`, upon completion, will save a report file `<FOLDER_NAME> - Video Duration.txt` inside that same folder.

---

## Example Output

The generated report file will look like this:

```text
Video Duration
========================================
Folder: Folder Name 1
  -> Videos: 7 | Duration: 01:11:28
----------------------------------------
Folder: Folder Name 2
  -> Videos: 5 | Duration: 00:54:47
----------------------------------------
                   .
                   .
                   .
----------------------------------------
Folder: Folder Name 67
  -> Videos: 12 | Duration: 02:08:15
----------------------------------------
Folder: Folder Name 68
  -> Videos: 10 | Duration: 01:45:21
----------------------------------------
TOTALS
  -> Total Folders: 68
  -> Total Videos: 493
  -> Total Duration: 98:37:44
========================================
```

import os

def format_seconds_hms(seconds: float) -> str:
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def format_bytes(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

    size_units = size_bytes
    unit_idx = 0
    while size_units >= 1024 and unit_idx < len(units) - 1:
        size_units /= 1024.0
        unit_idx += 1

    return f"{size_units:.2f} {units[unit_idx]}"

def enable_ansi_windows() -> bool:
    if os.name != 'nt':
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()

        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        
        if not kernel32.SetConsoleMode(handle, mode.value | 0x0004):
            return False 
        
        return True
    except Exception:
        return False

def format_windows_max_path(path: str) -> str:
    if os.name != 'nt':
        return os.path.abspath(path)

    path = os.path.abspath(path)
    
    # Path is safe if < 260 (Windows MAX_PATH)
    if len(path) < 260:
        return path

    # Add extended length prefix for long path
    if not path.startswith('\\\\?\\'):
        if path.startswith('\\\\'):
            # Network/UNC path
            path = f"\\\\?\\UNC\\{path[2:]}"
        else:
            # Local/Mapped Path
            path = f"\\\\?\\{path}"
            
    return path
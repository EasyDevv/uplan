from pathlib import Path
import os
import subprocess
import platform


def ensure_directory(path: Path) -> None:
    """Ensure a directory exists, creating it if necessary"""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"Failed to create directory {path}: {str(e)}")


def ensure_file(path: Path, content: str = "") -> None:
    """Ensure a file exists with optional content"""
    try:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
    except Exception as e:
        raise RuntimeError(f"Failed to create file {path}: {str(e)}")


def validate_file(path: Path) -> bool:
    """Validate that a file exists and is readable"""
    try:
        return path.exists() and os.access(path, os.R_OK)
    except Exception:
        return False


def open_file(file_path: str) -> None:
    """Open a file with the default associated application"""
    try:
        if platform.system() == "Windows":
            os.startfile(file_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.call(["open", file_path])
        else:  # Linux
            subprocess.call(["xdg-open", file_path])
    except Exception as e:
        print(f"Warning: Could not open file {file_path}: {e}")

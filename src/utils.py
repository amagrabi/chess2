import os
import sys


def _resource_path(relative_path):
    """Get absolute path to resource that works for dev and PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
        base_path = os.path.join(base_path, "src")

    return os.path.join(base_path, relative_path)
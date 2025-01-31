import os
import sys


def _resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "src")
        )

    return os.path.join(base_path, relative_path)

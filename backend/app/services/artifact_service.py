"""
Utilities for job artifact lifecycle.
"""
import shutil
import time
from pathlib import Path

from app.config import settings


def _remove_old_children(parent: Path, cutoff: float) -> int:
    removed = 0
    if not parent.exists():
        return removed

    for child in parent.iterdir():
        try:
            mtime = child.stat().st_mtime
        except OSError:
            continue

        if mtime >= cutoff:
            continue

        try:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
            removed += 1
        except OSError as exc:
            print(f"Could not cleanup artifact {child}: {exc}")

    return removed


def cleanup_old_artifacts(retention_days: int | None = None) -> int:
    """
    Remove old generated files so local disk does not grow forever.
    """
    days = retention_days or settings.artifact_retention_days
    if days <= 0:
        return 0

    cutoff = time.time() - days * 24 * 60 * 60
    roots = [
        Path(settings.output_dir),
        Path(settings.assets_dir) / "audio",
        Path(settings.assets_dir) / "video",
        Path(settings.assets_dir) / "images",
    ]

    return sum(_remove_old_children(root, cutoff) for root in roots)

import os
import time
from pathlib import Path
from guessit import guessit

# === Config ===
SOURCE = Path(os.getenv("SOURCE", "/mnt/cloudmedia"))
DEST_BASE = Path(os.getenv("DEST_BASE", "/srv/jellyfin"))
MODIFIED_WITHIN_HOURS = int(os.getenv("MODIFIED_WITHIN_HOURS", 24))  # Default to 24 hours if not set

# === Helper Functions ===

def is_recent(filepath: Path) -> bool:
    """Check if the file was modified within the last N hours."""
    mtime = filepath.stat().st_mtime
    return (time.time() - mtime) <= (MODIFIED_WITHIN_HOURS * 3600)

def make_symlink(source_file: Path, target_path: Path):
    if target_path.exists():
        if target_path.is_symlink():
            if target_path.resolve() == source_file.resolve():
                print(f"[SKIP] Symlink already exists: {target_path}")
                return
            else:
                print(f"[WARN] Updating stale symlink: {target_path}")
                target_path.unlink()
        else:
            print(f"[WARN] Not a symlink, skipping: {target_path}")
            return

    os.makedirs(target_path.parent, exist_ok=True)
    try:
        target_path.symlink_to(source_file)
        print(f"[LINK] {target_path} -> {source_file}")
    except Exception as e:
        print(f"[ERROR] Could not create symlink: {e}")

def process_file(filepath: Path):
    if not is_recent(filepath):
        return  # Skip old files

    info = guessit(filepath.name)

    if info.get("type") == "movie":
        name = info.get("title")
        year = info.get("year", "")
        target_folder = DEST_BASE / "Movies" / f"{name} ({year})"
        target_name = f"{name} ({year}){filepath.suffix}"

    elif info.get("type") == "episode":
        name = info.get("title")
        season = info.get("season")
        episode = info.get("episode")
        if not (season and episode):
            print(f"[SKIP] Incomplete episode info: {filepath}")
            return
        target_folder = DEST_BASE / "TV Shows" / name / f"Season {season:02}"
        target_name = f"{name} - S{season:02}E{episode:02}{filepath.suffix}"

    else:
        print(f"[SKIP] Unknown media type: {filepath}")
        return

    target_path = target_folder / target_name
    make_symlink(filepath, target_path)

def cleanup_broken_symlinks(path: Path):
    """Remove any broken symlinks in the target folder tree."""
    for root, _, files in os.walk(path):
        for file in files:
            full_path = Path(root) / file
            if full_path.is_symlink() and not full_path.exists():
                print(f"[CLEAN] Removing broken symlink: {full_path}")
                full_path.unlink()

# === Main ===

def main():
    print("[START] Cleaning up broken symlinks...")
    cleanup_broken_symlinks(DEST_BASE)

    print("[START] Processing recent files...")
    for root, _, files in os.walk(SOURCE):
        for file in files:
            full_path = Path(root) / file
            process_file(full_path)

if __name__ == "__main__":
    main()

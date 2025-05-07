import os
import time
import re
from pathlib import Path
from guessit import guessit

# === Config ===
SOURCE = Path(os.getenv("SOURCE", "/mnt/cloudmedia"))
DEST_BASE = Path(os.getenv("DEST_BASE", "/srv/jellyfin"))
MODIFIED_WITHIN_HOURS = int(os.getenv("MODIFIED_WITHIN_HOURS", 24))

# === Helper Functions ===

def is_recent(filepath: Path) -> bool:
    """Check if the file was modified within the last N hours."""
    mtime = filepath.stat().st_mtime
    return (time.time() - mtime) <= (MODIFIED_WITHIN_HOURS * 3600)

def clean_filename(filename: str) -> str:
    """
    Strip common release tags like 'www.1TamilMV.moi - ' from the beginning of filenames.
    Extend this pattern as needed for other tag styles.
    """
    # Match patterns like: www.1TamilMV.moi - , www.XXX.com -
    cleaned = re.sub(r'^(www\.[^\s]+)\s*-\s*', '', filename)
    return cleaned.strip()

def make_symlink(source_file: Path, target_path: Path):
    """Create or update a symlink at the target path."""
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
    """Parse filename and create appropriate symlink."""
    if not is_recent(filepath):
        return  # Skip old files

    cleaned_name = clean_filename(filepath.name)
    info = guessit(cleaned_name)

    if info.get("type") == "movie":
        title = info.get("title")
        year = info.get("year", "")
        if not title:
            print(f"[SKIP] No title found: {filepath}")
            return
        target_folder = DEST_BASE / "Movies" / f"{title} ({year})"
        target_name = f"{title} ({year}){filepath.suffix}"

    elif info.get("type") == "episode":
        title = info.get("title")
        season = info.get("season")
        episode = info.get("episode")
        if not (title and season and episode):
            print(f"[SKIP] Incomplete episode info: {filepath}")
            return
        target_folder = DEST_BASE / "TV Shows" / title / f"Season {season:02}"
        target_name = f"{title} - S{season:02}E{episode:02}{filepath.suffix}"

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
    print(f"[INFO] Scanning for recent files in: {SOURCE}")
    cleanup_broken_symlinks(DEST_BASE)

    for root, _, files in os.walk(SOURCE):
        for file in files:
            full_path = Path(root) / file
            process_file(full_path)

if __name__ == "__main__":
    main()

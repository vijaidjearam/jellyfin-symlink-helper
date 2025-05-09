import os
import time
import re
from pathlib import Path
from guessit import guessit

# === Config ===
SOURCE = Path(os.getenv("SOURCE", "/mnt/cloudmedia"))
DEST_BASE = Path(os.getenv("DEST_BASE", "/srv/jellyfin"))

# === Helper Functions ===

# === Allowed media types ===
MEDIA_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.mp3', '.aac', '.flac', '.wav'}


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
    if filepath.suffix.lower() not in MEDIA_EXTENSIONS:
        print(f"[SKIP] Unsupported file type: {filepath}")
        return
    cleaned_name = clean_filename(filepath.name)
    info = guessit(cleaned_name)

    if info.get("type") == "movie":
        title = info.get("title")
        year = info.get("year", "")
        if not title:
            print(f"[SKIP] No title found: {filepath}")
            return
        target_folder = DEST_BASE / "movies" / f"{title} ({year})"
        target_name = f"{title} ({year}){filepath.suffix}"

    elif info.get("type") == "episode" or filepath.parent != SOURCE:
        # If guessit says it's an episode, or it's inside a folder (not directly under SOURCE)
        title = info.get("title") or filepath.parent.name
        season = info.get("season")
        episode = info.get("episode")
        # Try to extract season/episode from filename if guessit missed it
        if not (season and episode):
            # Example fallback: try to parse S01E01 manually
            match = re.search(r'[Ss](\d{1,2})[Ee](\d{1,2})', filepath.name)
            if match:
                season, episode = int(match.group(1)), int(match.group(2))
        if not (title and season and episode):
            print(f"[SKIP] Incomplete episode info: {filepath}")
            return

        target_folder = DEST_BASE / "tvshows" / title / f"Season {season:02}"
        target_name = f"{title} - S{season:02}E{episode:02}{filepath.suffix}"

    else:
        print(f"[SKIP] Unknown media type: {filepath}")
        return

    target_path = target_folder / target_name
    make_symlink(filepath, target_path)

def cleanup_broken_symlinks(path: Path):
    """Remove any broken symlinks in the target folder tree."""
    print(f"[INFO] Cleaning broken symlinks in: {path}")
    for root, _, files in os.walk(path):
        for file in files:
            full_path = Path(root) / file
            try:
                if full_path.is_symlink():
                    target = full_path.resolve(strict=False)
                    if not full_path.exists():
                        print(f"[CLEAN] Removing broken symlink: {full_path} -> {target}")
                        full_path.unlink()
                    else:
                        print(f"[OK] Symlink valid: {full_path} -> {target}")
            except Exception as e:
                print(f"[ERROR] Checking symlink {full_path}: {e}")
# === Main ===

def main():
    print(f"[INFO] Scanning for files in: {SOURCE}")
    cleanup_broken_symlinks(DEST_BASE)

    for dirpath, _, filenames in os.walk(SOURCE):
        for filename in filenames:
            full_path = Path(dirpath) / filename
            if full_path.is_file():
                process_file(full_path)

if __name__ == "__main__":
    main()

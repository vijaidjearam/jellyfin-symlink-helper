import os
import time
import re
from pathlib import Path
from guessit import guessit

# === Config ===
SOURCE = Path(os.getenv("SOURCE", "/mnt/debridlink"))
DEST_BASE = Path(os.getenv("DEST_BASE", "/srv/jellyfin"))
POLL_INTERVAL = 3600  # seconds

# === Allowed media types ===
MEDIA_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.mp3', '.aac', '.flac', '.wav'}

# === Helper Functions ===

def log(message: str):
    """Print log messages with a timestamp."""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)

def clean_filename(filename: str) -> str:
    """Strip common release tags like 'www.1TamilMV.moi - ' from the beginning of filenames."""
    cleaned = re.sub(r'^(?:\[\s*www\.[\w.-]+\s*\]|\(\s*www\.[\w.-]+\s*\)|www\.[\w.-]+)\s*-\s*','',filename,flags=re.IGNORECASE)
    return cleaned.strip()

def make_symlink(source_file: Path, target_path: Path):
    """Create or update a symlink at the target path."""
    if target_path.exists():
        if target_path.is_symlink():
            if target_path.resolve() == source_file.resolve():
                log(f"[SKIP] Symlink already exists: {target_path}")
                return
            else:
                log(f"[WARN] Updating stale symlink: {target_path}")
                target_path.unlink()
        else:
            log(f"[WARN] Not a symlink, skipping: {target_path}")
            return

    os.makedirs(target_path.parent, exist_ok=True)
    try:
        target_path.symlink_to(source_file)
        log(f"[LINK] {target_path} -> {source_file}")
    except Exception as e:
        log(f"[ERROR] Could not create symlink: {e}")

def process_file(filepath: Path):
    """Parse filename and create appropriate symlink."""
    if filepath.suffix.lower() not in MEDIA_EXTENSIONS:
        log(f"[SKIP] Unsupported file type: {filepath}")
        return

    cleaned_name = clean_filename(filepath.name)
    info = guessit(cleaned_name)

    if info.get("type") == "movie":
        title = info.get("title")
        year = info.get("year", "")
        if not title:
            log(f"[SKIP] No title found: {filepath}")
            return
        target_folder = DEST_BASE / "movies" / f"{title} ({year})"
        target_name = f"{title} ({year}){filepath.suffix}"

    elif info.get("type") == "episode" or filepath.parent != SOURCE:
        title = info.get("title") or filepath.parent.name
        season = info.get("season")
        episode = info.get("episode")

        # Normalize season and episode if they are lists
        if isinstance(season, list):
            season = season[0]
        if isinstance(episode, list):
            episode_list = episode
        elif isinstance(episode, int):
            episode_list = [episode]
        else:
            episode_list = []

        # Fallback to regex if episode info is missing
        if not (season and episode_list):
            match = re.search(r'[Ss](\d{1,2})[Ee](\d{1,2})', filepath.name)
            if match:
                season = int(match.group(1))
                episode_list = [int(match.group(2))]

        if not (title and season and episode_list):
            log(f"[SKIP] Incomplete episode info: {filepath}")
            return

        # Format episode part: E01-E02-E03
        episode_str = '-'.join(f"E{e:02}" for e in episode_list)
        target_folder = DEST_BASE / "tvshows" / title / f"Season {season:02}"
        target_name = f"{title} - S{season:02}{episode_str}{filepath.suffix}"

    else:
        log(f"[SKIP] Unknown media type: {filepath}")
        return

    target_path = target_folder / target_name
    make_symlink(filepath, target_path)

def cleanup_broken_symlinks(path: Path):
    """Remove broken symlinks and then clean up empty directories."""
    log(f"[INFO] Cleaning broken symlinks in: {path}")
    for root, _, files in os.walk(path):
        for file in files:
            full_path = Path(root) / file
            try:
                if full_path.is_symlink():
                    target = full_path.resolve(strict=False)
                    if not full_path.exists():
                        log(f"[CLEAN] Removing broken symlink: {full_path} -> {target}")
                        full_path.unlink()
                    else:
                        log(f"[OK] Symlink valid: {full_path} -> {target}")
            except Exception as e:
                log(f"[ERROR] Checking symlink {full_path}: {e}")

    for root, dirs, files in os.walk(path, topdown=False):
        dir_path = Path(root)
        if not any(dir_path.iterdir()):
            try:
                dir_path.rmdir()
                log(f"[CLEAN] Removed empty directory: {dir_path}")
            except Exception as e:
                log(f"[ERROR] Could not remove {dir_path}: {e}")

def main():
    start_time = time.time()
    log(f"[INFO] Scanning for files in: {SOURCE}")
    
    cleanup_broken_symlinks(DEST_BASE)

    for dirpath, _, filenames in os.walk(SOURCE):
        for filename in filenames:
            full_path = Path(dirpath) / filename
            if full_path.is_file():
                process_file(full_path)

    end_time = time.time()
    duration = end_time - start_time
    log(f"[DONE] Script completed in {duration:.2f} seconds.")

if __name__ == "__main__":
    while True:
        main()
        log(f"[INFO] Sleeping for {POLL_INTERVAL} seconds before next scan.")
        time.sleep(POLL_INTERVAL)



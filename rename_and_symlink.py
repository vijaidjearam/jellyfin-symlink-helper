import os
import time
import re
from pathlib import Path
from guessit import guessit
from datetime import datetime

# === Config ===
SOURCE = Path(os.getenv("SOURCE", "/mnt/debridlink"))
DEST_BASE = Path(os.getenv("DEST_BASE", "/srv/jellyfin"))
POLL_INTERVAL = 3600  # seconds

# === Allowed media types ===
MEDIA_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.mp3', '.aac', '.flac', '.wav'}
SUBTITLE_EXTENSIONS = {'.srt', '.sub', '.ass', '.ssa', '.vtt'}

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

def create_nfo_file(target_folder: Path, title: str, year: int = None, season: int = None, episode_list: list = None, release_date: str = None):
    """Create an NFO file with metadata for Jellyfin."""
    
    # Ensure target folder exists before creating NFO
    os.makedirs(target_folder, exist_ok=True)
    
    if season is not None and episode_list is not None:
        # TV Show Episode NFO
        for episode in episode_list:
            episode_str = f"E{episode:02}"
            nfo_path = target_folder / f"{title} - S{season:02}{episode_str}.nfo"
            
            nfo_content = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            nfo_content += '<episodedetails>\n'
            nfo_content += f'  <title>{title}</title>\n'
            nfo_content += f'  <season>{season}</season>\n'
            nfo_content += f'  <episode>{episode}</episode>\n'
            if release_date or year:
                date_to_use = release_date if release_date else f"{year}-01-01"
                nfo_content += f'  <aired>{date_to_use}</aired>\n'
            nfo_content += '</episodedetails>\n'
            
            try:
                with open(nfo_path, 'w', encoding='utf-8') as f:
                    f.write(nfo_content)
                log(f"[NFO] Created episode NFO: {nfo_path}")
            except Exception as e:
                log(f"[ERROR] Could not create NFO file: {e}")
    else:
        # Movie NFO
        nfo_path = target_folder / f"{title} ({year}).nfo"
        
        nfo_content = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        nfo_content += '<movie>\n'
        nfo_content += f'  <title>{title}</title>\n'
        if year:
            nfo_content += f'  <year>{year}</year>\n'
        if release_date or year:
            date_to_use = release_date if release_date else f"{year}-01-01"
            nfo_content += f'  <premiered>{date_to_use}</premiered>\n'
            nfo_content += f'  <releasedate>{date_to_use}</releasedate>\n'
        nfo_content += '</movie>\n'
        
        try:
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(nfo_content)
            log(f"[NFO] Created movie NFO: {nfo_path}")
        except Exception as e:
            log(f"[ERROR] Could not create NFO file: {e}")

def extract_release_date(info: dict, filepath: Path) -> str:
    """Try to extract release date from guessit info or use current date."""
    # Check if guessit found a date
    date_val = info.get('date')
    if date_val:
        return str(date_val)
    
    # Fallback to current date
    return datetime.now().strftime('%Y-%m-%d')

def find_matching_subtitles(media_file: Path) -> list[Path]:
    """Find subtitle files that match the media file."""
    subtitles = []
    media_stem = media_file.stem
    parent_dir = media_file.parent
    
    # Look for subtitles with the same base name
    for sub_ext in SUBTITLE_EXTENSIONS:
        # Direct match: movie.srt
        direct_match = parent_dir / f"{media_stem}{sub_ext}"
        if direct_match.exists():
            subtitles.append(direct_match)
        
        # Language-tagged subtitles: movie.en.srt, movie.eng.srt
        for sub_file in parent_dir.glob(f"{media_stem}.*{sub_ext}"):
            if sub_file not in subtitles:
                subtitles.append(sub_file)
    
    return subtitles

def process_file(filepath: Path):
    """Parse filename and create appropriate symlink."""
    if filepath.suffix.lower() not in MEDIA_EXTENSIONS:
        log(f"[SKIP] Unsupported file type: {filepath}")
        return

    cleaned_name = clean_filename(filepath.name)
    info = guessit(cleaned_name)
    
    # Extract release date
    release_date = extract_release_date(info, filepath)

    if info.get("type") == "movie":
        title = info.get("title")
        year = info.get("year", "")
        if not title:
            log(f"[SKIP] No title found: {filepath}")
            return
        target_folder = DEST_BASE / "movies" / f"{title} ({year})"
        target_name = f"{title} ({year}){filepath.suffix}"
        subtitle_base = f"{title} ({year})"
        
        # Create NFO file for movie
        create_nfo_file(target_folder, title, year=year, release_date=release_date)

    elif info.get("type") == "episode" or filepath.parent != SOURCE:
        # Use parent folder name as the show title, not the episode title
        title = filepath.parent.name
        # Clean the folder name from release tags too
        title = clean_filename(title)
        # Remove common patterns like "S01 - EP(01-09)" from folder names
        title = re.sub(r'\s*S\d{2}\s*-\s*EP\([^)]+\).*

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
        subtitle_base = f"{title} - S{season:02}{episode_str}"
        
        # Create NFO file for episode
        year = info.get("year")
        create_nfo_file(target_folder, title, year=year, season=season, episode_list=episode_list, release_date=release_date)

    else:
        log(f"[SKIP] Unknown media type: {filepath}")
        return

    target_path = target_folder / target_name
    make_symlink(filepath, target_path)
    
    # Process matching subtitle files
    subtitles = find_matching_subtitles(filepath)
    for sub_file in subtitles:
        # Extract language code if present (e.g., .en.srt, .eng.srt)
        sub_stem = sub_file.stem
        media_stem = filepath.stem
        
        if sub_stem == media_stem:
            # Direct match: keep same extension
            sub_target_name = f"{subtitle_base}{sub_file.suffix}"
        else:
            # Language-tagged: extract the language part
            lang_part = sub_stem.replace(media_stem, '').lstrip('.')
            sub_target_name = f"{subtitle_base}.{lang_part}{sub_file.suffix}"
        
        sub_target_path = target_folder / sub_target_name
        make_symlink(sub_file, sub_target_path)

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
        time.sleep(POLL_INTERVAL), '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*\(\d{4}\).*

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
        subtitle_base = f"{title} - S{season:02}{episode_str}"
        
        # Create NFO file for episode
        year = info.get("year")
        create_nfo_file(target_folder, title, year=year, season=season, episode_list=episode_list, release_date=release_date)

    else:
        log(f"[SKIP] Unknown media type: {filepath}")
        return

    target_path = target_folder / target_name
    make_symlink(filepath, target_path)
    
    # Process matching subtitle files
    subtitles = find_matching_subtitles(filepath)
    for sub_file in subtitles:
        # Extract language code if present (e.g., .en.srt, .eng.srt)
        sub_stem = sub_file.stem
        media_stem = filepath.stem
        
        if sub_stem == media_stem:
            # Direct match: keep same extension
            sub_target_name = f"{subtitle_base}{sub_file.suffix}"
        else:
            # Language-tagged: extract the language part
            lang_part = sub_stem.replace(media_stem, '').lstrip('.')
            sub_target_name = f"{subtitle_base}.{lang_part}{sub_file.suffix}"
        
        sub_target_path = target_folder / sub_target_name
        make_symlink(sub_file, sub_target_path)

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
        time.sleep(POLL_INTERVAL), '', title)  # Remove year and everything after
        title = title.strip()
        
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
        subtitle_base = f"{title} - S{season:02}{episode_str}"
        
        # Create NFO file for episode
        year = info.get("year")
        create_nfo_file(target_folder, title, year=year, season=season, episode_list=episode_list, release_date=release_date)

    else:
        log(f"[SKIP] Unknown media type: {filepath}")
        return

    target_path = target_folder / target_name
    make_symlink(filepath, target_path)
    
    # Process matching subtitle files
    subtitles = find_matching_subtitles(filepath)
    for sub_file in subtitles:
        # Extract language code if present (e.g., .en.srt, .eng.srt)
        sub_stem = sub_file.stem
        media_stem = filepath.stem
        
        if sub_stem == media_stem:
            # Direct match: keep same extension
            sub_target_name = f"{subtitle_base}{sub_file.suffix}"
        else:
            # Language-tagged: extract the language part
            lang_part = sub_stem.replace(media_stem, '').lstrip('.')
            sub_target_name = f"{subtitle_base}.{lang_part}{sub_file.suffix}"
        
        sub_target_path = target_folder / sub_target_name
        make_symlink(sub_file, sub_target_path)

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

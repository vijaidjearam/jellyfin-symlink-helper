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
METADATA_EXTENSIONS = {'.nfo', '.jpg', '.jpeg', '.png', '.xml', '.txt'}

# === Helper Functions ===

def log(message: str):
    """Print log messages with a timestamp."""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)

def clean_filename(filename: str) -> str:
    """Strip common release tags like 'www.1TamilMV.moi - ' from the beginning of filenames."""
    cleaned = re.sub(r'^(?:\[\s*www\.[\w.-]+\s*\]|\(\s*www\.[\w.-]+\s*\)|www\.[\w.-]+)\s*-\s*', '', filename, flags=re.IGNORECASE)
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

    elif info.get("type") == "episode":
        # Determine the show title
        if filepath.parent == SOURCE:
            # File is in root SOURCE directory, use guessit title from filename
            title = info.get("title")
            if not title:
                log(f"[SKIP] No title found in filename: {filepath}")
                return
        else:
            # File is in a subdirectory, use parent folder name as the show title
            title = filepath.parent.name
            # Clean the folder name from release tags too
            title = clean_filename(title)
            # Remove common patterns like "S01 - EP(01-09)" from folder names
            title = re.sub(r'\s*S\d{2}\s*-\s*EP\([^)]+\).*$', '', title, flags=re.IGNORECASE)
            title = re.sub(r'\s*\(\d{4}\).*$', '', title)
            title = title.strip()
            
            # Skip if the cleaned title is empty
            if not title:
                log(f"[SKIP] Invalid show title derived from folder: {filepath}")
                return
        
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


def cleanup_orphaned_content(dest_path: Path):
    """
    Complete cleanup function that:
    1. Removes broken symlinks (pointing to non-existent source files)
    2. Removes orphaned metadata files (NFO, images) when no valid media exists
    3. Removes empty directories from bottom-up
    """
    log(f"[INFO] Starting cleanup scan in: {dest_path}")
    
    broken_symlinks_removed = 0
    orphaned_files_removed = 0
    empty_dirs_removed = 0
    
    # === PASS 1: Remove all broken symlinks ===
    log(f"[INFO] Pass 1: Checking for broken symlinks...")
    for root, _, files in os.walk(dest_path):
        for filename in files:
            full_path = Path(root) / filename
            try:
                # Check if it's a symlink and if the target exists
                if full_path.is_symlink():
                    # Use exists() which returns False for broken symlinks
                    if not full_path.exists():
                        target = os.readlink(full_path)
                        log(f"[CLEAN] Removing broken symlink: {full_path} -> {target}")
                        full_path.unlink()
                        broken_symlinks_removed += 1
            except Exception as e:
                log(f"[ERROR] Error checking {full_path}: {e}")
    
    log(f"[INFO] Pass 1 complete: Removed {broken_symlinks_removed} broken symlinks")
    
    # === PASS 2: Remove orphaned metadata files ===
    # NFO files and other metadata should be removed if there's no valid media in the same directory
    log(f"[INFO] Pass 2: Checking for orphaned metadata files...")
    
    for root, _, _ in os.walk(dest_path):
        dir_path = Path(root)
        
        try:
            # Get fresh list of items in directory
            current_items = list(dir_path.iterdir())
        except Exception as e:
            log(f"[ERROR] Cannot read directory {dir_path}: {e}")
            continue
        
        # Check if any valid media symlinks exist in this directory
        has_valid_media = False
        for item in current_items:
            if item.is_symlink() and item.exists():
                # Check if it's a media or subtitle file
                if item.suffix.lower() in MEDIA_EXTENSIONS or item.suffix.lower() in SUBTITLE_EXTENSIONS:
                    has_valid_media = True
                    break
        
        # If no valid media exists, remove all metadata files (not symlinks)
        if not has_valid_media:
            for item in current_items:
                # Only remove regular files (not symlinks, not directories)
                if item.is_file() and not item.is_symlink():
                    if item.suffix.lower() in METADATA_EXTENSIONS:
                        try:
                            log(f"[CLEAN] Removing orphaned metadata: {item}")
                            item.unlink()
                            orphaned_files_removed += 1
                        except Exception as e:
                            log(f"[ERROR] Could not remove {item}: {e}")
    
    log(f"[INFO] Pass 2 complete: Removed {orphaned_files_removed} orphaned metadata files")
    
    # === PASS 3: Remove empty directories (bottom-up) ===
    log(f"[INFO] Pass 3: Removing empty directories...")
    
    # We need multiple passes because removing a directory may make its parent empty
    max_passes = 10  # Prevent infinite loops
    for pass_num in range(max_passes):
        dirs_removed_this_pass = 0
        
        # Walk bottom-up to handle nested empty directories
        for root, dirs, files in os.walk(dest_path, topdown=False):
            dir_path = Path(root)
            
            # Don't delete the base destination directories
            if dir_path == dest_path:
                continue
            if dir_path == dest_path / "movies":
                continue
            if dir_path == dest_path / "tvshows":
                continue
            
            try:
                # Check if directory is empty
                if not any(dir_path.iterdir()):
                    log(f"[CLEAN] Removing empty directory: {dir_path}")
                    dir_path.rmdir()
                    empty_dirs_removed += 1
                    dirs_removed_this_pass += 1
            except Exception as e:
                log(f"[ERROR] Could not remove directory {dir_path}: {e}")
        
        # If no directories were removed this pass, we're done
        if dirs_removed_this_pass == 0:
            break
    
    log(f"[INFO] Pass 3 complete: Removed {empty_dirs_removed} empty directories")
    log(f"[INFO] Cleanup finished: {broken_symlinks_removed} symlinks, {orphaned_files_removed} metadata files, {empty_dirs_removed} directories removed")


def main():
    start_time = time.time()
    log(f"[INFO] Starting scan cycle")
    log(f"[INFO] Source: {SOURCE}")
    log(f"[INFO] Destination: {DEST_BASE}")
    
    # Run cleanup first
    cleanup_orphaned_content(DEST_BASE)
    
    # Process all files from source
    log(f"[INFO] Processing files from source...")
    files_processed = 0
    for dirpath, _, filenames in os.walk(SOURCE):
        for filename in filenames:
            full_path = Path(dirpath) / filename
            if full_path.is_file():
                process_file(full_path)
                files_processed += 1

    end_time = time.time()
    duration = end_time - start_time
    log(f"[DONE] Scan completed in {duration:.2f} seconds. Processed {files_processed} files.")


if __name__ == "__main__":
    while True:
        main()
        log(f"[INFO] Sleeping for {POLL_INTERVAL} seconds before next scan.")
        time.sleep(POLL_INTERVAL)

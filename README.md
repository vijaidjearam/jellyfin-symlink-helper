# Jellyfin Symlink Helper

This project provides a Dockerized Python script to:
- Rename media files using [guessit](https://github.com/guessit-io/guessit)
- Create symbolic links in a structure compatible with [Jellyfin](https://jellyfin.org/)
- Clean up broken symlinks automatically
- Only process newly added or recently modified files

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/vijaidjearam/jellyfin-symlink-helper.git
cd jellyfin-symlink-helper
```

### 2. Set Up Environment Variables
Copy .env.example to .env and edit it with your actual paths:

```bash

cp .env.example .env
nano .env
```

Example:

```
SOURCE=/mnt/cloudmedia
DEST_BASE=/srv/jellyfin
MODIFIED_WITHIN_HOURS=24
```

### 3. Build the Docker Image

```bash
docker-compose build
```

### 4. Run the Script
```bash

docker-compose up
```

You can also run it manually without logs:

```bash
docker-compose run --rm symlink-processor
```

## 🔁 Automate with Cron
To run the script periodically:

```bash
crontab -e
```

Add a line like:

```bash
0 * * * * cd /path/to/jellyfin-symlink-helper && docker-compose run --rm symlink-processor >> /var/log/symlink_processor.log 2>&1
```


## 🛠 How It Works
- Files in **$SOURCE** modified within the last **$MODIFIED_WITHIN_HOURS** hours are scanned.

- Their names are parsed with **guessit**.

- Symlinks are created in **$DEST_BASE** following Jellyfin-compatible structure:

    - Movies: **/Movies/Title (Year)/Title (Year).ext**

    - Series: **/TV Shows/Show/Season 01/Show - S01E01.ext**

- Broken symlinks in **$DEST_BASE** are automatically deleted.

## 📂 Volume Permissions

Ensure your Docker user has read access to **$SOURCE** and write access to **$DEST_BASE**.

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
DEST_BASE=/Data
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

    - Tv Shows: **/TV Shows/Show/Season 01/Show - S01E01.ext**

- Broken symlinks in **$DEST_BASE** are automatically deleted.

## 📂 Volume Permissions

Ensure your Docker user has read access to **$SOURCE** and write access to **$DEST_BASE**.

# 🧩 Jellyfin Symlink Helper Docker container from DockerHub

This project sets up a Docker container using the [`vijaidj/jellyfin-symlink-helper`](https://hub.docker.com/r/vijaidj/jellyfin-symlink-helper) image to process media files and create symbolic links, helping Jellyfin better index and organize your media library.

---

## 📦 Overview

The container watches a specified **source** directory for media files and creates symbolic links in a structured format inside a **destination** directory. These symlinks are designed to be recognized and parsed correctly by [Jellyfin](https://jellyfin.org/).

---

## 🐳 Docker Compose Setup

### `docker-compose.yml`

```yaml
version: '3.8'

services:
  symlink-processor:
    image: vijaidj/jellyfin-symlink-helper:latest
    container_name: symlink-processor
    environment:
      - SOURCE=${SOURCE}
      - DEST_BASE=${DEST_BASE}
    volumes:
      - ${SOURCE}:${SOURCE}:ro
      - /srv/jellyfin:${DEST_BASE}
    restart: unless-stopped
```

---

## 🌱 Environment Variables

Create a `.env` file in the same directory as your `docker-compose.yml` and define the following variables:

| Variable    | Description                             | Example              |
|-------------|-----------------------------------------|----------------------|
| `SOURCE`    | Path to the source media directory      | `/srv/downloads`     |
| `DEST_BASE` | Path to the base destination directory  | `/media`             |

### Example `.env` file

```env
SOURCE=/srv/downloads
DEST_BASE=/media
```

> 💡 **Note**: Ensure the Jellyfin container has access to the `DEST_BASE` path for proper indexing.

---

## ▶️ Usage

1. Clone or create this repository.
2. Create a `.env` file as shown above.
3. Start the container with:

   ```bash
   docker-compose up -d
   ```

4. The container will:
   - Scan the `SOURCE` directory for media files.
   - Generate symlinks inside `DEST_BASE`.
   - Update automatically when restarted.

5. Point your Jellyfin library to the `DEST_BASE` path.

---

## ♻️ Restart Policy

The service uses the following restart policy:

```yaml
restart: unless-stopped
```

This means the container will:

- Restart automatically if it crashes or the system reboots.
- Stay stopped if manually stopped with `docker stop`.

---

## 🛠️ Troubleshooting

- **No symlinks created?** Double-check your `.env` paths and make sure the source directory is not empty.
- **Permissions issue?** Ensure Docker has read access to `SOURCE` and write access to `DEST_BASE`.
- **Still stuck?** Review logs with:

  ```bash
  docker logs symlink-processor
  ```

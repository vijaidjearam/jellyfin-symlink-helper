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

---

# 🧩 Jellyfin Symlink Helper Docker container from DockerHub

This project deploys a Docker container using the [`vijaidj/jellyfin-symlink-helper`](https://hub.docker.com/r/vijaidj/jellyfin-symlink-helper) image. It scans a source directory for media files and creates symbolic links in a destination directory, enabling Jellyfin to correctly recognize and organize the content.

---

## 📦 Overview

This helper tool is useful when downloaded or unmanaged media needs to be cleaned up, renamed, and symlinked into a structured format for Jellyfin to consume easily.

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
      - ${DEST_BASE}:${DEST_BASE}
    restart: unless-stopped
```

---

## 🌱 Environment Variables

Create a `.env` file in the same directory as your `docker-compose.yml` and define the following variables:

| Variable    | Description                             | Example              |
|-------------|-----------------------------------------|----------------------|
| `SOURCE`    | Path to the source media directory      | `/srv/downloads`     |
| `DEST_BASE` | Path to the destination directory       | `/srv/jellyfin`      |

### Example `.env` file

```env
SOURCE=/srv/downloads
DEST_BASE=/srv/jellyfin
```

> 🔒 **Note**: The container mounts both paths. Ensure appropriate permissions are set so the container can read from `SOURCE` and write to `DEST_BASE`.

---

## ▶️ Usage

1. Create your `.env` file as described above.
2. Deploy the container:

   ```bash
   docker-compose up -d
   ```

3. The symlink helper will:
   - Scan media files in the source folder.
   - Parse names and generate symlinks.
   - Place symlinks in the destination folder for Jellyfin to detect.

---

## ♻️ Restart Policy

The container uses the following restart policy:

```yaml
restart: unless-stopped
```

This ensures the container restarts automatically on system reboot or crash, unless manually stopped.

---

## 🛠️ Troubleshooting

- **No symlinks created?**
  - Ensure your source folder is not empty.
  - Validate file naming for compatibility.
- **Permission issues?**
  - Check that Docker can read from `SOURCE` and write to `DEST_BASE`.
- **Logs for diagnosis:**

  ```bash
  docker logs symlink-processor
  ```
# Run rename_and_symlink.py Script with guessit via Cron on Ubuntu 24.04 directly on the host instead of containers

## 🐍 Step 1: Set up a Virtual Environment

```bash
python3 -m venv /opt/venvs/guessit
source /opt/venvs/guessit/bin/activate
pip install guessit
```

This ensures you can import `guessit` in scripts without breaking your system Python.

## 📝 Step 2: Create a Shell Wrapper Script

Create a script to activate the environment and run your Python code.

```bash
sudo nano /scripts/run_process.sh
```

Paste this:

```bash
#!/bin/bash
source /opt/venvs/guessit/bin/activate
python /scripts/rename_and_symlink.py >> /scripts/process.log 2>&1
```

Make it executable:

```bash
chmod +x /scripts/run_process.sh
```

## 🕐 Step 3: Schedule with Cron

Edit your crontab:

```bash
crontab -e
```

Add this line to run the script every hour:

```cron
0 * * * * /scripts/run_process.sh
```

## ✅ Step 4: Verify Execution

Check if the cron job is installed:

```bash
crontab -l
```

Monitor the log file to confirm your script is running:

```bash
tail -f /scripts/process.log
```

## ⚠️ Additional Tips

- **Always use absolute paths** in scripts called from cron.
- **Cron has a minimal environment**, so set any required `PATH`, environment variables, or dependencies inside your wrapper script.
- Don’t use `pipx` for libraries used in scripts — it's intended for CLI tools.

---

By using virtual environments and a shell wrapper, you ensure your scripts run reliably and safely with modern Python package management constraints on Ubuntu 24.04.




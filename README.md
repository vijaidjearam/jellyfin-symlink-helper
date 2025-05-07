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
git clone https://github.com/yourusername/jellyfin-symlink-helper.git
cd jellyfin-symlink-helper

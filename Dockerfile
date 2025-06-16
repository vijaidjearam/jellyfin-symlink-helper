FROM python:3.9-slim

WORKDIR /usr/local/bin

# Install guessit and cron
RUN apt-get update && \
    apt-get install -y cron && \
    pip install --no-cache-dir guessit && \
    rm -rf /var/lib/apt/lists/*

COPY rename_and_symlink.py .

# Copy cron job definition
COPY cronjob /etc/cron.d/symlink-cron

# Apply cron job and give proper permissions
RUN chmod 0644 /etc/cron.d/symlink-cron && \
    crontab /etc/cron.d/symlink-cron

# Start cron and script
CMD ["cron", "-f"]

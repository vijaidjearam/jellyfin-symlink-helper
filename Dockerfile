FROM python:3.9-slim

WORKDIR /usr/local/bin

# Install guessit and cron
RUN apt-get update && apt-get install -y cron && \
    pip install --no-cache-dir guessit && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy your script
COPY rename_and_symlink.py .

# Copy cron job definition
COPY cronjob /etc/cron.d/symlink-cron
RUN chmod 0644 /etc/cron.d/symlink-cron

# Copy and set entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Use entrypoint script to start cron and script
CMD ["./entrypoint.sh"]

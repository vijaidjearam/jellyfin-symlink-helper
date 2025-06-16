#!/bin/bash

# Register the cron job
crontab /etc/cron.d/symlink-cron

# Start cron service
cron

# Keep container alive with log
touch /var/log/cron.log
tail -f /var/log/cron.log

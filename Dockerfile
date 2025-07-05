FROM python:3.9-slim

WORKDIR /usr/local/bin

# Install guessit
RUN pip install --no-cache-dir guessit

# Copy script
COPY rename_and_symlink.py .

CMD ["python3", "rename_and_symlink.py"]

# Default command to run bash shell and keep container running
# CMD ["sh"]

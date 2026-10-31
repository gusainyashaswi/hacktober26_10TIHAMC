# syntax=docker/dockerfile:1
FROM python:3.11.9-slim-bookworm

# Create a non-root user and group named 'runner'
RUN groupadd --gid 10001 runner \
 && useradd --uid 10001 --gid runner --shell /bin/sh --create-home runner

# Set a scratch working directory owned by runner
WORKDIR /work
RUN chown runner:runner /work

# Install only the pinned test dependency; no repository source is copied
RUN pip install --no-cache-dir pytest==8.3.5

# Drop privileges
USER runner

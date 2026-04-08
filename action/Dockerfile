FROM python:3.12-slim

LABEL maintainer="archlens" \
      description="ArchLens - Architecture Context Layer for Coding Agents"

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app
WORKDIR /app

# Install archlens with action dependencies
RUN pip install --no-cache-dir -e ".[action]"

ENTRYPOINT ["python", "-m", "action.entrypoint"]

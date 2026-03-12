# Use a lightweight Python image
FROM python:3.11-slim

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# 1. Install system dependencies for Postgres
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. Install dependencies using uv
# We copy uv.lock and pyproject.toml if you have them, 
# or just requirements.txt if that's what you generated.
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache -r pyproject.toml

# 3. Copy the rest of the code
COPY ./src ./src

# Set pathing
ENV PYTHONPATH=/app
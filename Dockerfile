# Use slim Python base image
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpoppler-cpp-dev \
    libjpeg-dev \
    zlib1g-dev \
    poppler-utils \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Pre-copy and install Python dependencies to cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the code after installing dependencies (for caching)
COPY main.py .
COPY input ./input

# Ensure output folder exists
RUN mkdir -p /app/output

# Default run command
CMD ["python", "main.py"]

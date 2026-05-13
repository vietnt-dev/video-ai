FROM python:3.11-slim

# Install system dependencies (FFmpeg required by MoviePy)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-liberation \
    fonts-dejavu-core \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Tải font Roboto hỗ trợ tiếng Việt
RUN python download_fonts.py

RUN mkdir -p outputs assets/audio assets/video assets/music assets/fonts

EXPOSE 8000

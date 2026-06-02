# ── Dockerfile for Kokoro TTS RunPod Serverless ──────────────────────────
# Deploy as Custom Deployment on RunPod
# Recommended GPU: RTX 4090 (24GB) or your RTX 5090
# Build: docker build -t yourdockerhub/kokoro-runpod:latest .
# Push:  docker push yourdockerhub/kokoro-runpod:latest

FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python deps
RUN pip install --no-cache-dir \
    runpod \
    kokoro>=0.9.2 \
    soundfile \
    numpy \
    scipy \
    torch \
    --extra-index-url https://download.pytorch.org/whl/cu121

# Copy handler
WORKDIR /app
COPY handler.py .

# Pre-download Kokoro model weights at build time (saves cold start)
RUN python -c "
from kokoro import KPipeline
print('Pre-loading American English pipeline...')
p = KPipeline(lang_code='a')
print('Pre-loading British English pipeline...')
p2 = KPipeline(lang_code='b')
print('Kokoro models cached.')
"

CMD ["python", "-u", "handler.py"]

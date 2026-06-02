FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir runpod kokoro>=0.9.2 soundfile numpy scipy torch --extra-index-url https://download.pytorch.org/whl/cu121

WORKDIR /app
COPY handler.py .

RUN python -c "from kokoro import KPipeline; print('Pre-loading...'); KPipeline(lang_code='a'); KPipeline(lang_code='b'); print('Done.')"

CMD ["python", "-u", "handler.py"]

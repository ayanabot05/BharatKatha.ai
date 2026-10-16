FROM python:3.11-slim-bookworm
WORKDIR /app/backend
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fontconfig && rm -rf /var/lib/apt/lists/*
COPY backend/requirements-cloud.txt ./
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY backend/ ./
ENV PYTHONUNBUFFERED=1 APP_ENV=production FFMPEG_BINARY=/usr/bin/ffmpeg
RUN useradd --create-home renderer && chown -R renderer:renderer /app
USER renderer
CMD ["python", "cloud_render_worker.py"]

FROM python:3.11-slim-bookworm
WORKDIR /app
RUN pip install --no-cache-dir 'piper-tts[http]==1.8.0' 'google-cloud-storage>=3,<4'
COPY deploy/voice-piper/entrypoint.py ./entrypoint.py
ENV PYTHONUNBUFFERED=1 PORT=8080
RUN useradd --create-home --gid voice voice && chown -R voice:voice /app
USER voice
EXPOSE 8080
CMD ["python", "entrypoint.py"]

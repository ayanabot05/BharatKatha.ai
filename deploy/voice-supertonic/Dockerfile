FROM python:3.11-slim-bookworm
WORKDIR /app
RUN pip install --no-cache-dir 'supertonic==1.3.1' 'fastapi==0.110.1' 'starlette==0.37.2' 'uvicorn==0.25.0' 'google-cloud-storage>=3,<4' 'soundfile>=0.12,<1'
COPY deploy/voice-supertonic/app.py ./app.py
ENV PYTHONUNBUFFERED=1 PORT=8080
RUN useradd --create-home voice && chown -R voice:voice /app
USER voice
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]

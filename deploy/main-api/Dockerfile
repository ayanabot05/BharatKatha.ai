FROM python:3.11-slim-bookworm

WORKDIR /app/backend
COPY backend/requirements-cloud.txt ./
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY backend/ ./

ENV PYTHONUNBUFFERED=1 APP_ENV=production PORT=8080
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8080

# Cloud Run supplies PORT. The API has one worker until all in-process jobs have
# moved to durable cloud execution; do not scale out this image prematurely.
CMD ["sh", "-c", "exec python -m uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]

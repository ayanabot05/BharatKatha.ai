FROM python:3.13-slim-bookworm
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]

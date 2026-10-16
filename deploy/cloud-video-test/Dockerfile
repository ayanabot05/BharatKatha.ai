FROM python:3.13-slim-bookworm
WORKDIR /app/backend
COPY backend/requirements-cloud.txt ./
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY backend/ ./
ENV PYTHONUNBUFFERED=1
CMD ["python", "cloud_video_test.py"]

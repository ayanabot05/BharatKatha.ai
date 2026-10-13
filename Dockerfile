FROM node:22-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
RUN npm ci
COPY frontend/ ./
ENV REACT_APP_BACKEND_URL=/
RUN npm run build

FROM python:3.13-slim-bookworm
WORKDIR /app/backend
COPY backend/requirements-cloud.txt ./
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY backend/ ./
COPY --from=frontend /src/frontend/build /app/frontend/build
ENV SERVE_FRONTEND=true FRONTEND_DIST=/app/frontend/build PYTHONUNBUFFERED=1
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

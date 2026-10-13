FROM python:3.12-slim
WORKDIR /app
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir scikit-learn==1.9.1 numpy==2.4.6 requests==2.34.2 google-cloud-storage==3.4.1
COPY fetch_wili.py cloud_train.py ./
CMD ["python", "cloud_train.py"]

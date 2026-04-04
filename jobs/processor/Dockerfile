FROM python:3.12-slim
WORKDIR /app
COPY jobs/processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared ./shared
COPY config ./config
COPY jobs/processor ./jobs/processor
CMD ["python", "jobs/processor/main.py"]

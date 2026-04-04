FROM python:3.12-slim
WORKDIR /app
COPY jobs/notifier/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared ./shared
COPY config ./config
COPY jobs/notifier ./jobs/notifier
CMD ["python", "jobs/notifier/main.py"]

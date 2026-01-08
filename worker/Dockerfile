FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY worker /app/worker
COPY packages /app/packages

CMD ["uvicorn", "worker.main:app", "--host", "0.0.0.0", "--port", "8080"]
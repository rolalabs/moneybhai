# worker/main.py
from fastapi import FastAPI, Request
import json
import time

app = FastAPI()

@app.post("/tasks/process")
async def process_task(request: Request):
    payload = await request.json()

    job_id = payload.get("job_id")

    print(f"Processing job {job_id}")

    # simulate long work
    time.sleep(5)

    # TODO: update DB here

    return {"status": "done", "job_id": job_id}

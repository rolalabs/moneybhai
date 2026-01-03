import json
import base64

from google.cloud import tasks_v2
from src.core.connectors import ENV_SETTINGS

def enqueue_worker_task(payload: dict):
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(
        "rola-labs",
        "asia-south1",
        "expense-workers"
    )

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{ENV_SETTINGS.WORKER_CLOUD_RUN_URL}/tasks/process",
            "headers": {
                "Content-Type": "application/json"
            },
            "oidc_token": {
                "service_account_email": "rola-labs@appspot.gserviceaccount.com"
            },
            "body": base64.b64encode(
                json.dumps(payload).encode("utf-8")
            )
        }
    }

    response = client.create_task(parent=parent, task=task)
    return response.name

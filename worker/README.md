
Command to invoke the endpoint
curl -X POST \
  https://mb-sync-worker-319702317581.asia-south1.run.app/tasks/process \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "laudas"}'
{"status":"done","job_id":"laudas"}%
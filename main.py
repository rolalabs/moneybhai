import os
import json
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_redoc_html
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from src.api import router
from src.utils.log import setup_logger
# from app.ws import chat

logger = setup_logger(__name__)

app = FastAPI(
    title="MoneyBhai API",
    version="1.0.0", 
    docs_url="/docs",
    redoc_url=None,
    openapi_version="3.0.2"
)

# Middleware to log all incoming requests and outgoing responses
@app.middleware("http")
async def log_requests_responses(request: Request, call_next):
    # Log incoming request
    start_time = time.time()
    
    # Prepare request log structure
    request_log = {
        "type": "REQUEST",
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "headers": dict(request.headers),
        "client": f"{request.client.host}:{request.client.port}" if request.client else None,
    }
    
    # Get request body
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            # Store body so it can be read by the endpoint
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
            
            # Try to parse as JSON
            try:
                body_json = json.loads(body.decode())
                request_log["body"] = body_json
            except:
                request_log["body"] = body.decode()
        except Exception as e:
            request_log["body_error"] = str(e)
    
    logger.info(json.dumps(request_log, indent=2))
    
    # Process request and get response
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Prepare response log structure
    response_log = {
        "type": "RESPONSE",
        "status_code": response.status_code,
        "path": request.url.path,
        "processing_time_seconds": round(process_time, 3),
        "headers": dict(response.headers),
    }
    
    logger.info(json.dumps(response_log, indent=2))
    
    return response

app.include_router(router, prefix="/api")
# app.include_router(chat.router, prefix="/ws")

origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] to allow all (not recommended for prod)
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, PUT, etc.
    allow_headers=["*"],
)


security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "money")
    correct_password = secrets.compare_digest(credentials.password, "bhai")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/", tags=["Health"])
def health_check():
    return JSONResponse(content={"status": "ok"}, status_code=200)

@app.get("/health", tags=["Health"])
def root_health_check():
    return JSONResponse(content={"status": "ok"}, status_code=200)



@app.get("/redoc", include_in_schema=False)
async def redoc_docs(user: str = Depends(verify_credentials)):
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title="MoneyBhai API Docs"
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
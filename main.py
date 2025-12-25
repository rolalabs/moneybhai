import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_redoc_html
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from src.api import router
# from app.ws import chat

app = FastAPI(
    title="MoneyBhai API",
    version="1.0.0", 
    docs_url="/docs",
    redoc_url=None,
    openapi_version="3.0.2"
)
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
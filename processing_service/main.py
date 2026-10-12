from fastapi import FastAPI

app = FastAPI(title="Processing Service")


@app.get("/")
def root():
    return {
        "service": "processing-service",
        "message": "Processing Service is running",
    }


@app.get("/health")
def health():
    return {
        "service": "processing-service",
        "status": "ok",
    }

from fastapi import FastAPI

app = FastAPI(title="Resource Service")


@app.get("/")
def root():
    return {
        "service": "resource-service",
        "message": "Resource Service is running",
    }


@app.get("/health")
def health():
    return {
        "service": "resource-service",
        "status": "ok",
    }

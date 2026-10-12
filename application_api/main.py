from fastapi import FastAPI

app = FastAPI(title="Application API")


@app.get("/")
def root():
    return {
        "service": "application-api",
        "message": "Application API is running",
    }


@app.get("/health")
def health():
    return {
        "service": "application-api",
        "status": "ok",
    }

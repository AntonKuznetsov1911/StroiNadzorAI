from fastapi import FastAPI

app = FastAPI(title="Placeholder API")


@app.get("/api/health")
def health():
    return {"status": "ok"}

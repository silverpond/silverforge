"""HTTP API server for Factory."""
from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
def hello() -> dict[str, str]:
    """Simple hello endpoint."""
    return {"message": "hello"}

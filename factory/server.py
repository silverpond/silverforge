"""FastAPI server for Silverpond Factory."""
from fastapi import FastAPI

app = FastAPI(title="Silverpond Factory", version="0.1.0")


@app.get("/hello")
def hello() -> dict:
    """Say hello from Silverpond Factory."""
    return {"message": "Hello from Silverpond Factory"}

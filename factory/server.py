"""
Silverpond Factory HTTP API server.
"""
from fastapi import FastAPI

app = FastAPI(title="Silverpond Factory API")


@app.get("/hello")
def hello():
    """Return a simple hello message."""
    return {"message": "Hello, Silverpond Factory!"}

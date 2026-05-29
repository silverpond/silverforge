"""
Silverforge Factory HTTP server.

Provides REST API endpoints for the factory.
"""
from fastapi import FastAPI

app = FastAPI(title="Silverforge Factory", version="0.1.0")


@app.get("/hello")
def hello():
    """Hello endpoint."""
    return {"message": "Hello from Silverpond Factory"}

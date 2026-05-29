"""
HTTP server for Silverpond Factory.
"""
from fastapi import FastAPI

app = FastAPI(title="Silverpond Factory")


@app.get("/hello")
def hello():
    """Simple hello endpoint."""
    return {"message": "Hello from Silverpond Factory"}

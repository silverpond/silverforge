"""
HTTP API server for Silverpond Factory.
"""
from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
def hello():
    """Return a greeting."""
    return {"message": "Hello, World!"}

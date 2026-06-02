"""FastAPI application for Silverforge Factory."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
def hello() -> dict:
    """Hello endpoint."""
    return {"message": "Hello, World!"}

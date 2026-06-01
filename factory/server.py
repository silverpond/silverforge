"""
HTTP API server for Silverpond Factory.
"""
from fastapi import FastAPI
from pydantic import BaseModel


class HelloResponse(BaseModel):
    """Response model for the /hello endpoint."""
    message: str


app = FastAPI()


@app.get("/hello", response_model=HelloResponse)
def hello() -> HelloResponse:
    """Return a greeting."""
    return HelloResponse(message="Hello, World!")

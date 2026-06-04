"""FastAPI server for Silverforge Factory."""
from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
def hello():
    """Hello endpoint."""
    return {"message": "Hello from Silverforge Factory"}

"""FastAPI server for the Silverforge Factory."""
from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
def hello() -> dict[str, str]:
    """Return a hello message."""
    return {"message": "Hello, world!"}

"""FastAPI server for Silverpond Factory."""
from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
def hello():
    """Simple hello endpoint that returns a JSON response."""
    return {"message": "Hello, World!"}

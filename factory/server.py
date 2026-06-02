"""FastAPI server for Silverpond Factory."""
from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
def hello():
    """Return a simple hello greeting."""
    return {"message": "hello"}

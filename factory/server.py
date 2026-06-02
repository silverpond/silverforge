"""HTTP API server for Silverpond Factory."""
from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
def hello():
    """Hello endpoint that returns a JSON greeting."""
    return {"message": "Hello, Factory!"}

from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
def hello():
    """Return a hello message."""
    return {"message": "Hello from Silverpond Factory"}

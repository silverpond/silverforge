"""HTTP server for Silverpond Factory."""
from fastapi import FastAPI

app = FastAPI(title="Silverpond Factory")


@app.get("/hello")
def hello() -> dict[str, str]:
    """Simple hello endpoint."""
    return {"message": "Hello from Silverpond Factory"}

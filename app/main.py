"""Web layer: creates the FastAPI app and defines its routes (URLs)."""

from fastapi import FastAPI

app = FastAPI(title="Is This a Scam?")


@app.get("/")
def read_root() -> dict[str, str]:
    """Temporary hello-world route, to prove the app runs."""
    return {"message": "Is This a Scam? is running"}

"""Web layer: creates the FastAPI app and defines its routes (URLs)."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Folder this file lives in, so paths work no matter where the server is started from
APP_DIR = Path(__file__).parent

app = FastAPI(title="Is This a Scam?")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """The landing page."""
    return templates.TemplateResponse(request, "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    """Lets the hosting platform (and later, uptime monitoring) check the app is running."""
    return {"status": "ok"}

"""Web layer: creates the FastAPI app and defines its routes (URLs)."""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.analyser import MAX_MESSAGE_LENGTH, analyse_message, validate_message

# Folder this file lives in, so paths work no matter where the server is started from
APP_DIR = Path(__file__).parent

app = FastAPI(title="Is This a Scam?")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """The page with the paste box."""
    return templates.TemplateResponse(
        request, "index.html", {"max_length": MAX_MESSAGE_LENGTH}
    )


@app.post("/check", response_class=HTMLResponse)
def check(request: Request, message: Annotated[str, Form()] = "") -> HTMLResponse:
    """Check the pasted message and show the result on the same page.

    The message is never stored or logged.
    """
    context: dict[str, object] = {"max_length": MAX_MESSAGE_LENGTH, "message": message}

    error = validate_message(message)
    if error:
        context["error"] = error
        return templates.TemplateResponse(request, "index.html", context, status_code=400)

    context["result"] = analyse_message(message)
    return templates.TemplateResponse(request, "index.html", context)


@app.get("/health")
def health() -> dict[str, str]:
    """Lets the hosting platform (and later, uptime monitoring) check the app is running."""
    return {"status": "ok"}

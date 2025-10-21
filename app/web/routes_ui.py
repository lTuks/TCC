
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/web/templates")
router = APIRouter(prefix="/ui", tags=["ui"])

@router.get("", response_class=HTMLResponse)
async def ui_home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register", response_class=HTMLResponse)
async def ui_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.get("/editor", response_class=HTMLResponse)
async def ui_editor(request: Request):
    return templates.TemplateResponse("editor.html", {"request": request})

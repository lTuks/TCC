from fastapi import Request
from fastapi.responses import RedirectResponse

PUBLIC_PATHS = [
    "/ui", "/auth/login", "/auth/register", "/auth/logout",
    "/static", "/favicon.ico", "/.well-known",
]

COOKIE_NAME = "ar_jwt"

def _get_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth.split(" ", 1)[1]
    cookie = request.cookies.get(COOKIE_NAME)
    return cookie

async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # libera caminhos públicos
    if any(path == p or path.startswith(p) for p in PUBLIC_PATHS):
        return await call_next(request)

    token = _get_token(request)
    if not token:
        return RedirectResponse(url="/ui", status_code=307)

    return await call_next(request)

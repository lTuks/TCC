
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.auth.deps import get_db
from app.schemas.auth import RegisterIn, LoginIn, TokenOut
from app.auth.service import register_user, login_user

router = APIRouter(prefix="/auth", tags=["auth"])

def set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key="ar_jwt",
        value=token,
        httponly=True,
        samesite="Lax",
        secure=False,
        path="/",
        max_age=60 * 60 * 8,
    )

@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_db), response: Response = None):
    user = register_user(db, body.name, body.email, body.password)
    token = login_user(db, user.email, body.password)
    set_auth_cookie(response, token)
    return TokenOut(access_token=token)

@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db), response: Response = None):
    token = login_user(db, body.email, body.password)
    set_auth_cookie(response, token)
    return TokenOut(access_token=token)

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("ar_jwt", path="/")
    return {"ok": True}

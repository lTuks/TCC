
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.utils.security import hash_password, verify_password, create_access_token

def register_user(db: Session, name: str, email: str, password: str) -> User:
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    user = User(name=name, email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def login_user(db: Session, email: str, password: str) -> str:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    return create_access_token(str(user.id))

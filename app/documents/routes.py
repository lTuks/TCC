
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.deps import get_db, get_current_user
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentOut
from app.models.document import Document

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("", response_model=DocumentOut)
def create_document(body: DocumentCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = Document(user_id=user.id, title=body.title, content=body.content or "", language="pt-BR")
    db.add(doc); db.commit(); db.refresh(doc)
    return doc

@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = db.get(Document, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return doc

@router.put("/{doc_id}", response_model=DocumentOut)
def update_document(doc_id: int, body: DocumentUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = db.get(Document, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if body.title is not None:
        doc.title = body.title
    if body.content is not None:
        doc.content = body.content
    db.commit(); db.refresh(doc)
    return doc

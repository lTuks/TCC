from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.deps import get_db, get_current_user
from pdfminer.high_level import extract_text
import io
from app.models.tutor import TutorDocument
from app.models.user import User


router = APIRouter(prefix="/upload", tags=["upload"])

MAX_MB = 10

@router.post("/pdf-multi")
async def upload_pdf_multi(files: list[UploadFile] = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo PDF recebido.")

    full_text = ""
    count = 0

    for file in files:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail=f"Arquivo '{file.filename}' não é PDF.")

        data = await file.read()
        if len(data) > MAX_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"{file.filename} maior que {MAX_MB}MB.")

        try:
            text = extract_text(io.BytesIO(data)) or ""
        except Exception:
            text = ""

        if text.strip():
            full_text += f"\n\n--- [PDF: {file.filename}] ---\n\n" + text
            count += 1

    if not full_text.strip():
        raise HTTPException(status_code=422, detail="Nenhum texto pôde ser extraído.")

    title = "PDFs Importados"
    doc = TutorDocument(owner_id=user.id, title=title, content=full_text)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "ok": True,
        "count": count,
        "document_id": doc.id,
        "chars": len(full_text),
        "text": full_text,
    }

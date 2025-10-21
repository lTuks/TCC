from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.deps import get_db, get_current_user
from pdfminer.high_level import extract_text
import io
from app.models.document import Document

router = APIRouter(prefix="/upload", tags=["upload"])

MAX_MB = 10  # tamanho máximo do PDF (ajuste se quiser)

@router.post("/pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if file.content_type not in ("application/pdf",):
        raise HTTPException(status_code=400, detail="Envie um PDF (content-type application/pdf).")

    data = await file.read()
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Arquivo maior que {MAX_MB}MB.")

    try:
        text = extract_text(io.BytesIO(data)) or ""
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Falha ao extrair texto do PDF: {e}")

    title = (file.filename or "PDF sem nome").rsplit(".", 1)[0][:120]

    # Cria um Documento com o texto extraído
    doc = Document(user_id=user.id, title=title, content=text, language="pt-BR")
    db.add(doc); db.commit(); db.refresh(doc)

    return {
        "ok": True,
        "document_id": doc.id,
        "title": doc.title,
        "chars": len(text),
        "text": text,
    }

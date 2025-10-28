from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.deps import get_db, get_current_user
from pdfminer.high_level import extract_text
import io, re
from app.models.tutor import TutorDocument
from app.models.user import User


router = APIRouter(prefix="/upload", tags=["upload"])

MAX_MB = 10

def _clean_pdf_text(raw: str) -> str:
    if not raw:
        return ""

    raw = re.sub(r"^\s*---\s*\[PDF:[^\]]+\]\s*---\s*$", "", raw, flags=re.IGNORECASE | re.MULTILINE)
    raw = raw.replace("\x0c", "\n\n")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = re.sub(r"[ \t]{2,}", " ", raw)
    raw = "\n".join(line.strip() for line in raw.split("\n"))

    return raw.strip()

@router.post("/pdf-multi")
async def upload_pdf_multi(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo PDF recebido.")

    merged = []
    count = 0

    for f in files:
        if f.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail=f"Arquivo '{f.filename}' não é PDF.")
        data = await f.read()
        if len(data) > MAX_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"{f.filename} maior que {MAX_MB}MB.")

        try:
            raw = extract_text(io.BytesIO(data)) or ""
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Falha ao extrair texto de {f.filename}: {e}")

        cleaned = _clean_pdf_text(raw)
        if cleaned:
            merged.append(cleaned)
            count += 1

    if not merged:
        raise HTTPException(status_code=422, detail="Nenhum texto pôde ser extraído.")

    full_text = "\n\n".join(merged)

    doc = TutorDocument(owner_id=user.id, title="PDFs Importados", content=full_text)
    db.add(doc); db.commit(); db.refresh(doc)

    return {
        "ok": True,
        "count": count,
        "document_id": doc.id,
        "chars": len(full_text),
        "text": full_text,
    }
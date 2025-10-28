from fastapi import APIRouter, Request, UploadFile, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.auth.deps import get_db, get_current_user
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.tutor import TutorDocument, TutorChatMessage, StudyPlan, Quiz, QuizAttempt
from app.models.user import User
from app.tutor.study import create_study_plan_md, generate_quiz, grade_discursive_batch
from app.llm.llm_gateway import summarize_to_bullets
from markupsafe import Markup
import markdown
import json

router = APIRouter(prefix="/tutor", tags=["tutor"])
templates = Jinja2Templates(directory="app/web/templates")

def _extract_pdf(file: UploadFile) -> str:
    MAX_MB = 10
    data = file.file.read()
    if len(data) > MAX_MB * 1024 * 1024:
        return ""
    try:
        from pdfminer.high_level import extract_text
        import io
        return extract_text(io.BytesIO(data)) or ""
    except Exception:
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""

def _clean_text(s: str) -> str:
    import re
    s = s.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", s).strip()

def _get_doc_user_safe(db: Session, user_id: int, doc_id: int) -> TutorDocument | None:
    return db.query(TutorDocument).filter(
        TutorDocument.id == doc_id,
        TutorDocument.owner_id == user_id
    ).first()

@router.get("", response_class=HTMLResponse)
def tutor_home(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    docs = (db.query(TutorDocument)
              .filter(TutorDocument.owner_id == user.id)
              .order_by(TutorDocument.created_at.desc())
              .all())
    return templates.TemplateResponse("tutor/index.html", {"request": request, "docs": docs})

@router.post("/upload", response_class=HTMLResponse)
def upload(
    request: Request,
    title: str = Form(...),
    text: str = Form(""),
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content = text or ""
    if file and file.filename:
        if file.filename.lower().endswith(".pdf"):
            content += "\n" + _extract_pdf(file)
        else:
            content += "\n" + file.file.read().decode("utf-8", errors="ignore")
    content = _clean_text(content)
    if not content.strip():
        return RedirectResponse(url="/tutor", status_code=303)

    doc = TutorDocument(owner_id=user.id, title=title or "Sem Título", content=content)
    db.add(doc); db.commit(); db.refresh(doc)
    return RedirectResponse(url=f"/tutor/doc/{doc.id}", status_code=303)

@router.get("/doc/{doc_id}", response_class=HTMLResponse)
def doc_detail(request: Request, doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_doc_user_safe(db, user.id, doc_id)
    if not doc:
        return RedirectResponse(url="/tutor", status_code=303)

    summary = summarize_to_bullets(doc.content, bullets=10)

    quiz_stats = (
        db.query(
            Quiz.id.label("quiz_id"),
            Quiz.quiz_type.label("quiz_type"),
            Quiz.created_at.label("created_at"),
            func.count(QuizAttempt.id).label("attempts"),
            func.coalesce(func.avg(QuizAttempt.score), 0).label("avg_score"),
            func.coalesce(func.max(QuizAttempt.score), 0).label("best_score"),
        )
        .outerjoin(QuizAttempt, QuizAttempt.quiz_id == Quiz.id)
        .filter(
            Quiz.document_id == doc_id,
            Quiz.owner_id == user.id,
        )
        .group_by(Quiz.id)
        .order_by(Quiz.created_at.desc())
        .all()
    )

    attempt_rows = (
        db.query(
            QuizAttempt.id.label("attempt_id"),
            QuizAttempt.created_at.label("attempt_at"),
            QuizAttempt.score.label("score"),
            QuizAttempt.max_score.label("max_score"),
            Quiz.quiz_type.label("quiz_type"),
            Quiz.id.label("quiz_id"),
        )
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .filter(
            Quiz.document_id == doc_id,
            Quiz.owner_id == user.id,
            QuizAttempt.owner_id == user.id,
        )
        .order_by(QuizAttempt.created_at.desc())
        .all()
    )

    type_labels = {"vf": "Verdadeiro/Falso", "mc": "Alternativas", "disc": "Discursiva"}
    return templates.TemplateResponse(
        "tutor/doc_detail.html",
        {
            "request": request,
            "doc": doc,
            "summary": summary,
            "quiz_stats": quiz_stats,
            "attempt_rows": attempt_rows,
            "type_labels": type_labels,
        },
    )

# ----- Plano de estudo -----
from markupsafe import Markup
import markdown

@router.get("/doc/{doc_id}/study", response_class=HTMLResponse)
def study_get(request: Request, doc_id: int,
              db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):

    doc = _get_doc_user_safe(db, user.id, doc_id)
    if not doc:
        return RedirectResponse(url="/tutor", status_code=303)

    plan = (
        db.query(StudyPlan)
        .filter(StudyPlan.document_id == doc_id,
                StudyPlan.owner_id == user.id)
        .order_by(StudyPlan.created_at.desc())
        .first()
    )

    rendered_md = None
    if plan:
        rendered_md = Markup(markdown.markdown(
            plan.plan_md,
            extensions=[
                "fenced_code",
                "tables",
                "toc",
                "nl2br",
            ]
        ))

    return templates.TemplateResponse(
        "tutor/study.html",
        {"request": request, "doc": doc, "plan": plan,
         "rendered_md": rendered_md}
    )

@router.post("/doc/{doc_id}/study", response_class=HTMLResponse)
def study_post( request: Request, doc_id: int, horas_semanais: int = Form(6), semanas: int = Form(4), db: Session = Depends(get_db), user: User = Depends(get_current_user),):
    doc = _get_doc_user_safe(db, user.id, doc_id)
    if not doc:
        return RedirectResponse(url="/tutor", status_code=303)
    md = create_study_plan_md(doc.content, horas_semanais=horas_semanais, semanas=semanas)
    row = StudyPlan(document_id=doc_id, owner_id=user.id, plan_md=md)
    db.add(row)
    db.commit()
    return RedirectResponse(url=f"/tutor/doc/{doc_id}/study", status_code=303)

# ----- Provas -----
@router.get("/doc/{doc_id}/quiz", response_class=HTMLResponse)
def quiz_select(request: Request, doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_doc_user_safe(db, user.id, doc_id)
    if not doc:
        return RedirectResponse(url="/tutor", status_code=303)

    quiz_stats = (
        db.query(
            Quiz.id.label("quiz_id"),
            Quiz.quiz_type.label("quiz_type"),
            Quiz.created_at.label("created_at"),
            func.count(QuizAttempt.id).label("attempts"),
            func.coalesce(func.avg(QuizAttempt.score), 0).label("avg_score"),
            func.coalesce(func.max(QuizAttempt.score), 0).label("best_score"),
        )
        .outerjoin(QuizAttempt, QuizAttempt.quiz_id == Quiz.id)
        .filter(Quiz.document_id == doc_id, Quiz.owner_id == user.id)
        .group_by(Quiz.id)
        .order_by(Quiz.created_at.desc())
        .all()
    )

    attempt_rows = (
        db.query(
            QuizAttempt.id.label("attempt_id"),
            QuizAttempt.created_at.label("attempt_at"),
            QuizAttempt.score.label("score"),
            QuizAttempt.max_score.label("max_score"),
            Quiz.quiz_type.label("quiz_type"),
            Quiz.id.label("quiz_id"),
        )
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .filter(Quiz.document_id == doc_id, Quiz.owner_id == user.id, QuizAttempt.owner_id == user.id)
        .order_by(QuizAttempt.created_at.desc())
        .all()
    )

    type_labels = {"vf": "Verdadeiro/Falso", "mc": "Alternativas", "disc": "Discursiva"}
    return templates.TemplateResponse(
        "tutor/quiz_select.html",
        {"request": request, "doc": doc, "quiz_stats": quiz_stats,
         "attempt_rows": attempt_rows, "type_labels": type_labels},
    )

@router.post("/doc/{doc_id}/quiz/create", response_class=HTMLResponse)
def quiz_create(request: Request, doc_id: int, tipo: str = Form(...), n: int = Form(10),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_doc_user_safe(db, user.id, doc_id)
    if not doc:
        return RedirectResponse(url="/tutor", status_code=303)

    if tipo not in ("vf", "mc", "disc"):
        tipo = "mc"
    payload = generate_quiz(doc.content, quiz_type=tipo, n=n)

    q = Quiz(
        document_id=doc_id,
        owner_id=user.id,
        quiz_type=payload["type"],
        items_json=json.dumps(payload["items"], ensure_ascii=False),
    )
    db.add(q); db.commit(); db.refresh(q)
    return RedirectResponse(url=f"/tutor/quiz/{q.id}", status_code=303)

@router.get("/quiz/{quiz_id}", response_class=HTMLResponse)
def quiz_take(request: Request, quiz_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.owner_id == user.id).first()
    if not quiz:
        return RedirectResponse(url="/tutor", status_code=303)
    items = json.loads(quiz.items_json)
    doc = _get_doc_user_safe(db, user.id, quiz.document_id)
    if not doc:
        return RedirectResponse(url="/tutor", status_code=303)
    return templates.TemplateResponse("tutor/quiz_take.html", {"request": request, "quiz": quiz, "items": items, "doc": doc})

@router.post("/quiz/{quiz_id}/submit", response_class=HTMLResponse)
async def quiz_submit(request: Request, quiz_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.owner_id == user.id).first()
    if not quiz:
        return RedirectResponse(url="/tutor", status_code=303)

    items = json.loads(quiz.items_json)
    form = await request.form()
    answers = []
    for i, it in enumerate(items):
        key = f"q_{i}"
        val = form.get(key)
        if it["type"] == "vf":
            answers.append(True if val == "true" else False if val == "false" else None)
        elif it["type"] == "mc":
            try: answers.append(int(val))
            except: answers.append(None)
        else:
            answers.append(val or "")

    correct, total = 0, len(items)
    disc_scores = []
    if quiz.quiz_type in ("vf", "mc"):
        for it, ans in zip(items, answers):
            if it["type"] == "vf" and ans is not None and bool(ans) == bool(it["answer"]):
                correct += 1
            elif it["type"] == "mc" and ans is not None and int(ans) == int(it["answer"]):
                correct += 1
    else:
        doc = _get_doc_user_safe(db, user.id, quiz.document_id)
        if not doc:
            return RedirectResponse(url="/tutor", status_code=303)
        disc_scores = grade_discursive_batch(doc.content, items, answers)
        correct = sum(1 if s >= 0.5 else 0 for s in disc_scores)

    score10 = round((correct / total) * 10) if total else 0
    attempt = QuizAttempt(
        quiz_id=quiz_id,
        owner_id=user.id,
        answers_json=json.dumps(answers, ensure_ascii=False),
        score=score10,
        max_score=10,
    )
    db.add(attempt); db.commit()

    return templates.TemplateResponse(
        "tutor/quiz_result.html",
        {"request": request, "quiz": quiz, "items": items, "answers": answers,
         "score": score10, "correct": correct, "total": total, "disc_scores": disc_scores},
    )
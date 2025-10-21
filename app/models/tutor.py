from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.db.session import Base

class TutorDocument(Base):
    __tablename__ = "tutor_documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TutorChatMessage(Base):
    __tablename__ = "tutor_chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("tutor_documents.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class StudyPlan(Base):
    __tablename__ = "study_plans"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("tutor_documents.id"), index=True, nullable=False)
    plan_md = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("tutor_documents.id"), index=True, nullable=False)
    quiz_type = Column(String(10), nullable=False)
    items_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), index=True, nullable=False)
    answers_json = Column(Text, nullable=False)
    score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

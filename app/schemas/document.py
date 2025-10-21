
from pydantic import BaseModel, Field

class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = ""

class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None

class DocumentOut(BaseModel):
    id: int
    title: str
    content: str
    language: str

    class Config:
        from_attributes = True

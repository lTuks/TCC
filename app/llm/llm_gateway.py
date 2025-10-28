import os
from typing import Sequence, List
from app.config import settings
import re
import hashlib
from typing import List
try:
    from openai import OpenAI
    _HAS_NEW = True
except Exception:
    OpenAI = None
    _HAS_NEW = False

try:
    import openai as _legacy 
    _HAS_LEGACY = True
except Exception:
    _legacy = None 
    _HAS_LEGACY = False

CHAT_MODEL = getattr(settings, "llm_model", None) or os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
EMBED_MODEL = "text-embedding-3-small"
SUMMARY_CACHE = {}
MAX_INPUT_CHARS = 25000

def _hash_payload(text: str, bullets: int) -> str:
    h = hashlib.sha256()
    h.update(str(bullets).encode("utf-8"))
    h.update(text.encode("utf-8"))
    return h.hexdigest()

def _api_key():
    """Retorna a OPENAI_API_KEY a partir de settings/.env."""
    return getattr(settings, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")

def _client_new():
    """Instancia OpenAI (SDK 1.x)."""
    if not _HAS_NEW:
        raise RuntimeError("SDK openai>=1.x não disponível.")
    key = _api_key()
    return OpenAI(api_key=key) if key else OpenAI()

def _naive_summary(text: str, n: int = 5) -> List[str]:
    """Fallback: pega as N primeiras sentenças distintas."""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    sents = re.split(r'(?<=[.!?])\s+', text)
    cleaned = []
    for s in sents:
        s = s.strip()
        if s and (not cleaned or s != cleaned[-1]):
            cleaned.append(s)
        if len(cleaned) >= n:
            break
    return cleaned or ["(sem conteúdo)"]

def chat(system: str, user: str, temperature: float = 0.2) -> str:
    """Executa chat no modelo configurado e retorna apenas o texto.
    Comentários em PT-BR: função principal para prompts do app."""
    if _HAS_NEW:
        c = _client_new()
        # caminho preferido em 1.x
        if hasattr(c, "chat") and hasattr(c.chat, "completions"):
            r = c.chat.completions.create(
                model=CHAT_MODEL,
                messages=[{"role":"system","content":system},
                          {"role":"user","content":user}],
                temperature=temperature,
            )
            return (r.choices[0].message.content or "").strip()
        # fallback: Responses API (algumas versões)
        if hasattr(c, "responses"):
            r = c.responses.create(
                model=CHAT_MODEL,
                input=[{"role":"system","content":system},
                       {"role":"user","content":user}],
                temperature=temperature,
            )
            return getattr(r, "output_text", "").strip()
        raise RuntimeError("SDK 1.x encontrado, mas sem chat.completions/responses.")

    # API antiga 0.28.x
    if not _HAS_LEGACY:
        raise RuntimeError("Nenhum SDK OpenAI disponível. Instale conforme requirements.")
    _legacy.api_key = _api_key()
    r = _legacy.ChatCompletion.create(
        model=CHAT_MODEL or "gpt-3.5-turbo",
        messages=[{"role":"system","content":system},
                  {"role":"user","content":user}],
        temperature=temperature,
    )
    return r["choices"][0]["message"]["content"].strip()

def embed(texts: Sequence[str]) -> List[List[float]]:
    """Gera embeddings para uma sequência de textos."""
    if _HAS_NEW:
        c = _client_new()
        r = c.embeddings.create(model=EMBED_MODEL, input=list(texts))
        return [d.embedding for d in r.data]
    if not _HAS_LEGACY:
        raise RuntimeError("Nenhum SDK OpenAI disponível para embeddings.")
    _legacy.api_key = _api_key()
    r = _legacy.Embedding.create(model=EMBED_MODEL, input=list(texts))
    return [d["embedding"] for d in r["data"]]

def summarize_to_bullets(text: str, bullets: int = 10) -> List[str]:
    """
    Gera um resumo em 'bullets' itens usando o LLM (via chat()), com fallback.
    Retorna uma lista de strings (cada item = 1 bullet).
    """
    text = (text or "").strip()
    if not text:
        return ["(sem conteúdo)"]

    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]

    cache_key = _hash_payload(text, bullets)
    if cache_key in SUMMARY_CACHE:
        return SUMMARY_CACHE[cache_key]

    system = (
        "Você é um assistente de estudo conciso. "
        "Resuma o texto solicitado em tópicos claros e objetivos (bullet points). "
        "Escreva em português do Brasil."
    )
    user_prompt = (
        f"Resuma o texto abaixo em exatamente {bullets} itens curtos. "
        "Foque em conceitos, definições e relações importantes. "
        "Responda somente com bullets (uma linha por bullet), sem parágrafos extras.\n\n"
        f"TEXTO:\n{text}"
    )

    try:
        content = chat(system=system, user=user_prompt, temperature=0.2)
        # normaliza e extrai bullets, mesmo que venham com -, *, •, ou numerados
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        out = []
        for l in lines:
            l = re.sub(r'^(\-|\*|•|\d+[\).\:-]?)\s*', '', l).strip()
            if l:
                out.append(l)
            if len(out) >= bullets:
                break
        if not out:
            out = _naive_summary(text, bullets)
    except Exception:
        out = _naive_summary(text, bullets)

    SUMMARY_CACHE[cache_key] = out
    return out

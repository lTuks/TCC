# -*- coding: utf-8 -*-
"""
Camada de acesso LLM universal.
- Compatível com openai>=1.x (preferencial) e com a API legada openai==0.28.x.
- Centraliza chat e embeddings, lendo a API key de settings/.env.

Funções:
- chat(system, user, temperature=0.2) -> str
- embed(texts) -> List[List[float]]
"""
import os
from typing import Sequence, List
from app.config import settings

# Tenta cliente novo (>=1.x)
try:
    from openai import OpenAI  # type: ignore
    _HAS_NEW = True
except Exception:
    OpenAI = None  # type: ignore
    _HAS_NEW = False

# Tenta API antiga (<1.0)
try:
    import openai as _legacy  # type: ignore
    _HAS_LEGACY = True
except Exception:
    _legacy = None  # type: ignore
    _HAS_LEGACY = False

CHAT_MODEL = getattr(settings, "llm_model", None) or os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
EMBED_MODEL = "text-embedding-3-small"

def _api_key():
    """Retorna a OPENAI_API_KEY a partir de settings/.env."""
    return getattr(settings, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")

def _client_new():
    """Instancia OpenAI (SDK 1.x)."""
    if not _HAS_NEW:
        raise RuntimeError("SDK openai>=1.x não disponível.")
    key = _api_key()
    return OpenAI(api_key=key) if key else OpenAI()

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

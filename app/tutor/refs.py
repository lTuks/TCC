import json

def get_refs(doc) -> list[str]:
    try:
        return json.loads(doc.sources_json or "[]")
    except Exception:
        return []

def refs_md(doc) -> str:
    refs = get_refs(doc)
    if not refs:
        return ""
    lines = "\n".join(f"- {r}" for r in refs)
    return f"\n\n### Referências\n{lines}\n"
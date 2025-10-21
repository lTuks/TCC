from typing import Literal, List, Dict, Any
import json, re
from app.llm.llm_gateway import chat

QuizType = Literal["vf", "mc", "disc"]

def create_study_plan_md(text: str, horas_semanais: int = 6, semanas: int = 4) -> str:
    prompt = f"""Você é um tutor pedagógico. Com base no CONTEÚDO abaixo,
gere um PLANO DE ESTUDO em Markdown para {semanas} semanas, estimando ~{horas_semanais}h/semana.

Formato obrigatório (apenas Markdown):
# Objetivos de aprendizagem
- ...

# Pré-requisitos
- ...

# Cronograma (Semana 1..{semanas})
## Semana 1
- Tópicos:
- Atividades:
- Entregáveis:

# Materiais de apoio
- ...

# Estratégias de revisão e avaliação
- ...

CONTEÚDO:
{text}
"""
    return chat("Você monta planos de estudo objetivos e acionáveis. Responda em PT-BR.", prompt, temperature=0.3)

def _json_from_llm(raw: str) -> Any:
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*\}|\[[\s\S]*\])\s*```", raw, re.IGNORECASE)
    if m: raw = m.group(1)
    m2 = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
    if m2: raw = m2.group(1)
    return json.loads(raw)

def generate_quiz(text: str, quiz_type: QuizType, n: int = 10) -> Dict[str, Any]:
    """Gera uma prova conforme o tipo solicitado.
    Retorna: {type, items} com estrutura apropriada para cada tipo."""
    type_desc = {
        "vf": "Questões de Verdadeiro ou Falso",
        "mc": "Questões de múltipla escolha com 4 alternativas (apenas uma correta)",
        "disc": "Questões discursivas com rubrica de 3-5 critérios objetivos",
    }[quiz_type]

    schema_hint = {
        "vf": """[{"type":"vf","question":"...","answer":true,"explain":"..."}]""",
        "mc": """[{"type":"mc","question":"...","options":["A","B","C","D"],"answer":2,"explain":"..."}]""",
        "disc": """[{"type":"disc","question":"...","rubric":["critério 1","critério 2"]}]"""
    }[quiz_type]

    prompt = f"""Gere {n} itens de prova do tipo: {type_desc}.
Responda SOMENTE JSON válido, no formato do exemplo:

{schema_hint}

Regras:
- Itens não ambíguos e baseados EXCLUSIVAMENTE no CONTEÚDO.
- Não repita enunciados.
- Nas discursivas, forneça "rubric" com critérios factuais.

CONTEÚDO:
{text}
"""
    raw = chat("Você elabora avaliações claras e justas. Responda apenas JSON.", prompt, temperature=0.4)
    items = _json_from_llm(raw)
    out = []
    for it in items:
        t = it.get("type")
        if t == "vf":
            out.append({"type":"vf","question":it.get("question","").strip(),"answer":bool(it.get("answer", False)),"explain":it.get("explain","").strip()})
        elif t == "mc":
            opts = it.get("options") or []
            out.append({"type":"mc","question":it.get("question","").strip(),"options":opts[:4],"answer":int(it.get("answer",0)),"explain":it.get("explain","").strip()})
        elif t == "disc":
            rub = it.get("rubric") or []
            out.append({"type":"disc","question":it.get("question","").strip(),"rubric":[str(x).strip() for x in rub][:5]})
    return {"type": quiz_type, "items": out[:n]}

def grade_discursive_batch(context: str, items: List[Dict[str,Any]], answers: List[str]) -> List[float]:
    bundle = []
    for it, ans in zip(items, answers):
        bundle.append({"question": it["question"], "rubric": it.get("rubric", []), "answer": ans or ""})

    prompt = f"""Avalie respostas DISCURSIVAS com base na rubrica, devolvendo JSON com um array "scores", cada nota entre 0 e 1.
Se a resposta não estiver suportada pelo CONTEXTO, dê 0.

CONTEÚDO:
{context}

ITENS+RESPOSTAS (JSON):
{json.dumps(bundle, ensure_ascii=False, indent=2)}

SAÍDA OBRIGATÓRIA (apenas JSON):
{{"scores":[0.0, 1.0, ...]}}
"""
    raw = chat("Você é um corretor criterioso e objetivo. Apenas JSON.", prompt, temperature=0.0)
    try:
        data = _json_from_llm(raw)
        scores = data.get("scores", [])
        return [max(0.0, min(1.0, float(x))) for x in scores][:len(items)]
    except Exception:
        return [0.0]*len(items)

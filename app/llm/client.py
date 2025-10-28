import os
import httpx
from app.config import settings

OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

class LLMClient:
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.model = settings.llm_model
        self.api_key = settings.openai_api_key

    async def _request(self, method: str, path: str, json: dict):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{OPENAI_BASE}{path}"
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.request(method, url, headers=headers, json=json)
            r.raise_for_status()
            return r.json()

    async def _responses_api(self, messages):
        payload = {
            "model": self.model,
            "input": messages,
            "temperature": 0.2,
        }
        data = await self._request("POST", "/responses", payload)

        text = ""
        try:
            items = data.get("output", []) or data.get("response", {}).get("output", [])
            if items and items[0].get("content"):
                text = items[0]["content"][0].get("text", "")
        except Exception:
            pass
        if not text:
            text = (data.get("output_text")
                    or data.get("content")
                    or str(data))
        return {"output_text": text, "tokens_in": 0, "tokens_out": 0, "model": self.model}

    async def _chat_completions(self, messages):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        data = await self._request("POST", "/chat/completions", payload)
        text = data["choices"][0]["message"]["content"]
        return {"output_text": text, "tokens_in": 0, "tokens_out": 0, "model": self.model}

    async def chat(self, system_prompt: str, user_prompt: str):
        if self.provider == "openai" and self.api_key:
            msgs = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            try:
                return await self._responses_api(msgs)
            except httpx.HTTPStatusError as e:
                if e.response is not None and e.response.status_code in (404, 405):
                    return await self._chat_completions(msgs)
                raise
        txt = (
            f"[DUMMY-{self.model}]\nSistema: {system_prompt}\n\n"
            f"Pergunta:\n{user_prompt}\n\n"
            "Resposta simulada: (substitua pelo provedor real)."
        )
        return {"output_text": txt, "tokens_in": len(user_prompt)//4, "tokens_out": len(txt)//4, "model": self.model}

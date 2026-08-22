import re

with open('policy-ledger-v2/rag/llm_provider.py', 'r') as f:
    content = f.read()

def replacer(match):
    return """        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            "enable_thinking": False
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            resp = self._session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            content = choice["message"]["content"].strip()
            
            # Strip Qwen3 chain-of-thought thinking blocks
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            if not content:
                raise ValueError("Empty response after stripping <think> blocks")
                
            usage = data.get("usage", {})
            return LLMResponse(
                text=content,
                raw_response=data,
                model=self.model,
                usage=usage,
                fallback=False
            )"""

content = re.sub(
    r'        payload = \{\n.*?"stream": stream\n        \}\n\n        headers = \{\n.*?"Authorization": f"Bearer \{self\.api_key\}"\n        \}\n\n        try:\n.*?content = choice\["message"\]\["content"\]\.strip\(\)\n.*?usage = data\.get\("usage", \{\}\)\n.*?fallback=False\n            \)',
    replacer,
    content,
    flags=re.DOTALL
)

with open('policy-ledger-v2/rag/llm_provider.py', 'w') as f:
    f.write(content)


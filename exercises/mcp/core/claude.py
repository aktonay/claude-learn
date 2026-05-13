import os
from openai import OpenAI


class Claude:
    def __init__(self, model: str):
        self.client = OpenAI(
            api_key=os.getenv("ZAI_API_KEY"),
            base_url=os.getenv("ZAI_BASE_URL"),
        )
        self.model = model

    def chat(self, messages, tools=None, temperature=0.7, max_tokens=4000):
        params = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
            "extra_body": {"thinking": {"type": "disabled"}},
        }
        if tools:
            params["tools"] = tools
        return self.client.chat.completions.create(**params)

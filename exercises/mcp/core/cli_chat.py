from typing import Tuple
from mcp.types import Prompt, PromptMessage

from core.chat import Chat
from core.claude import Claude
from mcp_client import MCPClient


class CliChat(Chat):
    def __init__(self, doc_client, clients, claude_service):
        super().__init__(claude_service=claude_service, clients=clients)
        self.doc_client = doc_client

    async def list_prompts(self):
        return await self.doc_client.list_prompts()

    async def list_docs_ids(self):
        return await self.doc_client.read_resource("docs://documents")

    async def get_doc_content(self, doc_id):
        return await self.doc_client.read_resource(f"docs://documents/{doc_id}")

    async def get_prompt(self, command, doc_id):
        return await self.doc_client.get_prompt(command, {"doc_id": doc_id})

    async def _extract_resources(self, query):
        mentions = [word[1:] for word in query.split() if word.startswith("@")]
        doc_ids = await self.list_docs_ids()
        mentioned_docs = []

        for doc_id in doc_ids:
            if doc_id in mentions:
                content = await self.get_doc_content(doc_id)
                mentioned_docs.append((doc_id, content))

        return "".join(
            f'\n<document id="{doc_id}">\n{content}\n</document>\n'
            for doc_id, content in mentioned_docs
        )

    async def _process_command(self, query):
        if not query.startswith("/"):
            return False

        words = query.split()
        command = words[0].replace("/", "")

        if len(words) < 2:
            print(f"  Usage: /{command} <doc_id>")
            return True

        prompt_messages = await self.doc_client.get_prompt(
            command, {"doc_id": words[1]}
        )
        self.messages += _convert_prompt_messages(prompt_messages)
        return True

    async def _process_query(self, query):
        if await self._process_command(query):
            return

        added_resources = await self._extract_resources(query)

        prompt = f"""The user has a question:
<query>
{query}
</query>

The following context may be useful:
<context>
{added_resources}
</context>

Note the user's query might contain references to documents like "@report.docx".
The "@" is only for mentioning the doc. If document content is included above,
you don't need to use a tool to read it. Answer directly and concisely."""

        self.messages.append({"role": "user", "content": prompt})


def _convert_prompt_messages(prompt_messages):
    result = []
    for msg in prompt_messages:
        role = "user" if msg.role == "user" else "assistant"
        content = msg.content

        if isinstance(content, str):
            result.append({"role": role, "content": content})
        elif hasattr(content, "text"):
            result.append({"role": role, "content": content.text})
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if hasattr(item, "text"):
                    text_parts.append(item.text)
                elif isinstance(item, str):
                    text_parts.append(item)
            result.append({"role": role, "content": "\n".join(text_parts)})
        else:
            result.append({"role": role, "content": str(content)})
    return result

import json
from core.claude import Claude
from mcp_client import MCPClient
from core.tools import ToolManager


class Chat:
    def __init__(self, claude_service: Claude, clients: dict[str, MCPClient]):
        self.claude_service = claude_service
        self.clients = clients
        self.messages = []

    async def _process_query(self, query: str):
        self.messages.append({"role": "user", "content": query})

    async def run(self, query: str) -> str:
        await self._process_query(query)

        while True:
            tools = await ToolManager.get_all_tools(self.clients)
            response = self.claude_service.chat(
                messages=self.messages,
                tools=tools if tools else None,
            )

            choice = response.choices[0]
            assistant_msg = choice.message

            msg = {"role": "assistant", "content": assistant_msg.content or ""}
            if assistant_msg.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_msg.tool_calls
                ]
            self.messages.append(msg)

            if choice.finish_reason == "tool_calls" and assistant_msg.tool_calls:
                if assistant_msg.content:
                    print(f"\n[Thinking: {assistant_msg.content[:100]}...]")

                for tc in assistant_msg.tool_calls:
                    tool_name = tc.function.name
                    tool_input = json.loads(tc.function.arguments)
                    print(f"  [Tool call: {tool_name}]")

                    result_text = await ToolManager.execute_single_tool(
                        self.clients, tool_name, tool_input
                    )

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_text,
                    })
            else:
                return assistant_msg.content or ""

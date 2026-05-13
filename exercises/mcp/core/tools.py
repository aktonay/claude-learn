import json
from mcp.types import TextContent
from mcp_client import MCPClient


class ToolManager:
    @classmethod
    async def get_all_tools(cls, clients: dict[str, MCPClient]) -> list[dict]:
        tools = []
        for client in clients.values():
            tool_models = await client.list_tools()
            for t in tool_models:
                schema = dict(t.inputSchema) if t.inputSchema else {"type": "object", "properties": {}}
                tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": schema,
                    },
                })
        return tools

    @classmethod
    async def find_client(cls, clients, tool_name):
        for client in clients.values():
            tool_models = await client.list_tools()
            if any(t.name == tool_name for t in tool_models):
                return client
        return None

    @classmethod
    async def execute_single_tool(cls, clients, tool_name, tool_input):
        client = await cls.find_client(clients, tool_name)
        if not client:
            return json.dumps({"error": f"Tool '{tool_name}' not found"})

        try:
            result = await client.call_tool(tool_name, tool_input)
            if result and result.content:
                texts = [
                    item.text for item in result.content
                    if isinstance(item, TextContent)
                ]
                return "\n".join(texts) if texts else "No output"
            return "No output"
        except Exception as e:
            return json.dumps({"error": str(e)})

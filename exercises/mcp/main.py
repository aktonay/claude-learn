import asyncio
import sys
import os
from dotenv import load_dotenv
from contextlib import AsyncExitStack

from mcp_client import MCPClient
from core.claude import Claude
from core.cli_chat import CliChat
from core.cli import CliApp

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

llm_model = os.getenv("ZAI_MODEL", "glm-4.5-air")


async def main():
    claude_service = Claude(model=llm_model)

    async with AsyncExitStack() as stack:
        doc_client = await stack.enter_async_context(
            MCPClient(command="python", args=["mcp_server.py"])
        )

        clients = {"doc_client": doc_client}

        chat = CliChat(
            doc_client=doc_client,
            clients=clients,
            claude_service=claude_service,
        )

        cli = CliApp(chat)
        await cli.initialize()
        await cli.run()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())

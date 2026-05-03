import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

import nest_asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os
from google import genai
from google.genai import types

# Apply nest_asyncio to allow nested event loops (needed for Jupyter/IPython)
nest_asyncio.apply()

# Load environment variables
load_dotenv(".env", override=True)


class MCPGeminiClient:
    """Client for interacting with Gemini models using MCP tools."""

    def __init__(self, model: str = "gemini-3-flash-preview"):
        """Initialize the Gemini MCP client.

        Args:
            model: The Gemini model to use.
        """
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise SystemExit("Missing GOOGLE_API_KEY in environment or .env file.")
            
        self.genai_client = genai.Client(api_key=api_key)
        self.model = model
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None

    async def connect_to_server(self, server_script_path: str = "server.py"):
        """Connect to an MCP server.

        Args:
            server_script_path: Path to the server script.
        """
        # Server configuration
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
        )

        # Connect to the server
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        # Initialize the connection
        await self.session.initialize()

        # List available tools
        tools_result = await self.session.list_tools()
        print("\nConnected to server with tools:")
        for tool in tools_result.tools:
            print(f"  - {tool.name}: {tool.description}")

    async def get_mcp_tools(self) -> list[types.Tool]:
        """Get available tools from the MCP server in Gemini format.

        Returns:
            A list containing a Gemini Tool object with function declarations.
        """
        tools_result = await self.session.list_tools()
        
        function_declarations = []
        for tool in tools_result.tools:
            function_declarations.append(
                types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.inputSchema,
                )
            )
            
        return [types.Tool(function_declarations=function_declarations)]

    async def process_query(self, query: str) -> str:
        """Process a query using Gemini and available MCP tools.

        Args:
            query: The user query.

        Returns:
            The response from Gemini.
        """
        # Get available tools
        tools = await self.get_mcp_tools()

        # Initialize chat
        chat = self.genai_client.aio.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(tools=tools)
        )

        response = await chat.send_message(query)

        # Handle tool calls if present
        if response.function_calls:
            # Process each tool call
            parts = []
            for function_call in response.function_calls:
                # Execute tool call
                result = await self.session.call_tool(
                    function_call.name,
                    arguments=function_call.args,
                )

                # Add tool response
                parts.append(
                    types.Part.from_function_response(
                        name=function_call.name,
                        response={"result": result.content[0].text}
                    )
                )

            # Get final response from Gemini with tool results
            final_response = await chat.send_message(parts)

            return final_response.text

        # No tool calls, just return the direct response
        return response.text

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    """Main entry point for the client."""
    client = MCPGeminiClient()
    try:
        await client.connect_to_server("server.py")

        print("\nInteractive MCP Client Started!")
        print("Type your queries below. Type 'quit' to exit.")

        while True:
            query = input("\nQuery: ")
            if query.lower() in ['quit', 'exit', 'q']:
                break

            response = await client.process_query(query)
            print(f"\nResponse: {response}")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import sys

load_dotenv("../.env")

# Create an MCP server
mcp = FastMCP(
    name="Calculator",
    host="0.0.0.0",  # only used for SSE transport (localhost)
    port=8051,  # only used for SSE transport (set this to any port)
    stateless_http=True,
)


# Add a simple calculator tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b


# Run the server
if __name__ == "__main__":
    transport = "streamable-http"
    if transport == "stdio":
        print("Running server with stdio transport", file=sys.stderr)
        mcp.run(transport="stdio")
    elif transport == "sse":
        print("Running server with SSE transport", file=sys.stderr)
        mcp.run(transport="sse")
    elif transport == "streamable-http":
        print("Running server with Streamable HTTP transport", file=sys.stderr)
        mcp.run(transport="streamable-http")
    else:
        raise ValueError(f"Unknown transport: {transport}")

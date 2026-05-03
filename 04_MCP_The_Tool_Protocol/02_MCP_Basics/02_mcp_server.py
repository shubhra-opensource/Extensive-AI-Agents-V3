from mcp.server.fastmcp import FastMCP

# Create MCP server instance
mcp = FastMCP("String Reverser")


@mcp.tool()
def reverse_string(text: str) -> str:
    """Reverse a given string"""
    return text[::-1]


import sys

if __name__ == "__main__":
    print("Starting MCP String Reverser server...", file=sys.stderr)
    mcp.run()

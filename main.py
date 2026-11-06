"""Run the server locally.

    python main.py          # stdio (Claude Desktop / Claude Code)
    python main.py http     # streamable HTTP on http://127.0.0.1:8000/mcp
"""
import sys

from dotenv import load_dotenv

load_dotenv()

from upstride_mcp.server import mcp  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        mcp.run(transport="http", host="127.0.0.1", port=8000)
    else:
        mcp.run()

"""r10n MCP server.

Exposes all r10n automations as MCP tools and config templates as resources.
Run via: r10n mcp (CLI) or r10n-mcp (direct entry point).
"""

from mcp.server import FastMCP

mcp = FastMCP(
    name="r10n",
    instructions=(
        "r10n automation toolkit - exposes contacts, certificates, images, email, "
        "colors, rename, validate, and markdown-to-pdf automations as tools."
    ),
)

# Import tool and resource registrations (must be after mcp is created)
from src.mcp import resources, tools  # noqa: E402, F401


def main():
    """Entry point for r10n-mcp."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

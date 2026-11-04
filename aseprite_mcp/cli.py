"""CLI entry point reusing the original Aseprite MCP tool functions."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Image

from . import INSTRUCTIONS, __version__, mcp
from . import tools as _tools  # noqa: F401  (register all original functions)


_HELP_GUIDELINES = """Pixel art guidelines (shared with Aseprite MCP):
  1. Plan pixel bounds and margins before drawing.
  2. Draw the silhouette first; use draw_rows for small details.
  3. Choose a limited palette before adding colour.
  4. Shade from one light direction; avoid tiny-sprite dithering.
  5. Use a dark outline and clean, consistent pixel steps.
  6. Inspect every pass with view_sprite, get_color_stats, and lint_sprite.
  7. Keep objects attached and away from canvas edges.

Run 'aseprite-cli instructions' for the full MCP guidelines."""


def _find_aseprite() -> None:
    """Keep the original ASEPRITE_PATH setting authoritative."""
    if os.getenv("ASEPRITE_PATH") or shutil.which("aseprite"):
        return
    mac_app = Path("/Applications/Aseprite.app/Contents/MacOS/aseprite")
    if mac_app.is_file():
        os.environ["ASEPRITE_PATH"] = str(mac_app)


def _decode(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _arguments(ns: argparse.Namespace) -> dict[str, Any]:
    sources = int(ns.json is not None) + int(ns.input is not None)
    if sources > 1:
        raise ValueError("Use only one of --json or --input")
    if ns.json is not None:
        data = json.loads(ns.json)
    elif ns.input == "-":
        data = json.load(sys.stdin)
    elif ns.input:
        data = json.loads(Path(ns.input).read_text(encoding="utf-8"))
    else:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Tool arguments must be a JSON object")
    for assignment in ns.set:
        if "=" not in assignment:
            raise ValueError(f"Expected KEY=VALUE for --set, got {assignment!r}")
        key, value = assignment.split("=", 1)
        if not key:
            raise ValueError("--set key must not be empty")
        data[key] = _decode(value)
    return data


def _print_result(result: Any) -> bool:
    """Print human-readable text/JSON without dumping embedded image bytes."""
    if isinstance(result, (list, tuple)):
        failed = False
        for item in result:
            failed |= _print_result(item)
        return failed
    if isinstance(result, Image):
        print("Image generated; use the tool's output_filename argument to save a PNG.")
        return False
    if isinstance(result, str):
        print(result)
        return result.startswith(("Failed", "Invalid", "ERROR", "Script failed")) or (
            result.startswith("File ") and " not found" in result
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aseprite-cli",
        description="Call the original diivi/aseprite-mcp tools from a terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_HELP_GUIDELINES,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    ls = sub.add_parser("list", help="List available Aseprite tools")
    ls.add_argument("--json", action="store_true", help="Output names as a JSON array")
    info = sub.add_parser("schema", help="Show a tool's JSON input schema")
    info.add_argument("tool")
    instruction_cmd = sub.add_parser(
        "instructions",
        help="Print the full pixel-art instructions shared with the MCP server",
    )
    instruction_cmd.add_argument(
        "--json", action="store_true", help="Output the instructions as a JSON object",
    )
    run = sub.add_parser(
        "call",
        help="Invoke a tool with JSON or --set KEY=VALUE",
        epilog="For pixel-art best practices, run 'aseprite-cli instructions'.",
    )
    run.add_argument("tool")
    run.add_argument("--json", help="JSON object containing all arguments")
    run.add_argument("--input", help="JSON file path, or '-' for stdin")
    run.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                     help="Override an argument; JSON literals are accepted (repeatable)")
    args = parser.parse_args(argv)

    if args.command == "instructions":
        print(json.dumps({"instructions": INSTRUCTIONS}, ensure_ascii=False, indent=2)
              if args.json else INSTRUCTIONS)
        return 0

    registry = mcp._tool_manager
    if args.command == "list":
        names = sorted(t.name for t in registry.list_tools())
        print(json.dumps(names, ensure_ascii=False, indent=2) if args.json else "\n".join(names))
        return 0
    tool = registry.get_tool(args.tool)
    if tool is None:
        parser.error(f"Unknown tool {args.tool!r}; run 'aseprite-cli list'")
    if args.command == "schema":
        print(json.dumps({"name": tool.name, "description": tool.description,
                          "parameters": tool.parameters}, ensure_ascii=False, indent=2))
        return 0
    try:
        _find_aseprite()
        inputs = _arguments(args)
        response = asyncio.run(registry.call_tool(args.tool, inputs))
        return 1 if _print_result(response) else 0
    except (ValueError, OSError, RuntimeError, TypeError, json.JSONDecodeError) as exc:
        print(f"aseprite-cli: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

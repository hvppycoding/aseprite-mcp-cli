"""Smoke tests for the CLI adapter; original tool tests cover drawing behavior."""

import json

from aseprite_mcp.cli import main


def test_list_and_schema(capsys):
    assert main(["list"]) == 0
    assert "draw_rows" in capsys.readouterr().out
    assert main(["schema", "draw_rows"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert "rows" in schema["parameters"]["properties"]


def test_bad_input(capsys):
    assert main(["call", "get_palette", "--json", "[]"]) == 2
    assert "JSON object" in capsys.readouterr().err
    assert main(["call", "get_palette", "--set", "invalid"]) == 2


def test_call_original_function(monkeypatch, capsys):
    from aseprite_mcp.cli import mcp

    async def fake(_name, inputs):
        return inputs

    monkeypatch.setattr(mcp._tool_manager, "call_tool", fake)
    assert main(["call", "get_palette", "--set", "filename=demo.aseprite", "--set", "frame=1"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data == {"filename": "demo.aseprite", "frame": 1}

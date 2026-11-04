"""Smoke tests for the CLI adapter; original tool tests cover drawing behavior."""

import json

import pytest

from aseprite_mcp import INSTRUCTIONS
from aseprite_mcp.cli import main


def test_list_and_schema(capsys):
    assert main(["list"]) == 0
    assert "draw_rows" in capsys.readouterr().out
    assert main(["schema", "draw_rows"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert "rows" in schema["parameters"]["properties"]


def test_help_has_guidelines_and_full_instructions_command(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "instructions" in output
    for tip in ("silhouette", "draw_rows", "view_sprite",
                "get_color_stats", "lint_sprite", "light direction"):
        assert tip in output
    assert "aseprite-cli instructions" in output


def test_call_help_points_to_guidelines(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["call", "--help"])
    assert exc.value.code == 0
    assert "aseprite-cli instructions" in capsys.readouterr().out


def test_instructions_exact_mcp_text_without_aseprite(monkeypatch, capsys):
    from aseprite_mcp import cli

    def no_aseprite_needed():
        raise AssertionError("Instructions must not require an Aseprite installation")

    monkeypatch.setattr(cli, "_find_aseprite", no_aseprite_needed)
    assert main(["instructions"]) == 0
    assert capsys.readouterr().out == INSTRUCTIONS + "\n"

    assert main(["instructions", "--json"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed == {"instructions": INSTRUCTIONS}


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

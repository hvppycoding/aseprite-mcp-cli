"""Regression: draw_rows must write palette indices on indexed sprites."""

import json

from conftest import ok, run
from aseprite_mcp.tools import drawing, palette, pixel_read


def test_indexed_draw_rows_preserves_palette(sprite):
    ok(run(palette.set_palette(sprite, ["#000000", "#D04648", "#F4B41B"])))
    ok(run(palette.set_color_mode(sprite, "indexed")))
    colors = json.loads(ok(run(palette.get_palette(sprite))))

    ok(run(drawing.draw_rows(sprite, "body", 1, 4, 4, ["RR"], {"R": "#F4B41B"})))
    readback = json.loads(ok(run(pixel_read.read_rows(sprite, 4, 4, 2, 1, 1, "body"))))
    assert readback["rows"] == ["AA"]
    assert readback["legend"] == {"A": "#F4B41B"}
    assert json.loads(ok(run(palette.get_palette(sprite)))) == colors

    error = run(drawing.draw_rows(sprite, "body", 1, 6, 4, ["R"], {"R": "#123456"}))
    assert "not in the indexed sprite palette" in error
    assert json.loads(ok(run(palette.get_palette(sprite)))) == colors

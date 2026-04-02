"""Tests for layout engine and position helpers."""
import pytest
from builder.layout import pos, make_manifest, COLS


def test_pos_top_left():
    assert pos(0, 0) == "0"


def test_pos_row1_col7():
    assert pos(0, 7) == "7"


def test_pos_row2_col0():
    assert pos(1, 0) == "8"


def test_pos_row4_col7():
    assert pos(3, 7) == "31"


def test_cols_is_8():
    assert COLS == 8


def test_make_manifest_structure():
    m = make_manifest({"0": {"UUID": "com.elgato.streamdeck.system.website"}})
    assert m["Columns"] == 8
    assert m["Rows"] == 4
    assert m["DeviceType"] == 20
    assert m["AppearanceVersion"] == 2
    assert "0" in m["Actions"]

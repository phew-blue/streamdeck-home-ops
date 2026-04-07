# tests/test_pages.py
import pytest
from builder.pages import chunk_apps, build_actions_layer, build_status_layer, build_namespace_folder
from unittest.mock import patch


SAMPLE_APPS = [
    {"name": f"app{i}", "deployment": f"app{i}", "url": f"https://app{i}.phew.blue"}
    for i in range(8)
]

SAMPLE_NS = {"name": "media", "color": "#1565c0", "apps": SAMPLE_APPS[:7]}


def test_chunk_apps_under_6():
    chunks = chunk_apps(SAMPLE_APPS[:5])
    assert len(chunks) == 1
    assert len(chunks[0]) == 5

def test_chunk_apps_exactly_6():
    chunks = chunk_apps(SAMPLE_APPS[:6])
    assert len(chunks) == 1

def test_chunk_apps_7_gives_2_chunks():
    chunks = chunk_apps(SAMPLE_APPS[:7])
    assert len(chunks) == 2
    assert len(chunks[0]) == 6
    assert len(chunks[1]) == 1

def test_chunk_apps_14_gives_3_chunks():
    assert len(chunk_apps([{"name": f"a{i}"} for i in range(14)])) == 3

def test_build_actions_layer_has_correct_positions():
    with patch("builder.pages._bat_path", return_value=r"C:\scripts\media-app0-logs.bat"):
        layer = build_actions_layer(
            apps=SAMPLE_APPS[:3],
            namespace="media",
            install_path=r"C:\StreamDeck-HomeOps",
            depth=2,
        )
    # col 1 row 0 = pos 0 → home button
    assert "0" in layer["Actions"]
    assert layer["Actions"]["0"]["UUID"] in (
        "com.elgato.streamdeck.profile.backtoparent",
        "com.elgato.streamdeck.multi",
    )
    # col 2 row 0 = pos 1 → logs for first app
    assert "1" in layer["Actions"]
    assert layer["Actions"]["1"]["UUID"] == "com.elgato.streamdeck.system.open"

def test_build_status_layer_has_plugin_buttons():
    with patch("builder.pages.folder_action", wraps=__import__("builder.actions", fromlist=["folder_action"]).folder_action):
        layer = build_status_layer(
            apps=SAMPLE_APPS[:3],
            namespace="media",
            install_path=r"C:\StreamDeck-HomeOps",
            depth=1,
            has_prev=False,
            has_next=False,
        )
    # col 2 row 1 = pos 9 → pods status for first app
    assert "9" in layer["Actions"]
    assert layer["Actions"]["9"]["UUID"] == "com.phew.blue.homeops.status"
    assert layer["Actions"]["9"]["Settings"]["metric"] == "pods"

# tests/test_pages.py
import pytest
from builder.pages import chunk_apps, build_actions_layer, build_status_layer, build_namespace_folder
from unittest.mock import patch
from builder.layout import pos


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
            has_next=False,
        )
    # col 2 row 1 = pos 9 → pods status for first app
    assert "9" in layer["Actions"]
    assert layer["Actions"]["9"]["UUID"] == "com.phew.blue.homeops.status"
    assert layer["Actions"]["9"]["Settings"]["metric"] == "pods"


# The nav contract is defined by the live profile's first media page:
# back at col0/row0, Down at col7/row1, Next at col7/row3 -- and nothing else.
# There is deliberately no "Up" (col7/row0) and no "Prev" (col0/row3); both were
# removed on the deck by hand, and a generator that restores them regresses it.

def test_status_layer_nav_matches_the_live_media_page():
    layer = build_status_layer(
        apps=SAMPLE_APPS[:6],
        namespace="media",
        install_path=r"C:\StreamDeck-HomeOps",
        has_next=True,
        next_folder_manifest={"Actions": {}},
    )
    acts = layer["Actions"]
    assert acts[pos(0, 0)]["UUID"] == "com.elgato.streamdeck.profile.backtoparent"
    assert acts[pos(1, 7)]["UUID"] == "com.elgato.streamdeck.profile.openchild"
    assert acts[pos(3, 7)]["UUID"] == "com.elgato.streamdeck.profile.openchild"
    assert pos(0, 7) not in acts, "no Up key -- back at 0,0 already goes one level up"
    assert pos(3, 0) not in acts, "no Prev key -- back at 0,0 already reaches the previous page"


def test_actions_layer_has_exactly_one_back_key():
    with patch("builder.pages._bat_path", return_value=r"C:\x.bat"):
        layer = build_actions_layer(
            apps=SAMPLE_APPS[:6],
            namespace="media",
            install_path=r"C:\StreamDeck-HomeOps",
        )
    backs = [p for p, a in layer["Actions"].items()
             if a["UUID"] == "com.elgato.streamdeck.profile.backtoparent"]
    assert backs == [pos(0, 0)]

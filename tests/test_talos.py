# tests/test_talos.py
from builder.talos import build_talos_page

NODES = [
    {"name": "talos-01", "role": "control-plane"},
    {"name": "talos-02", "role": "control-plane"},
    {"name": "talos-03", "role": "control-plane"},
    {"name": "talos-04", "role": "worker"},
]

def test_talos_page_has_home_button():
    m = build_talos_page(NODES)
    assert "0" in m["Actions"]
    assert m["Actions"]["0"]["UUID"] == "com.elgato.streamdeck.profile.backtoparent"

def test_talos_page_has_node_columns():
    m = build_talos_page(NODES)
    # talos-01 at row 0 col 1 → pos 1
    assert "1" in m["Actions"]
    assert m["Actions"]["1"]["Settings"]["node"] == "talos-01"
    assert m["Actions"]["1"]["UUID"] == "com.phewblue.homeops.node"

def test_talos_page_pods_row():
    m = build_talos_page(NODES)
    # pods for talos-01 at row 1 col 1 → pos 9
    assert "9" in m["Actions"]
    assert m["Actions"]["9"]["Settings"]["metric"] == "pods"

def test_talos_page_cpu_row():
    m = build_talos_page(NODES)
    # cpu at row 2 col 1 → pos 17
    assert "17" in m["Actions"]
    assert m["Actions"]["17"]["Settings"]["metric"] == "cpu"

def test_talos_page_ram_row():
    m = build_talos_page(NODES)
    # ram at row 3 col 1 → pos 25
    assert "25" in m["Actions"]
    assert m["Actions"]["25"]["Settings"]["metric"] == "ram"

# tests/test_k8sgrid.py
import pytest
from builder.k8sgrid import build_k8s_grid, NS_POSITIONS

def test_ns_positions_covers_9_namespaces():
    assert len(NS_POSITIONS) == 9

def test_ns_positions_all_in_inner_cols():
    for name, (row, col) in NS_POSITIONS.items():
        assert 1 <= col <= 6, f"{name} col {col} not in inner range 1-6"

def test_build_k8s_grid_has_namespace_folders():
    ns_manifests = {ns: {} for ns in NS_POSITIONS}
    pinned = [
        {"app": "grafana", "url": "https://grafana.phew.blue"},
        {"app": "gatus", "url": "https://status.phew.blue"},
    ]
    manifest = build_k8s_grid(ns_manifests=ns_manifests, pinned=pinned)
    # media is at row 0 col 1 → pos 1
    assert "1" in manifest["Actions"]
    assert manifest["Actions"]["1"]["UUID"] == "com.elgato.streamdeck.profile.openchild"

def test_build_k8s_grid_has_home_button():
    ns_manifests = {ns: {} for ns in NS_POSITIONS}
    manifest = build_k8s_grid(ns_manifests=ns_manifests, pinned=[])
    # home at row 0 col 0 → pos 0
    assert "0" in manifest["Actions"]
    assert manifest["Actions"]["0"]["UUID"] == "com.elgato.streamdeck.profile.backtoparent"

def test_build_k8s_grid_has_no_update_button():
    ns_manifests = {ns: {} for ns in NS_POSITIONS}
    manifest = build_k8s_grid(ns_manifests=ns_manifests, pinned=[])
    # update button (pos 30) should NOT be present — it's on the landing page
    assert "30" not in manifest["Actions"]

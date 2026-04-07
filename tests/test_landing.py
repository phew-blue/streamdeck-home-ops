# tests/test_landing.py
from builder.landing import build_landing_page

K8S = {"AppearanceVersion": 2, "Actions": {}}
TALOS = {"AppearanceVersion": 2, "Actions": {}}

def test_landing_has_back_button():
    m = build_landing_page(K8S, TALOS, r"C:\sd", "https://kromgo.phew.blue")
    assert "0" in m["Actions"]
    assert m["Actions"]["0"]["UUID"] == "com.elgato.streamdeck.profile.backtoparent"

def test_landing_has_talos_folder():
    m = build_landing_page(K8S, TALOS, r"C:\sd", "https://kromgo.phew.blue")
    # Talos at row 0 col 2 → pos 2
    assert "2" in m["Actions"]
    assert m["Actions"]["2"]["UUID"] == "com.elgato.streamdeck.profile.openchild"
    assert m["Actions"]["2"]["Children"] == TALOS

def test_landing_has_k8s_folder():
    m = build_landing_page(K8S, TALOS, r"C:\sd", "https://kromgo.phew.blue")
    # K8s at row 0 col 3 → pos 3
    assert "3" in m["Actions"]
    assert m["Actions"]["3"]["UUID"] == "com.elgato.streamdeck.profile.openchild"
    assert m["Actions"]["3"]["Children"] == K8S

def test_landing_has_flux_display():
    m = build_landing_page(K8S, TALOS, r"C:\sd", "https://kromgo.phew.blue")
    # Flux at row 0 col 4 → pos 4
    assert "4" in m["Actions"]
    assert m["Actions"]["4"]["UUID"] == "com.phew.blue.homeops.cluster"
    assert m["Actions"]["4"]["Settings"]["metric"] == "flux_version"

def test_landing_stats_row2():
    m = build_landing_page(K8S, TALOS, r"C:\sd", "https://kromgo.phew.blue")
    # Age at row 1 col 2 → pos 10
    assert "10" in m["Actions"]
    assert m["Actions"]["10"]["Settings"]["metric"] == "cluster_age_days"
    # Pods at row 1 col 5 → pos 13
    assert "13" in m["Actions"]
    assert m["Actions"]["13"]["Settings"]["metric"] == "cluster_pod_count"

def test_landing_stats_row3():
    m = build_landing_page(K8S, TALOS, r"C:\sd", "https://kromgo.phew.blue")
    # CPU at row 2 col 2 → pos 18
    assert "18" in m["Actions"]
    assert m["Actions"]["18"]["Settings"]["metric"] == "cluster_cpu_usage"
    # Alerts at row 2 col 4 → pos 20
    assert "20" in m["Actions"]
    assert m["Actions"]["20"]["Settings"]["metric"] == "cluster_alert_count"

def test_landing_has_update_button():
    m = build_landing_page(K8S, TALOS, r"C:\sd", "https://kromgo.phew.blue")
    # Update at row 3 col 6 → pos 30
    assert "30" in m["Actions"]
    assert m["Actions"]["30"]["UUID"] == "com.elgato.streamdeck.system.open"

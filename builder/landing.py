# builder/landing.py
"""Build the Home Ops landing page (root of our profile folder)."""

import os
from builder.actions import (
    folder_action, open_file_action, single_back_action,
)
from builder.layout import pos, make_manifest

STATS_ROW2 = [
    ("cluster_age_days",    2),
    ("cluster_uptime_days", 3),
    ("cluster_node_count",  4),
    ("cluster_pod_count",   5),
]

STATS_ROW3 = [
    ("cluster_cpu_usage",    2),
    ("cluster_memory_usage", 3),
    ("cluster_alert_count",  4),
]

STAT_LABELS = {
    "cluster_age_days":     "Age",
    "cluster_uptime_days":  "Uptime",
    "cluster_node_count":   "Nodes",
    "cluster_pod_count":    "Pods",
    "cluster_cpu_usage":    "CPU",
    "cluster_memory_usage": "Memory",
    "cluster_alert_count":  "Alerts",
}


def _cluster_action(metric: str, label: str, kromgo_url: str) -> dict:
    return {
        "Name": label,
        "UUID": "com.phew.blue.homeops.cluster",
        "State": 0,
        "States": [{"Image": "Icons/status-loading", "ShowTitle": True, "Title": "..."}],
        "Settings": {"metric": metric, "kromgo_url": kromgo_url, "label": label},
    }


def build_landing_page(
    k8s_manifest: dict,
    talos_manifest: dict,
    install_path: str,
    kromgo_url: str,
) -> dict:
    actions = {}

    # Col 1 row 1: back → user's own page
    actions[pos(0, 0)] = single_back_action("Back", "Icons/actions/nav-back")

    # Row 1: Talos(col2=pos2), K8s(col3=pos3), Flux(col4=pos4)
    actions[pos(0, 2)] = folder_action("Talos", "Icons/actions/talos", talos_manifest)
    actions[pos(0, 3)] = folder_action("K8s", "Icons/actions/k8s", k8s_manifest)
    actions[pos(0, 4)] = _cluster_action("flux_version", "Flux", kromgo_url)

    # Row 2: cluster info stats (cols 2-5)
    for metric, col in STATS_ROW2:
        actions[pos(1, col)] = _cluster_action(metric, STAT_LABELS[metric], kromgo_url)

    # Row 3: resource + alert stats (cols 2-4)
    for metric, col in STATS_ROW3:
        actions[pos(2, col)] = _cluster_action(metric, STAT_LABELS[metric], kromgo_url)

    # Row 4 col 7 (0-indexed col 6 = pos 30): update profile
    update_bat = os.path.join(install_path, "scripts", "launchers", "update-profile.bat")
    actions[pos(3, 6)] = open_file_action("Update Profile", update_bat, "Icons/actions/update-profile")

    return make_manifest(actions)

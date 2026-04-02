# builder/k8sgrid.py
"""Build the K8s namespace grid page (reached from landing page via K8s button)."""

from builder.actions import folder_action, website_action, single_back_action
from builder.layout import pos, make_manifest

# Namespace button positions (row, col) — 0-indexed
NS_POSITIONS = {
    "media":           (0, 1),
    "downloads":       (0, 2),
    "home":            (0, 3),
    "home-automation": (0, 4),
    "lab":             (0, 5),
    "default":         (0, 6),
    "observability":   (1, 1),
    "network":         (1, 2),
    "db":              (1, 3),
}

# Pinned app positions: row 2, cols 1-5 (0-indexed)
PINNED_POSITIONS = [(2, 1), (2, 2), (2, 3), (2, 4), (2, 5)]


def build_k8s_grid(ns_manifests: dict, pinned: list) -> dict:
    """Assemble the K8s namespace grid manifest."""
    actions = {}

    # Col 1 row 1: home → landing page (1× backtoparent)
    actions[pos(0, 0)] = single_back_action("Home", "Icons/actions/nav-home")

    # Namespace folder buttons
    for ns_name, (row, col) in NS_POSITIONS.items():
        if ns_name in ns_manifests:
            actions[pos(row, col)] = folder_action(
                name=ns_name,
                icon=f"Icons/ns-{ns_name}",
                children=ns_manifests[ns_name],
            )

    # Pinned app quick-launch buttons
    for i, app_cfg in enumerate(pinned[:5]):
        row, col = PINNED_POSITIONS[i]
        actions[pos(row, col)] = website_action(
            name=app_cfg["app"],
            url=app_cfg["url"],
            icon=f"Icons/{app_cfg['app']}",
        )

    return make_manifest(actions)

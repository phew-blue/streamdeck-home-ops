# builder/talos.py
"""Build the Talos nodes page."""

from builder.actions import single_back_action
from builder.layout import pos, make_manifest

INNER_COLS = list(range(1, 7))  # cols 1-6 (0-indexed)


def _node_action(node_name: str, role: str, metric: str) -> dict:
    """Plugin action for a single node metric."""
    label = "CP" if role == "control-plane" else "W"
    name = f"{node_name} ({label})" if metric == "node" else f"{node_name} {metric}"
    return {
        "Name": name,
        "UUID": "com.phewblue.homeops.node",
        "State": 0,
        "States": [{"Image": f"Icons/node-{metric}", "ShowTitle": True, "Title": "..."}],
        "Settings": {"node": node_name, "role": role, "metric": metric},
    }


def build_talos_page(nodes: list) -> dict:
    """Build the per-node status page.
    Home button (col 1 row 1) → backtoparent → landing page.
    """
    actions = {}

    # Col 1 row 1: home → landing page
    actions[pos(0, 0)] = single_back_action("Home", "Icons/actions/nav-home")

    for i, node in enumerate(nodes[:6]):  # max 6 nodes (inner cols 1-6)
        col = INNER_COLS[i]
        name = node["name"]
        role = node["role"]

        actions[pos(0, col)] = _node_action(name, role, "node")   # R1: name+role
        actions[pos(1, col)] = _node_action(name, role, "pods")   # R2: running/capacity pods
        actions[pos(2, col)] = _node_action(name, role, "cpu")    # R3: CPU%
        actions[pos(3, col)] = _node_action(name, role, "ram")    # R4: RAM%

    return make_manifest(actions)

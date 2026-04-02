# builder/pages.py
"""Build namespace folder pages (status + actions layers, pagination)."""

import os
from pathlib import Path
from typing import List
from builder.actions import (
    website_action, folder_action, back_action, single_back_action,
    open_file_action, plugin_status_action, empty_action,
)
from builder.layout import pos, make_manifest

APPS_PER_PAGE = 6
# Inner columns: cols 1-6 (0-indexed)
INNER_COLS = list(range(1, 7))


def chunk_apps(apps: list) -> List[list]:
    return [apps[i:i + APPS_PER_PAGE] for i in range(0, len(apps), APPS_PER_PAGE)]


def _bat_path(namespace: str, app: str, action: str, install_path: str) -> str:
    return os.path.join(install_path, "scripts", "launchers", f"{namespace}-{app}-{action}.bat")


def _app_icon(app_name: str) -> str:
    return f"Icons/{app_name}"


def build_actions_layer(apps: list, namespace: str, install_path: str, depth: int) -> dict:
    """Layer 2: logs / restart / reconcile buttons per app."""
    actions = {}

    # Col 1 row 1 (pos 0): Home
    actions[pos(0, 0)] = back_action(depth=depth, icon="Icons/actions/nav-home")

    # Col 8 row 1 (pos 7): up to status layer
    actions[pos(0, 7)] = single_back_action("Up", "Icons/actions/nav-up")

    for i, app in enumerate(apps):
        col = INNER_COLS[i]
        name = app["name"]
        ns = namespace

        # R1 (row 0): logs
        actions[pos(0, col)] = open_file_action(
            f"Logs {name}",
            _bat_path(ns, name, "logs", install_path),
            "Icons/actions/action-logs",
        )
        # R2 (row 1): restart
        actions[pos(1, col)] = open_file_action(
            f"Restart {name}",
            _bat_path(ns, name, "restart", install_path),
            "Icons/actions/action-restart",
        )
        # R3 (row 2): reconcile
        actions[pos(2, col)] = open_file_action(
            f"Reconcile {name}",
            _bat_path(ns, name, "reconcile", install_path),
            "Icons/actions/action-reconcile",
        )

    return make_manifest(actions)


def build_status_layer(
    apps: list,
    namespace: str,
    install_path: str,
    depth: int,
    has_prev: bool,
    has_next: bool,
    next_folder_manifest: dict = None,
) -> dict:
    """Layer 1: app icon + live plugin status buttons."""
    actions = {}

    # Col 1 row 1 (pos 0): Home
    actions[pos(0, 0)] = back_action(depth=depth, icon="Icons/actions/nav-home")

    # Col 8 row 2 (pos 15): down to actions layer
    actions_layer_manifest = build_actions_layer(
        apps=apps,
        namespace=namespace,
        install_path=install_path,
        depth=depth + 1,
    )
    actions[pos(1, 7)] = folder_action("Down", "Icons/actions/nav-down", actions_layer_manifest)

    if has_prev:
        actions[pos(3, 0)] = single_back_action("Prev", "Icons/actions/nav-back")

    if has_next and next_folder_manifest is not None:
        actions[pos(3, 7)] = folder_action("Next", "Icons/actions/nav-next", next_folder_manifest)

    for i, app in enumerate(apps):
        col = INNER_COLS[i]
        name = app["name"]
        dep = app["deployment"]
        url = app["url"]

        # R1 (row 0): app icon + URL
        actions[pos(0, col)] = website_action(name, url, _app_icon(name))

        # R2 (row 1): pods + restarts (plugin)
        actions[pos(1, col)] = plugin_status_action(name, namespace, dep, "pods")

        # R3 (row 2): CPU (plugin)
        actions[pos(2, col)] = plugin_status_action(name, namespace, dep, "cpu")

        # R4 (row 3): RAM (plugin)
        actions[pos(3, col)] = plugin_status_action(name, namespace, dep, "ram")

    return make_manifest(actions)


def build_namespace_folder(ns: dict, install_path: str, root_depth: int = 1) -> dict:
    """Build the full nested folder manifest for a namespace."""
    chunks = chunk_apps(ns["apps"])
    namespace = ns["name"]

    page_manifests = [None] * len(chunks)

    for page_idx in range(len(chunks) - 1, -1, -1):
        chunk = chunks[page_idx]
        depth = root_depth + page_idx

        next_manifest = page_manifests[page_idx + 1] if page_idx < len(chunks) - 1 else None

        page_manifests[page_idx] = build_status_layer(
            apps=chunk,
            namespace=namespace,
            install_path=install_path,
            depth=depth,
            has_prev=(page_idx > 0),
            has_next=(page_idx < len(chunks) - 1),
            next_folder_manifest=next_manifest,
        )

    return page_manifests[0]

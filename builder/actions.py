"""Factory functions for Stream Deck action JSON objects."""

from typing import Optional


def _base(name: str, uuid: str, icon: str, show_title: bool = False, title: str = "") -> dict:
    """Create base action structure."""
    return {
        "Name": name,
        "UUID": uuid,
        "State": 0,
        "States": [{"Image": icon, "ShowTitle": show_title, "Title": title}],
        "Settings": {},
    }


def website_action(name: str, url: str, icon: str) -> dict:
    """Create a website/link action."""
    a = _base(name, "com.elgato.streamdeck.system.website", icon)
    a["Settings"] = {"openInBrowser": True, "url": url}
    return a


def folder_action(name: str, icon: str, children: dict) -> dict:
    """Create a folder/profile navigation action."""
    a = _base(name, "com.elgato.streamdeck.profile.openchild", icon, show_title=True, title=name)
    a["Children"] = children
    return a


def back_action(depth: int, icon: str) -> dict:
    """Create a back/parent navigation action. Depth > 1 uses multi-action."""
    if depth == 1:
        a = _base("Home", "com.elgato.streamdeck.profile.backtoparent", icon)
        return a
    a = _base("Home", "com.elgato.streamdeck.multi", icon)
    a["Settings"] = {
        "actions": [
            {"UUID": "com.elgato.streamdeck.profile.backtoparent", "Settings": {}}
            for _ in range(depth)
        ]
    }
    return a


# Alias for semantic clarity
multi_back_action = back_action


def single_back_action(name: str, icon: str) -> dict:
    """Go back exactly one level (for layer up button)."""
    a = _base(name, "com.elgato.streamdeck.profile.backtoparent", icon)
    return a


def open_file_action(name: str, path: str, icon: str) -> dict:
    """Create a file/script execution action."""
    a = _base(name, "com.elgato.streamdeck.system.open", icon)
    a["Settings"] = {"path": path}
    return a


def plugin_status_action(app: str, namespace: str, deployment: str, metric: str) -> dict:
    """Create a live status button driven by the custom plugin."""
    return {
        "Name": f"{app}-{metric}",
        "UUID": "com.phewblue.homeops.status",
        "State": 0,
        "States": [{"Image": "Icons/status-loading", "ShowTitle": True, "Title": "..."}],
        "Settings": {
            "app": app,
            "namespace": namespace,
            "deployment": deployment,
            "metric": metric,
        },
    }


def empty_action() -> None:
    """Return None for empty slots."""
    return None

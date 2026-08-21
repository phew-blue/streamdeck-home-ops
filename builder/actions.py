"""Factory functions for Stream Deck action JSON objects.

Actions are built in the compact intermediate shape; builder/v3.py expands them
into the 3.0 format the deck loads.

Plugin-driven actions (com.phew.blue.homeops.*) intentionally carry neither an
Image nor a Title. Stream Deck reads either field as a user choice made in the
Property Inspector and refuses to let a plugin override it, so a key that ships
with one can never be repainted by setImage/setTitle -- silently, with no error
anywhere. Do not "helpfully" add a loading icon or a placeholder title here.
"""


def _base(name: str, uuid: str, icon: str, show_title: bool = False, title: str = "") -> dict:
    """Create base action structure."""
    return {
        "Name": name,
        "UUID": uuid,
        "State": 0,
        "States": [{"Image": icon, "ShowTitle": show_title, "Title": title}],
        "Settings": {},
    }


def _plugin_base(name: str, uuid: str, settings: dict) -> dict:
    """Base structure for a key this plugin paints at runtime.

    No Image, no Title -- see the module docstring.
    """
    return {
        "Name": name,
        "UUID": uuid,
        "State": 0,
        "States": [{"ShowTitle": True}],
        "Settings": settings,
    }


def website_action(name: str, url: str, icon: str) -> dict:
    """Create a website/link action."""
    a = _base(name, "com.elgato.streamdeck.system.website", icon)
    a["Settings"] = {"openInBrowser": True, "url": url}
    return a


def folder_action(name: str, icon: str, children: dict, show_title: bool = True) -> dict:
    """Create a folder/profile navigation action."""
    a = _base(name, "com.elgato.streamdeck.profile.openchild", icon,
              show_title=show_title, title=name if show_title else "")
    a["Children"] = children
    return a


def single_back_action(name: str, icon: str) -> dict:
    """Go back exactly one level."""
    return _base(name, "com.elgato.streamdeck.profile.backtoparent", icon)


def open_file_action(name: str, path: str, icon: str) -> dict:
    """Create a file/script execution action."""
    a = _base(name, "com.elgato.streamdeck.system.open", icon)
    a["Settings"] = {"path": path}
    return a


def plugin_status_action(app: str, namespace: str, deployment: str, metric: str) -> dict:
    """Create a live status button driven by the custom plugin."""
    return _plugin_base(
        f"{app}-{metric}",
        "com.phew.blue.homeops.status",
        {
            "app": app,
            "namespace": namespace,
            "deployment": deployment,
            "metric": metric,
        },
    )


def plugin_cluster_action(metric: str, label: str, kromgo_url: str) -> dict:
    """Create a live cluster-stat button driven by the custom plugin."""
    return _plugin_base(
        label,
        "com.phew.blue.homeops.cluster",
        {"metric": metric, "kromgo_url": kromgo_url, "label": label},
    )


def plugin_node_action(name: str, node: str, role: str, metric: str) -> dict:
    """Create a live Talos-node button driven by the custom plugin."""
    return _plugin_base(
        name,
        "com.phew.blue.homeops.node",
        {"node": node, "role": role, "metric": metric},
    )


def empty_action() -> None:
    """Return None for empty slots."""
    return None

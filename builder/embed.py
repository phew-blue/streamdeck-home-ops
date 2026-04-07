"""Embed the home-ops manifest tree as a child page within a Default Profile ZIP.

Converts from the home-ops 1.0 flat-key format to the Default Profile 3.0
col,row format, extracting nested Children into separate sub-profile ZIP entries.
"""

import hashlib
import json
import uuid
import zipfile
from pathlib import Path
from typing import Optional

COLS = 8
MAIN_PROFILE_UUID = "943A6338-7C91-458C-893D-CA16BEC2A82F"
MAIN_PAGE_UUID = "F570B178-3AF2-4C52-9505-9426A0D48CA7"
BUTTON_POSITION = "3,0"  # col 4, row 1 in Stream Deck UI (1-indexed)
BUTTON_TITLE = "Home\nOps"

EXTRA_REQUIRED_PLUGINS = [
    "com.phew.blue.homeops.cluster",
    "com.phew.blue.homeops.status",
    "com.phew.blue.homeops.node",
    "com.elgato.streamdeck.multi",
]


def _pos_to_colrow(pos: str) -> str:
    n = int(pos)
    return f"{n % COLS},{n // COLS}"


def _img_key(icon_ref: str) -> str:
    """Deterministic unique filename for an icon reference."""
    h = hashlib.sha1(icon_ref.encode()).hexdigest()[:26].upper()
    return f"{h}Z.png"


def _convert_states(states: list, image_map: dict) -> list:
    result = []
    for state in states:
        s = dict(state)
        img = s.get("Image", "")
        if img:
            fname = _img_key(img)
            image_map[img] = fname
            s["Image"] = f"Images/{fname}"
        result.append(s)
    return result


def _convert_action(action: dict, image_map: dict, child_registry: dict) -> dict:
    """Convert a single 1.0 action to Default Profile 3.0 format.

    openchild actions with inline Children are extracted into child_registry
    and replaced with a ProfileUUID reference.
    """
    converted = {
        "ActionID": str(uuid.uuid4()),
        "LinkedTitle": True,
        "Name": action.get("Name", ""),
        "Plugin": {
            "Name": action.get("Name", ""),
            "UUID": action["UUID"],
            "Version": "1.0",
        },
        "Resources": None,
        "Settings": dict(action.get("Settings", {})),
        "State": action.get("State", 0),
        "States": _convert_states(action.get("States", [{}]), image_map),
        "UUID": action["UUID"],
    }

    if action["UUID"] == "com.elgato.streamdeck.profile.openchild" and "Children" in action:
        child_uuid = str(uuid.uuid4()).upper()
        child_image_map: dict = {}
        child_actions = _convert_actions(action["Children"], child_image_map, child_registry)
        child_registry[child_uuid] = {
            "manifest": {
                "Controllers": [{"Actions": child_actions, "Type": "Keypad"}],
                "Icon": "",
                "Name": "",
            },
            "image_map": child_image_map,
        }
        converted["Settings"] = {"ProfileUUID": child_uuid.lower()}

    return converted


def _convert_actions(manifest: dict, image_map: dict, child_registry: dict) -> dict:
    """Convert all actions in a 1.0 manifest to 3.0 col,row-keyed actions."""
    result = {}
    for pos, action in manifest.get("Actions", {}).items():
        if action is None:
            continue
        result[_pos_to_colrow(pos)] = _convert_action(action, image_map, child_registry)
    return result


def _read_icon(icon_ref: str, hop_icons: dict) -> Optional[bytes]:
    """Return icon bytes for a reference like 'Icons/grafana' or 'Icons/actions/nav-back'."""
    zip_path = icon_ref + ".png"
    return hop_icons.get(zip_path)


def embed_home_ops(
    default_profile: str,
    home_ops_profile: str,
) -> None:
    """Read the home-ops profile ZIP and embed its pages into the Default Profile.

    Adds an openchild button at BUTTON_POSITION on the main page.
    All home-ops pages become sibling sub-profiles within the same ZIP.
    """
    # Read all current Default Profile entries
    with zipfile.ZipFile(default_profile, "r") as zf:
        entries: dict = {name: zf.read(name) for name in zf.namelist()}

    # Read home-ops manifest + pre-load all icons from the ZIP
    with zipfile.ZipFile(home_ops_profile, "r") as hop:
        hop_manifest = json.loads(hop.read("manifest.json"))
        hop_icons = {
            name: hop.read(name)
            for name in hop.namelist()
            if name.endswith(".png")
        }

    # Convert the home-ops manifest tree to Default Profile 3.0 format
    child_registry: dict = {}
    root_image_map: dict = {}
    root_actions = _convert_actions(hop_manifest, root_image_map, child_registry)

    root_child_uuid = str(uuid.uuid4()).upper()
    root_child = {
        "manifest": {
            "Controllers": [{"Actions": root_actions, "Type": "Keypad"}],
            "Icon": "",
            "Name": "",
        },
        "image_map": root_image_map,
    }

    # Add the Home Ops openchild button to the main page at BUTTON_POSITION
    main_key = (
        f"Profiles/{MAIN_PROFILE_UUID}.sdProfile"
        f"/Profiles/{MAIN_PAGE_UUID}/manifest.json"
    )
    main_manifest = json.loads(entries[main_key])
    main_manifest["Controllers"][0]["Actions"][BUTTON_POSITION] = {
        "ActionID": str(uuid.uuid4()),
        "LinkedTitle": True,
        "Name": "Home Ops",
        "Plugin": {
            "Name": "Create Folder",
            "UUID": "com.elgato.streamdeck.profile.openchild",
            "Version": "1.0",
        },
        "Resources": None,
        "Settings": {"ProfileUUID": root_child_uuid.lower()},
        "State": 0,
        "States": [
            {
                "FontFamily": "",
                "FontSize": 12,
                "FontStyle": "",
                "FontUnderline": False,
                "Image": "",
                "OutlineThickness": 2,
                "ShowTitle": True,
                "Title": BUTTON_TITLE,
                "TitleAlignment": "bottom",
                "TitleColor": "#ffffff",
            }
        ],
        "UUID": "com.elgato.streamdeck.profile.openchild",
    }
    entries[main_key] = json.dumps(main_manifest).encode()

    # Update RequiredPlugins in package.json
    pkg = json.loads(entries["package.json"])
    for plugin in EXTRA_REQUIRED_PLUGINS:
        if plugin not in pkg["RequiredPlugins"]:
            pkg["RequiredPlugins"].append(plugin)
    entries["package.json"] = json.dumps(pkg).encode()

    # Write all child profiles into the ZIP (flat — all at the same level)
    base = f"Profiles/{MAIN_PROFILE_UUID}.sdProfile/Profiles/"
    all_children = {root_child_uuid: root_child, **child_registry}

    for child_uuid, child_data in all_children.items():
        prefix = f"{base}{child_uuid}/"
        entries[f"{prefix}"] = b""
        entries[f"{prefix}Images/"] = b""
        entries[f"{prefix}manifest.json"] = json.dumps(child_data["manifest"]).encode()
        for icon_ref, fname in child_data["image_map"].items():
            icon_bytes = _read_icon(icon_ref, hop_icons)
            if icon_bytes:
                entries[f"{prefix}Images/{fname}"] = icon_bytes

    # Repack the Default Profile ZIP
    with zipfile.ZipFile(default_profile, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)

    print(f"✓ Home Ops button added at position {BUTTON_POSITION} (col 4, row 1)")
    print(f"✓ Embedded {len(all_children)} child profile pages into Default Profile")

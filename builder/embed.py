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


def _fix_settings(uuid_str: str, settings: dict) -> dict:
    """Fix settings for 3.0 format differences from 1.0."""
    s = dict(settings)
    if uuid_str == "com.elgato.streamdeck.system.website":
        # 3.0 uses "path" not "url"
        if "url" in s and "path" not in s:
            s["path"] = s.pop("url")
    return s


def _convert_action(action: dict, image_map: dict, child_registry: dict) -> dict:
    """Convert a single 1.0 action to Default Profile 3.0 format.

    openchild actions with inline Children are extracted into child_registry
    and replaced with a ProfileUUID reference.
    """
    uuid_str = action["UUID"]
    converted = {
        "ActionID": str(uuid.uuid4()),
        "LinkedTitle": True,
        "Name": action.get("Name", ""),
        "Plugin": {
            "Name": action.get("Name", ""),
            "UUID": uuid_str,
            "Version": "1.0",
        },
        "Resources": None,
        "Settings": _fix_settings(uuid_str, action.get("Settings", {})),
        "State": action.get("State", 0),
        "States": _convert_states(action.get("States", [{}]), image_map),
        "UUID": uuid_str,
    }

    if uuid_str == "com.elgato.streamdeck.profile.openchild" and "Children" in action:
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


def _collect_child_uuids(manifest: dict, entries: dict, prefix: str, protected: set) -> set:
    """Recursively collect all sub-profile UUIDs reachable from this manifest."""
    uuids = set()
    actions = manifest.get("Controllers", [{}])[0].get("Actions", {}) or {}
    for action in actions.values():
        if not action:
            continue
        if action.get("UUID") == "com.elgato.streamdeck.profile.openchild":
            child_uuid = action.get("Settings", {}).get("ProfileUUID", "").upper()
            if child_uuid and child_uuid not in protected:
                uuids.add(child_uuid)
                child_key = f"{prefix}{child_uuid}/manifest.json"
                child_data = entries.get(child_key)
                if child_data:
                    child_manifest = json.loads(child_data)
                    uuids |= _collect_child_uuids(child_manifest, entries, prefix, protected)
    return uuids


def _detect_profile_and_page(entries: dict) -> tuple[str, str]:
    """Auto-detect the main profile UUID and main page UUID from ZIP entries."""
    # Find the top-level profile manifest: Profiles/UUID.sdProfile/manifest.json
    for key in entries:
        parts = key.split("/")
        if (len(parts) == 3 and parts[0] == "Profiles"
                and parts[1].endswith(".sdProfile") and parts[2] == "manifest.json"):
            profile_uuid = parts[1].replace(".sdProfile", "")
            manifest = json.loads(entries[key])
            # Pages list gives us the page UUIDs; first is the main page
            pages = manifest.get("Pages", {}).get("Pages", [])
            if pages:
                return profile_uuid.upper(), pages[0].upper()
    raise ValueError("Could not detect profile UUID from ZIP entries")


def embed_home_ops(
    default_profile: str,
    home_ops_profile: str,
    home_ops_icon: Optional[bytes] = None,
) -> None:
    """Read the home-ops profile ZIP and embed its pages into the Default Profile.

    Adds an openchild button at BUTTON_POSITION on the main page.
    All home-ops pages become sibling sub-profiles within the same ZIP.
    On re-run, the previously embedded pages are replaced.
    """
    # Read all current Default Profile entries
    with zipfile.ZipFile(default_profile, "r") as zf:
        entries: dict = {name: zf.read(name) for name in zf.namelist()}

    MAIN_PROFILE_UUID, MAIN_PAGE_UUID = _detect_profile_and_page(entries)
    base = f"Profiles/{MAIN_PROFILE_UUID}.sdProfile/Profiles/"

    # Read home-ops manifest + pre-load all icons from the ZIP
    with zipfile.ZipFile(home_ops_profile, "r") as hop:
        hop_manifest = json.loads(hop.read("manifest.json"))
        hop_icons = {
            name: hop.read(name)
            for name in hop.namelist()
            if name.endswith(".png")
        }

    # Collect all original page UUIDs (those already in the ZIP before embed)
    existing_page_uuids = {
        k.split("/")[3].upper()
        for k in entries
        if k.startswith(f"Profiles/{MAIN_PROFILE_UUID}.sdProfile/Profiles/")
        and k.count("/") == 4 and k.endswith("manifest.json")
    }

    # --- Remove previously embedded home-ops subtree (if any) ---
    main_key = f"{base}{MAIN_PAGE_UUID}/manifest.json"
    main_manifest = json.loads(entries[main_key])
    existing_btn = main_manifest["Controllers"][0]["Actions"].get(BUTTON_POSITION)
    if existing_btn:
        old_root_uuid = existing_btn.get("Settings", {}).get("ProfileUUID", "").upper()
        if old_root_uuid and old_root_uuid not in existing_page_uuids:
            old_key = f"{base}{old_root_uuid}/manifest.json"
            if old_key in entries:
                old_root_manifest = json.loads(entries[old_key])
                stale_uuids = {old_root_uuid} | _collect_child_uuids(
                    old_root_manifest, {k: v for k, v in entries.items() if isinstance(v, bytes)},
                    base, existing_page_uuids
                )
                removed = 0
                for e_key in list(entries.keys()):
                    for u in stale_uuids:
                        if f"/{u}/" in e_key.upper() or e_key.upper().endswith(f"/{u}/"):
                            del entries[e_key]
                            removed += 1
                            break
                print(f"  Removed {removed} stale home-ops entries")

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

    # Build button icon state
    if home_ops_icon:
        icon_fname = "HOMEOPSZ.png"
        btn_image = f"Images/{icon_fname}"
    else:
        icon_fname = None
        btn_image = ""

    # Add/replace the Home Ops openchild button on the main page
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
                "Image": btn_image,
                "OutlineThickness": 2,
                "ShowTitle": btn_image == "",
                "Title": BUTTON_TITLE if btn_image == "" else "",
                "TitleAlignment": "bottom",
                "TitleColor": "#ffffff",
            }
        ],
        "UUID": "com.elgato.streamdeck.profile.openchild",
    }
    entries[main_key] = json.dumps(main_manifest).encode()

    # Store button icon in the main page Images dir
    if home_ops_icon and icon_fname:
        img_dir = f"Profiles/{MAIN_PROFILE_UUID}.sdProfile/Profiles/{MAIN_PAGE_UUID}/Images/"
        entries[img_dir + icon_fname] = home_ops_icon

    # Update RequiredPlugins in package.json
    pkg = json.loads(entries["package.json"])
    for plugin in EXTRA_REQUIRED_PLUGINS:
        if plugin not in pkg["RequiredPlugins"]:
            pkg["RequiredPlugins"].append(plugin)
    entries["package.json"] = json.dumps(pkg).encode()

    # Write all child profiles into the ZIP
    all_children = {root_child_uuid: root_child, **child_registry}

    for child_uuid_str, child_data in all_children.items():
        prefix = f"{base}{child_uuid_str}/"
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

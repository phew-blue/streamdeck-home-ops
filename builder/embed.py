"""Embed the home-ops page tree as a child folder inside a Default Profile ZIP.

The Default Profile is already a 3.0 archive, so this reuses builder/v3.py's
converter wholesale: the home-ops tree becomes a set of sibling pages under the
target profile's Profiles/ directory, and one openchild key on the main page
points at the root of it.

Re-running replaces the previously embedded subtree instead of stacking a second
copy, and because v3.py derives page UUIDs deterministically the replacement
lands on the same UUIDs it used last time.
"""

import json
import uuid
import zipfile
from typing import Optional

from builder.v3 import (
    UUID_NAMESPACE,
    convert_tree,
    resolve_icon,
)

BUTTON_POSITION = "3,0"  # col 4, row 1 in the Stream Deck UI (1-indexed)
BUTTON_TITLE = "Home\nOps"

EXTRA_REQUIRED_PLUGINS = [
    "com.phew.blue.homeops.cluster",
    "com.phew.blue.homeops.status",
    "com.phew.blue.homeops.node",
]


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
                child_data = entries.get(f"{prefix}{child_uuid}/manifest.json")
                if child_data:
                    uuids |= _collect_child_uuids(
                        json.loads(child_data), entries, prefix, protected
                    )
    return uuids


def _detect_profile_and_page(entries: dict) -> tuple[str, str]:
    """Auto-detect the main profile UUID and main page UUID from ZIP entries."""
    for key in entries:
        parts = key.split("/")
        if (len(parts) == 3 and parts[0] == "Profiles"
                and parts[1].endswith(".sdProfile") and parts[2] == "manifest.json"):
            profile_uuid = parts[1].replace(".sdProfile", "")
            manifest = json.loads(entries[key])
            pages = manifest.get("Pages", {}).get("Pages", [])
            if pages:
                return profile_uuid.upper(), pages[0].upper()
    raise ValueError("Could not detect profile UUID from ZIP entries")


def embed_home_ops(
    default_profile: str,
    home_ops_tree: dict,
    home_ops_icon: Optional[bytes] = None,
) -> None:
    """Embed the home-ops page tree into the Default Profile at BUTTON_POSITION."""
    with zipfile.ZipFile(default_profile, "r") as zf:
        entries: dict = {name: zf.read(name) for name in zf.namelist()}

    main_profile_uuid, main_page_uuid = _detect_profile_and_page(entries)
    base = f"Profiles/{main_profile_uuid}.sdProfile/Profiles/"

    # Only the profile's own top-level pages are off-limits. Anything reachable
    # solely through the Home Ops button is ours and may be replaced. Guarding
    # with "every page dir already in the archive" instead would protect the
    # previous embed from itself, and the Default Profile would grow by a full
    # home-ops subtree on every run.
    sd_manifest = json.loads(entries[f"Profiles/{main_profile_uuid}.sdProfile/manifest.json"])
    existing_page_uuids = {p.upper() for p in sd_manifest["Pages"]["Pages"]}

    # --- Remove a previously embedded home-ops subtree, if present ---
    main_key = f"{base}{main_page_uuid}/manifest.json"
    main_manifest = json.loads(entries[main_key])
    existing_btn = main_manifest["Controllers"][0]["Actions"].get(BUTTON_POSITION)
    if existing_btn:
        old_root_uuid = existing_btn.get("Settings", {}).get("ProfileUUID", "").upper()
        old_key = f"{base}{old_root_uuid}/manifest.json"
        if old_root_uuid and old_root_uuid not in existing_page_uuids and old_key in entries:
            stale = {old_root_uuid} | _collect_child_uuids(
                json.loads(entries[old_key]), entries, base, existing_page_uuids
            )
            removed = 0
            for e_key in list(entries):
                if any(f"/{u}/" in e_key.upper() for u in stale):
                    del entries[e_key]
                    removed += 1
            print(f"  Removed {removed} stale home-ops entries")

    root_uuid, pages = convert_tree(home_ops_tree, root_path="/embed/")

    # Add/replace the Home Ops openchild button on the main page
    btn_image = "Images/HOMEOPSZ.png" if home_ops_icon else ""
    main_manifest["Controllers"][0]["Actions"][BUTTON_POSITION] = {
        "ActionID": str(uuid.uuid5(UUID_NAMESPACE, "embed-button")),
        "LinkedTitle": True,
        "Name": "Home Ops",
        "Plugin": {
            "Name": "Create Folder",
            "UUID": "com.elgato.streamdeck.profile.openchild",
            "Version": "1.0",
        },
        "Resources": None,
        "Settings": {"ProfileUUID": root_uuid.lower()},
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

    if home_ops_icon:
        entries[f"{base}{main_page_uuid}/Images/HOMEOPSZ.png"] = home_ops_icon

    # Update RequiredPlugins in package.json
    pkg = json.loads(entries["package.json"])
    for plugin in EXTRA_REQUIRED_PLUGINS:
        if plugin not in pkg["RequiredPlugins"]:
            pkg["RequiredPlugins"].append(plugin)
    entries["package.json"] = json.dumps(pkg).encode()

    # Write the converted pages into the ZIP
    for page_uuid, page in pages.items():
        prefix = f"{base}{page_uuid}/"
        entries[prefix] = b""
        entries[f"{prefix}Images/"] = b""
        entries[f"{prefix}manifest.json"] = json.dumps(page["manifest"]).encode()
        for icon_ref, filename in page["images"].items():
            source = resolve_icon(icon_ref)
            if source is not None:
                entries[f"{prefix}Images/{filename}"] = source.read_bytes()

    with zipfile.ZipFile(default_profile, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)

    print(f"✓ Home Ops button added at position {BUTTON_POSITION} (col 4, row 1)")
    print(f"✓ Embedded {len(pages)} child profile pages into Default Profile")

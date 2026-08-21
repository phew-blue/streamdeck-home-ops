# builder/v3.py
"""Convert the internal page tree into the Stream Deck 3.0 profile format.

# Why this module exists

Stream Deck 7.5 rejects the 1.0 layout this repo used to emit -- a flat
`manifest.json` at the archive root plus an `Icons/` directory -- with
"unknown file contents". The format it accepts looks like this:

    package.json
    Profiles/<PROFILE-UUID>.sdProfile/manifest.json
    Profiles/<PROFILE-UUID>.sdProfile/Images/
    Profiles/<PROFILE-UUID>.sdProfile/Profiles/<PAGE-UUID>/manifest.json
    Profiles/<PROFILE-UUID>.sdProfile/Profiles/<PAGE-UUID>/Images/<KEY>.png

Every page -- the top-level one and every folder -- is a sibling directory
under `<PROFILE-UUID>.sdProfile/Profiles/`. Nesting is expressed by reference,
not by directory layout: an `openchild` key stores the child page's UUID in
`Settings.ProfileUUID`. The profile manifest's `Pages.Pages` lists only the
top-level pages.

Keys are addressed `"col,row"` (0-indexed), not by the flat `row*8+col` index
the 1.0 format used.

# Plugin-owned keys carry no Title and no Image

Stream Deck treats a Title or an Image stored on a key as a user choice made in
the Property Inspector, and a plugin may not override either -- setTitle and
setImage resolve successfully and change nothing, silently. Any key whose UUID
belongs to this plugin therefore gets a State with neither field. See
`scripts/strip-plugin-overrides.py` for the archaeology.

# UUIDs are derived, not random

Page and action UUIDs come from uuid5 over a stable path through the tree, so
regenerating an unchanged config produces a byte-identical archive and the deck
keeps whatever the previous import created rather than orphaning it.
"""

import hashlib
import json
import uuid
import zipfile
from pathlib import Path
from typing import Optional

# Fixed namespace for all derived UUIDs. Changing this re-keys every page.
UUID_NAMESPACE = uuid.UUID("6f2a1d3e-0c4b-5a7d-9e18-2b6c4f0a8d51")

PLUGIN_UUID_PREFIX = "com.phew.blue.homeops."

OPENCHILD = "com.elgato.streamdeck.profile.openchild"
BACKTOPARENT = "com.elgato.streamdeck.profile.backtoparent"

# Cosmetic label Stream Deck shows for the built-in actions. For everything
# else the action's own Name is used, which is what a real export does.
BUILTIN_PLUGIN_NAMES = {
    OPENCHILD: "Create Folder",
    BACKTOPARENT: "Open Parent Folder",
}

NULL_UUID = "00000000-0000-0000-0000-000000000000"

DEFAULT_DEVICE_MODEL = "20GAT9901"  # Stream Deck XL
DEFAULT_DEVICE_UUID = "9c55451f-0684-4931-b0cb-bddf1b58fef4"
DEFAULT_PROFILE_NAME = "Home Ops"
DEFAULT_APP_VERSION = "7.4.0.22712"

COLS = 8

# Directories searched for an "Icons/..." reference, in order.
ICON_DIRS = ("apps", "namespaces", "actions")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def derive_uuid(path: str) -> str:
    """Stable uppercase UUID for a path through the page tree."""
    return str(uuid.uuid5(UUID_NAMESPACE, path)).upper()


def pos_to_colrow(position: str) -> str:
    """Convert a 1.0 flat key index to the 3.0 "col,row" address."""
    n = int(position)
    return f"{n % COLS},{n // COLS}"


def image_filename(icon_ref: str) -> str:
    """Deterministic per-page filename for an icon reference."""
    return hashlib.sha1(icon_ref.encode()).hexdigest()[:26].upper() + "Z.png"


def is_plugin_action(action_uuid: str) -> bool:
    return action_uuid.startswith(PLUGIN_UUID_PREFIX)


def resolve_icon(icon_ref: str, icon_root: Path = Path("icons")) -> Optional[Path]:
    """Map an "Icons/..." reference onto a file under icons/.

    "Icons/plex"              -> icons/apps/plex.png
    "Icons/actions/nav-home"  -> icons/actions/nav-home.png
    "Icons/ns-media"          -> icons/namespaces/media.png

    The ns- prefix is a naming quirk of the grid page: the reference is
    prefixed but the generated file is not, so both spellings are tried.
    """
    stem = icon_ref.split("/")[-1]
    names = [stem]
    if stem.startswith("ns-"):
        names.append(stem[3:])
    for name in names:
        for sub in ICON_DIRS:
            candidate = icon_root / sub / f"{name}.png"
            if candidate.exists():
                return candidate
    return None


# ---------------------------------------------------------------------------
# Action conversion
# ---------------------------------------------------------------------------

def _make_state(action_uuid: str, state: dict, images: dict) -> dict:
    """Build a 3.0 state dict.

    Plugin-owned keys deliberately get neither Image nor Title: either one
    would freeze the tile at whatever the profile shipped.
    """
    out = {
        "FontFamily": "",
        "FontSize": 12,
        "FontStyle": "",
        "FontUnderline": False,
        "OutlineThickness": 2,
        "ShowTitle": bool(state.get("ShowTitle", False)),
        "TitleAlignment": "bottom",
        "TitleColor": "#ffffff",
    }
    if is_plugin_action(action_uuid):
        # Plugin paints this key at runtime; leave both overrides unset.
        out["ShowTitle"] = True
        return out

    icon_ref = state.get("Image") or ""
    if icon_ref:
        images[icon_ref] = image_filename(icon_ref)
        out["Image"] = f"Images/{images[icon_ref]}"
    else:
        out["Image"] = ""

    title = state.get("Title") or ""
    if title:
        out["Title"] = title
    return out


def _convert_action(action: dict, path: str, images: dict, pages: dict) -> dict:
    """Convert one 1.0 action, recursing into any inline Children."""
    action_uuid = action["UUID"]
    name = action.get("Name", "")

    settings = dict(action.get("Settings", {}))
    if action_uuid == OPENCHILD:
        child_uuid = _convert_page(action.get("Children") or {}, path, pages)
        settings = {"ProfileUUID": child_uuid.lower()}

    return {
        "ActionID": str(uuid.uuid5(UUID_NAMESPACE, path + "#action")),
        "LinkedTitle": True,
        "Name": name,
        "Plugin": {
            "Name": BUILTIN_PLUGIN_NAMES.get(action_uuid, name),
            "UUID": action_uuid,
            "Version": "1.0",
        },
        "Resources": None,
        "Settings": settings,
        "State": action.get("State", 0),
        "States": [
            _make_state(action_uuid, state, images)
            for state in (action.get("States") or [{}])
        ],
        "UUID": action_uuid,
    }


def _convert_page(manifest: dict, path: str, pages: dict) -> str:
    """Convert one 1.0 manifest into a 3.0 page. Returns the page UUID."""
    page_uuid = derive_uuid(path)
    images: dict = {}
    actions = {}
    for position, action in sorted(
        (manifest.get("Actions") or {}).items(), key=lambda kv: int(kv[0])
    ):
        if action is None:
            continue
        coord = pos_to_colrow(position)
        child_path = f"{path}{coord}:{action.get('Name', '')}/"
        actions[coord] = _convert_action(action, child_path, images, pages)

    pages[page_uuid] = {
        "manifest": {
            "Controllers": [{"Actions": actions, "Type": "Keypad"}],
            "Icon": "",
            "Name": "",
        },
        "images": images,
    }
    return page_uuid


def convert_tree(manifest: dict, root_path: str = "/") -> tuple[str, dict]:
    """Convert a 1.0 manifest tree into {page_uuid: {manifest, images}}.

    Returns (root_page_uuid, pages).
    """
    pages: dict = {}
    root_uuid = _convert_page(manifest, root_path, pages)
    return root_uuid, pages


# ---------------------------------------------------------------------------
# Archive assembly
# ---------------------------------------------------------------------------

def collect_required_plugins(pages: dict) -> list:
    """Every distinct action UUID used anywhere in the profile, sorted."""
    found = set()
    for page in pages.values():
        for action in page["manifest"]["Controllers"][0]["Actions"].values():
            found.add(action["UUID"])
    return sorted(found)


def build_entries(
    manifest: dict,
    profile_uuid: str,
    profile_name: str = DEFAULT_PROFILE_NAME,
    device_model: str = DEFAULT_DEVICE_MODEL,
    device_uuid: str = DEFAULT_DEVICE_UUID,
    app_version: str = DEFAULT_APP_VERSION,
    icon_root: Path = Path("icons"),
) -> dict:
    """Build the full {archive_path: bytes} map for a standalone v3 profile."""
    root_page_uuid, pages = convert_tree(manifest)

    profile_uuid = profile_uuid.upper()
    sd_dir = f"Profiles/{profile_uuid}.sdProfile"

    entries: dict = {
        "Profiles/": b"",
        f"{sd_dir}/": b"",
        f"{sd_dir}/Images/": b"",
        f"{sd_dir}/Profiles/": b"",
    }

    profile_manifest = {
        "Device": {"Model": device_model, "UUID": device_uuid},
        "Name": profile_name,
        "Pages": {
            "Current": NULL_UUID,
            "Default": root_page_uuid.lower(),
            "Pages": [root_page_uuid.lower()],
        },
        "Version": "3.0",
    }
    entries[f"{sd_dir}/manifest.json"] = _dump(profile_manifest)

    missing = []
    for page_uuid, page in sorted(pages.items()):
        page_dir = f"{sd_dir}/Profiles/{page_uuid}"
        entries[f"{page_dir}/"] = b""
        entries[f"{page_dir}/Images/"] = b""
        entries[f"{page_dir}/manifest.json"] = _dump(page["manifest"])
        for icon_ref, filename in sorted(page["images"].items()):
            source = resolve_icon(icon_ref, icon_root)
            if source is None:
                missing.append(icon_ref)
                continue
            entries[f"{page_dir}/Images/{filename}"] = source.read_bytes()

    entries["package.json"] = _dump(
        {
            "AppVersion": app_version,
            "DeviceModel": device_model,
            "DeviceSettings": None,
            "FormatVersion": 1,
            "OSType": "Windows",
            "OSVersion": "10.0.26200",
            "RequiredPlugins": collect_required_plugins(pages),
        }
    )

    if missing:
        for ref in sorted(set(missing)):
            print(f"  ! no icon file for {ref}")

    return entries


def _dump(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf8")


def write_archive(entries: dict, output_path: str) -> None:
    """Write the entry map out as a .streamDeckProfile ZIP."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(entries):
            zf.writestr(name, entries[name])


def write_profile(manifest: dict, output_path: str, profile_cfg: dict = None) -> dict:
    """Convert and write a standalone 3.0 profile. Returns the entry map."""
    cfg = profile_cfg or {}
    device = cfg.get("device", {}) or {}
    entries = build_entries(
        manifest,
        profile_uuid=cfg.get("uuid") or derive_uuid("profile:" + cfg.get("name", DEFAULT_PROFILE_NAME)),
        profile_name=cfg.get("name", DEFAULT_PROFILE_NAME),
        device_model=device.get("model", DEFAULT_DEVICE_MODEL),
        device_uuid=device.get("uuid", DEFAULT_DEVICE_UUID),
        icon_root=Path(cfg.get("icon_root", "icons")),
    )
    write_archive(entries, output_path)
    return entries

# builder/profile.py
"""Assemble the .streamDeckProfile ZIP from manifest + icons."""

import json
import zipfile
from pathlib import Path


def collect_icon_paths(manifest: dict) -> set:
    """Recursively collect all Icon references from a manifest."""
    paths = set()
    for action in manifest.get("Actions", {}).values():
        for state in action.get("States", []):
            img = state.get("Image", "")
            if img:
                paths.add(img)
        if "Children" in action:
            paths |= collect_icon_paths(action["Children"])
    return paths


def build_zip(manifest: dict, output_path: str):
    """Write the .streamDeckProfile ZIP file."""
    icon_paths = collect_icon_paths(manifest)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        for icon_ref in icon_paths:
            # icon_ref is like "Icons/plex" or "Icons/actions/nav-home"
            # Map to disk: icons/apps/plex.png, icons/actions/nav-home.png, etc.
            parts = icon_ref.split("/")
            name = parts[-1] + ".png"
            candidates = [
                Path("icons") / "apps" / name,
                Path("icons") / "namespaces" / name,
                Path("icons") / "actions" / name,
            ]
            for candidate in candidates:
                if candidate.exists():
                    zf.write(candidate, icon_ref + ".png")
                    break

# builder/profile.py
"""Assemble the .streamDeckProfile archive.

The archive is written in the Stream Deck 3.0 format; see builder/v3.py for the
layout and for why the 1.0 format this repo used to emit is rejected outright by
Stream Deck 7.5. The page tree the builder modules produce is still the compact
1.0-shaped dict -- it is a convenient intermediate representation and every
builder module and test speaks it -- and v3.py is the single place that turns it
into what the deck will load.
"""

from builder.v3 import write_profile


def collect_icon_paths(manifest: dict) -> set:
    """Recursively collect all Icon references from a page tree."""
    paths = set()
    for action in (manifest.get("Actions") or {}).values():
        if action is None:
            continue
        for state in action.get("States", []):
            img = state.get("Image", "")
            if img:
                paths.add(img)
        if "Children" in action:
            paths |= collect_icon_paths(action["Children"])
    return paths


def build_zip(manifest: dict, output_path: str, profile_cfg: dict = None):
    """Write the .streamDeckProfile ZIP file in 3.0 format."""
    return write_profile(manifest, output_path, profile_cfg)

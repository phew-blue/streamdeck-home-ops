#!/usr/bin/env python3
"""Clear per-key Title and Image overrides from a Stream Deck profile.

    python3 scripts/strip-plugin-overrides.py in.streamDeckProfile out.streamDeckProfile

# Why this exists

Stream Deck treats a Title or Image stored on a key as something the user set
in the Property Inspector, and a plugin cannot override either. The SDK says so
outright about images (key.d.ts): "The image can only be set by the plugin when
the user has not specified a custom image." Titles behave the same way.

The generated profile stores "..." as the Title of every plugin key and a PNG as
its Image. The result is a deck that looks correct and never updates: setTitle
and setImage are called, resolve successfully, and change nothing. There is no
error anywhere -- not in the Stream Deck log, not in the plugin -- so it reads
as the plugin being broken, the network failing, or the profile not being
selected. It is none of those.

Only keys belonging to this plugin are touched. Folder, website and hotkey keys
keep their icons, which is where the profile's artwork actually lives.

The real fix is for the profile generator to stop writing Title and Image on
plugin-driven keys at all; this script is what makes an already-exported
profile usable in the meantime.
"""
import json
import sys
import zipfile

PLUGIN = "homeops"


def strip(obj, counts):
    if isinstance(obj, dict):
        uuid = obj.get("UUID")
        if isinstance(uuid, str) and PLUGIN in uuid:
            for state in obj.get("States") or []:
                if not isinstance(state, dict):
                    continue
                for field in ("Title", "Image"):
                    if field in state:
                        del state[field]
                        counts[field] += 1
        for value in obj.values():
            strip(value, counts)
    elif isinstance(obj, list):
        for value in obj:
            strip(value, counts)


def main(src_path, dst_path):
    counts = {"Title": 0, "Image": 0}
    changed = 0
    with zipfile.ZipFile(src_path) as src, \
            zipfile.ZipFile(dst_path, "w", zipfile.ZIP_DEFLATED) as out:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename.endswith("manifest.json"):
                try:
                    parsed = json.loads(data)
                except ValueError:
                    out.writestr(item, data)
                    continue
                before = dict(counts)
                strip(parsed, counts)
                if counts != before:
                    changed += 1
                    data = json.dumps(parsed, ensure_ascii=False).encode("utf8")
            out.writestr(item, data)

    # Re-open and parse everything: a profile that fails to load is discarded by
    # Stream Deck silently, which is a bad way to find out.
    with zipfile.ZipFile(dst_path) as check:
        for name in check.namelist():
            if name.endswith("manifest.json"):
                json.loads(check.read(name))

    print(f"titles removed   : {counts['Title']}")
    print(f"images removed   : {counts['Image']}")
    print(f"manifests changed: {changed}")
    print(f"wrote {dst_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])

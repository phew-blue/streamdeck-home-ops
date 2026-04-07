#!/usr/bin/env python3
# generate.py
"""Entry point: reads config.yaml, builds .streamDeckProfile."""

import argparse
import yaml
from pathlib import Path
from builder.icons import download_all_icons
from builder.launchers import generate_launchers
from builder.pages import build_namespace_folder
from builder.k8sgrid import build_k8s_grid
from builder.talos import build_talos_page
from builder.landing import build_landing_page
from builder.profile import build_zip


def generate(config: dict, output_path: str = "profile/home-ops.streamDeckProfile"):
    install_path = config.get("install_path", r"C:\StreamDeck-HomeOps")
    kromgo_url = config.get("kromgo_url", "https://kromgo.phew.blue")

    download_all_icons(config)
    generate_launchers(config)

    # Namespace pages (depth=2: landing → k8s grid → namespace)
    ns_manifests = {}
    for ns in config["namespaces"]:
        print(f"Building namespace: {ns['name']} ({len(ns['apps'])} apps)")
        ns_manifests[ns["name"]] = build_namespace_folder(ns, install_path, root_depth=2)

    # K8s namespace grid (depth=1 from landing page)
    k8s_grid = build_k8s_grid(
        ns_manifests=ns_manifests,
        pinned=config.get("pinned", []),
    )

    # Talos nodes page (depth=1 from landing page)
    talos_page = build_talos_page(nodes=config.get("nodes", []))

    # Landing page (top level of our profile)
    landing = build_landing_page(
        k8s_manifest=k8s_grid,
        talos_manifest=talos_page,
        install_path=install_path,
        kromgo_url=kromgo_url,
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    build_zip(landing, output_path)
    print(f"\n✓ Profile written to {output_path}")

    return landing


def embed(config: dict, default_profile: str = "Default Profile.streamDeckProfile"):
    """Generate the home-ops profile then embed it into the Default Profile."""
    import requests
    from builder.embed import embed_home_ops
    from PIL import Image
    import io

    hop_path = "profile/home-ops.streamDeckProfile"
    generate(config, output_path=hop_path)

    # Download and resize Discord server icon for the Home Ops button
    icon_url = "https://cdn.discordapp.com/icons/673534664354430999/a_1824509333499341fd53b3d9389c5660.webp?size=64"
    icon_dest = Path("icons/home-ops.png")
    home_ops_icon = None
    try:
        resp = requests.get(icon_url, timeout=15)
        if resp.status_code == 200:
            img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            img = img.resize((144, 144), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            home_ops_icon = buf.getvalue()
            img.save(icon_dest)
            print("✓ Home Ops icon downloaded")
        else:
            print(f"✗ Home Ops icon not available (HTTP {resp.status_code}), using text label")
    except Exception as e:
        print(f"✗ Home Ops icon error: {e}, using text label")

    print(f"\nEmbedding into {default_profile} ...")
    embed_home_ops(default_profile, hop_path, home_ops_icon=home_ops_icon)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Also embed the home-ops pages into 'Default Profile.streamDeckProfile'",
    )
    parser.add_argument(
        "--default-profile",
        default="Default Profile.streamDeckProfile",
        help="Path to the Default Profile ZIP to embed into (used with --embed)",
    )
    args = parser.parse_args()

    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    if args.embed:
        embed(config, default_profile=args.default_profile)
    else:
        generate(config)

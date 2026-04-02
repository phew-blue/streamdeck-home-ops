# builder/icons.py
"""Icon download and generation for Stream Deck buttons."""

import os
import io
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ICON_SIZE = (144, 144)
DASHBOARD_ICONS_BASE = "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png"

# Maps app name → dashboard-icons filename (where it differs from app name)
ICON_NAME_OVERRIDES = {
    "kube-prometheus-stack": "prometheus",
    "crunchy-postgres": "postgresql",
    "open-webui": "open-webui",
    "home-assistant": "home-assistant",
    "code-server": "code-server",
    "audiobookshelf": "audiobookshelf",
    "qbittorrent": "qbittorrent",
    "netboot-xyz": "netbootxyz",
}


def ensure_dirs():
    Path("icons/apps").mkdir(parents=True, exist_ok=True)
    Path("icons/namespaces").mkdir(parents=True, exist_ok=True)
    Path("icons/actions").mkdir(parents=True, exist_ok=True)


def download_app_icon(app_name: str) -> Path:
    """Download icon from dashboard-icons. Returns path to saved PNG."""
    icon_name = ICON_NAME_OVERRIDES.get(app_name, app_name)
    dest = Path(f"icons/apps/{app_name}.png")
    if dest.exists():
        return dest
    url = f"{DASHBOARD_ICONS_BASE}/{icon_name}.png"
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        img = img.resize(ICON_SIZE, Image.LANCZOS)
        img.save(dest)
        print(f"  ✓ {app_name}")
    else:
        print(f"  ✗ {app_name} (not found, using fallback)")
        dest = _generate_fallback_icon(app_name, "#555555")
    return dest


def _generate_fallback_icon(name: str, color: str) -> Path:
    """Generate a colored tile with initials as fallback."""
    dest = Path(f"icons/apps/{name}.png")
    img = Image.new("RGBA", ICON_SIZE, _hex_to_rgba(color))
    draw = ImageDraw.Draw(img)
    initials = name[:2].upper()
    _draw_centered_text(draw, initials, ICON_SIZE, font_size=52, color="white")
    img.save(dest)
    return dest


def generate_namespace_icon(name: str, color: str) -> Path:
    """Generate a colored namespace tile icon."""
    dest = Path(f"icons/namespaces/{name}.png")
    img = Image.new("RGBA", ICON_SIZE, _hex_to_rgba(color))
    draw = ImageDraw.Draw(img)
    _draw_centered_text(draw, name, ICON_SIZE, font_size=22, color="white")
    img.save(dest)
    return dest


def generate_action_icons():
    """Generate consistent action button icons (status rows, nav buttons)."""
    ensure_dirs()
    _gen_action_icon("status-loading", "#263238", "...", "#90a4ae")
    _gen_action_icon("action-logs", "#1a237e", "LOGS", "#82b1ff")
    _gen_action_icon("action-restart", "#b71c1c", "RESTART", "#ef9a9a")
    _gen_action_icon("action-reconcile", "#1b5e20", "SYNC", "#a5d6a7")
    _gen_action_icon("nav-home", "#212121", "HOME", "#ffffff")
    _gen_action_icon("nav-back", "#212121", "<", "#ffffff")
    _gen_action_icon("nav-next", "#212121", ">", "#ffffff")
    _gen_action_icon("nav-up", "#212121", "UP", "#ffffff")
    _gen_action_icon("nav-down", "#212121", "DOWN", "#ffffff")
    _gen_action_icon("update-profile", "#4a148c", "UPDATE", "#ce93d8")


def _gen_action_icon(name: str, bg: str, label: str, fg: str):
    dest = Path(f"icons/actions/{name}.png")
    if dest.exists():
        return
    img = Image.new("RGBA", ICON_SIZE, _hex_to_rgba(bg))
    draw = ImageDraw.Draw(img)
    _draw_centered_text(draw, label, ICON_SIZE, font_size=36, color=fg)
    img.save(dest)


def _draw_centered_text(draw: ImageDraw.ImageDraw, text: str, size: tuple,
                         font_size: int, color: str):
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except (IOError, OSError):
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size[0] - w) / 2
    y = (size[1] - h) / 2
    draw.text((x, y), text, fill=color, font=font)


def _hex_to_rgba(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)


def download_all_icons(config: dict):
    """Download all app icons specified in config.yaml."""
    ensure_dirs()
    print("Downloading app icons...")
    seen = set()
    for ns in config["namespaces"]:
        for app in ns["apps"]:
            if app["name"] not in seen:
                download_app_icon(app["name"])
                seen.add(app["name"])
    for pinned in config.get("pinned", []):
        if pinned["app"] not in seen:
            download_app_icon(pinned["app"])
            seen.add(pinned["app"])
    print("Generating namespace icons...")
    for ns in config["namespaces"]:
        generate_namespace_icon(ns["name"], ns["color"])
    print("Generating action icons...")
    generate_action_icons()

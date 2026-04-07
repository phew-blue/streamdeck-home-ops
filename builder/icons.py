# builder/icons.py
"""Icon download and generation for Stream Deck buttons."""

import io
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ICON_SIZE = (144, 144)
DASHBOARD_ICONS_BASE = "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png"
SOURCE_DIR = Path("icons/source")

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

# Gradient pairs (c1, c2) for each action icon — diagonal top-left → bottom-right
_GRADIENTS = {
    "nav-home":         ((102, 126, 234), (118,  75, 162)),
    "nav-back":         ((102, 126, 234), (118,  75, 162)),
    "nav-next":         ((102, 126, 234), (118,  75, 162)),
    "nav-up":           ((102, 126, 234), (118,  75, 162)),
    "nav-down":         ((102, 126, 234), (118,  75, 162)),
    "update-profile":   ((240,  80, 200), (130,  60, 220)),
    "action-logs":      (( 79, 172, 254), (  0, 242, 254)),
    "action-restart":   ((248,  87, 166), (255,  88,  88)),
    "action-reconcile": (( 86, 171,  47), (168, 224,  99)),
    "status-loading":   (( 55,  55,  55), ( 90,  90,  90)),
    "node-node":        (( 55,  71,  79), ( 84, 110, 122)),
    "node-pods":        (( 55,  71,  79), ( 84, 110, 122)),
    "node-cpu":         (( 55,  71,  79), ( 84, 110, 122)),
    "node-ram":         (( 55,  71,  79), ( 84, 110, 122)),
}


def ensure_dirs():
    Path("icons/apps").mkdir(parents=True, exist_ok=True)
    Path("icons/namespaces").mkdir(parents=True, exist_ok=True)
    Path("icons/actions").mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Gradient background
# ---------------------------------------------------------------------------

def _gradient_bg(name: str, size: tuple = ICON_SIZE) -> Image.Image:
    c1, c2 = _GRADIENTS.get(name, ((60, 60, 60), (100, 100, 100)))
    w, h = size
    img = Image.new("RGBA", size)
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            t = (x + y) / (w + h - 2)
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            pixels[x, y] = (r, g, b, 255)
    return img


# ---------------------------------------------------------------------------
# Icon compositing
# ---------------------------------------------------------------------------

def _composite_transparent_icon(name: str, source_path: Path) -> Image.Image:
    """Gradient bg + white transparent icon overlaid on top."""
    bg = _gradient_bg(name)
    icon = Image.open(source_path).convert("RGBA")
    icon = icon.resize(ICON_SIZE, Image.LANCZOS)
    bg.paste(icon, mask=icon.split()[3])
    return bg


def _composite_solid_icon(name: str, source_path: Path) -> Image.Image:
    """Replace solid background of an action icon with a gradient,
    keeping the text/foreground pixels as white."""
    bg = _gradient_bg(name)
    icon = Image.open(source_path).convert("RGBA")
    icon = icon.resize(ICON_SIZE, Image.LANCZOS)

    # Background colour = corner pixel
    corner_r, corner_g, corner_b, _ = icon.getpixel((0, 0))
    tolerance = 25

    pixels = list(icon.getdata())
    mask_data = []
    for r, g, b, a in pixels:
        diff = abs(r - corner_r) + abs(g - corner_g) + abs(b - corner_b)
        mask_data.append(min(255, diff * 6) if diff > tolerance else 0)

    mask = Image.new("L", ICON_SIZE)
    mask.putdata(mask_data)

    # Paste white text/shapes (not the original colour, which would be invisible)
    white_layer = Image.new("RGBA", ICON_SIZE, (255, 255, 255, 255))
    bg.paste(white_layer, mask=mask)
    return bg


def _make_action_icon(name: str) -> Image.Image:
    """Choose compositing strategy based on source icon type."""
    src = SOURCE_DIR / f"{name}.png"
    if not src.exists():
        return _fallback_gradient_text(name)

    icon = Image.open(src).convert("RGBA")
    _, _, _, a = icon.split()
    if list(a.getdata()).count(0) > 1000:
        return _composite_transparent_icon(name, src)
    else:
        return _composite_solid_icon(name, src)


def _fallback_gradient_text(name: str) -> Image.Image:
    bg = _gradient_bg(name)
    draw = ImageDraw.Draw(bg)
    label = name.split("-")[-1].upper()
    _draw_centered_text(draw, label, ICON_SIZE, font_size=36, color="white")
    return bg


# ---------------------------------------------------------------------------
# App icon download
# ---------------------------------------------------------------------------

def _download_url(url: str, dest: Path, resize: bool = True) -> bool:
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        if resize:
            img = img.resize(ICON_SIZE, Image.LANCZOS)
        img.save(dest)
        return True
    return False


def download_app_icon(app_name: str) -> Path:
    icon_name = ICON_NAME_OVERRIDES.get(app_name, app_name)
    dest = Path(f"icons/apps/{app_name}.png")
    if dest.exists():
        return dest
    url = f"{DASHBOARD_ICONS_BASE}/{icon_name}.png"
    if _download_url(url, dest):
        print(f"  ✓ {app_name}")
    else:
        print(f"  ✗ {app_name} (not found, using fallback)")
        dest = _generate_fallback_icon(app_name, "#555555")
    return dest


def download_talos_icon() -> Path:
    dest = Path("icons/actions/talos.png")
    url = f"{DASHBOARD_ICONS_BASE}/talos.png"
    if _download_url(url, dest):
        print("  ✓ talos (logo)")
    else:
        _fallback_gradient_text("nav-home").save(dest)
    return dest


def download_k8s_icon() -> Path:
    dest = Path("icons/actions/k8s.png")
    url = f"{DASHBOARD_ICONS_BASE}/kubernetes.png"
    if _download_url(url, dest):
        print("  ✓ k8s (logo)")
    else:
        _fallback_gradient_text("nav-home").save(dest)
    return dest


def _generate_fallback_icon(name: str, color: str) -> Path:
    dest = Path(f"icons/apps/{name}.png")
    img = Image.new("RGBA", ICON_SIZE, _hex_to_rgba(color))
    draw = ImageDraw.Draw(img)
    _draw_centered_text(draw, name[:2].upper(), ICON_SIZE, font_size=52, color="white")
    img.save(dest)
    return dest


def generate_namespace_icon(name: str, color: str) -> Path:
    dest = Path(f"icons/namespaces/{name}.png")
    img = Image.new("RGBA", ICON_SIZE, _hex_to_rgba(color))
    draw = ImageDraw.Draw(img)
    _draw_centered_text(draw, name, ICON_SIZE, font_size=22, color="white")
    img.save(dest)
    return dest


def generate_action_icons():
    """Generate action icons: Stream Deck source icons on gradient backgrounds."""
    ensure_dirs()

    for name in ["nav-home", "nav-back", "nav-next", "nav-up", "nav-down",
                 "update-profile", "action-logs", "action-restart", "action-reconcile"]:
        _make_action_icon(name).save(f"icons/actions/{name}.png")

    for name in ["node-node", "node-pods", "node-cpu", "node-ram", "status-loading"]:
        _fallback_gradient_text(name).save(f"icons/actions/{name}.png")

    print("  ✓ action icons (Stream Deck style, gradient colours)")
    download_talos_icon()
    download_k8s_icon()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _draw_centered_text(draw, text, size, font_size, color):
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except (IOError, OSError):
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size[0] - w) / 2, (size[1] - h) / 2), text, fill=color, font=font)


def _hex_to_rgba(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)


def download_all_icons(config: dict):
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

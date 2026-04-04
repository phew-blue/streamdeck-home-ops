# builder/launchers.py
"""Generate per-app .bat launcher files for Stream Deck actions."""

import os
from pathlib import Path


ACTIONS = {
    "logs": (
        'powershell.exe -NoProfile -ExecutionPolicy Bypass -File '
        '"{scripts_dir}\\logs.ps1" -App "{app}" -Namespace "{namespace}"'
    ),
    "restart": (
        'powershell.exe -NoProfile -ExecutionPolicy Bypass -File '
        '"{scripts_dir}\\restart-pod.ps1" -App "{app}" -Namespace "{namespace}"'
    ),
    "reconcile": (
        'powershell.exe -NoProfile -ExecutionPolicy Bypass -File '
        '"{scripts_dir}\\force-reconcile.ps1" -App "{app}" -Namespace "{namespace}"'
    ),
}


def generate_launchers(config: dict):
    """Generate scripts/launchers/{ns}-{app}-{action}.bat for every app x action."""
    install_path = config.get("install_path", r"C:\StreamDeck-HomeOps")
    scripts_dir = os.path.join(install_path, "scripts")
    out_dir = Path("scripts/launchers")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Update profile launcher
    update_bat = out_dir / "update-profile.bat"
    update_bat.write_text(
        f'@echo off\npowershell.exe -NoProfile -ExecutionPolicy Bypass '
        f'-File "{scripts_dir}\\update-profile.ps1"\n'
    )

    for ns in config["namespaces"]:
        ns_name = ns["name"]
        for app in ns["apps"]:
            app_name = app["name"]
            for action, cmd_template in ACTIONS.items():
                bat_name = f"{ns_name}-{app_name}-{action}.bat"
                cmd = cmd_template.format(
                    scripts_dir=scripts_dir,
                    app=app_name,
                    namespace=ns_name,
                )
                bat_path = out_dir / bat_name
                bat_path.write_text(f"@echo off\n{cmd}\n")

    print(f"✓ Launchers written to scripts/launchers/ ({len(list(out_dir.glob('*.bat')))} files)")

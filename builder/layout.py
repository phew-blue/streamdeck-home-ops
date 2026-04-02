"""Position helpers and manifest factory for Stream Deck XL (8x4)."""

COLS = 8
ROWS = 4
DEVICE_TYPE = 20  # XL


def pos(row: int, col: int) -> str:
    """Return the manifest Actions key for a given 0-indexed row and col."""
    return str(row * COLS + col)


def make_manifest(actions: dict) -> dict:
    """Wrap an actions dict in a full manifest envelope."""
    return {
        "AppearanceVersion": 2,
        "Columns": COLS,
        "DeviceType": DEVICE_TYPE,
        "Rows": ROWS,
        "Version": "1.0",
        "Actions": {k: v for k, v in actions.items() if v is not None},
    }

# tests/test_v3.py
"""Unit tests for the 1.0 page tree -> 3.0 profile conversion."""
import pytest

from builder.v3 import (
    build_entries,
    convert_tree,
    derive_uuid,
    image_filename,
    is_plugin_action,
    pos_to_colrow,
    resolve_icon,
)
from builder.actions import (
    folder_action,
    plugin_status_action,
    single_back_action,
    website_action,
)
from builder.layout import make_manifest, pos


def test_pos_to_colrow():
    assert pos_to_colrow("0") == "0,0"
    assert pos_to_colrow("7") == "7,0"
    assert pos_to_colrow("8") == "0,1"
    assert pos_to_colrow("31") == "7,3"


def test_derive_uuid_is_stable_and_distinct():
    assert derive_uuid("/a/") == derive_uuid("/a/")
    assert derive_uuid("/a/") != derive_uuid("/b/")
    assert derive_uuid("/a/") == derive_uuid("/a/").upper()


def test_image_filename_is_deterministic():
    assert image_filename("Icons/plex") == image_filename("Icons/plex")
    assert image_filename("Icons/plex").endswith("Z.png")


def test_is_plugin_action():
    assert is_plugin_action("com.phew.blue.homeops.status")
    assert not is_plugin_action("com.elgato.streamdeck.system.website")


def test_resolve_icon_handles_the_ns_prefix(tmp_path):
    (tmp_path / "namespaces").mkdir()
    (tmp_path / "namespaces" / "media.png").write_bytes(b"x")
    assert resolve_icon("Icons/ns-media", tmp_path).name == "media.png"


def test_resolve_icon_returns_none_when_absent(tmp_path):
    assert resolve_icon("Icons/nope", tmp_path) is None


@pytest.fixture
def tree():
    inner = make_manifest({
        pos(0, 0): single_back_action("Home", "Icons/actions/nav-home"),
        pos(1, 1): plugin_status_action("plex", "media", "plex", "pods"),
    })
    return make_manifest({
        pos(0, 0): website_action("plex", "https://plex.phew.blue", "Icons/plex"),
        pos(0, 3): folder_action("media", "Icons/ns-media", inner),
        pos(1, 0): None,
    })


def test_convert_tree_extracts_children_into_sibling_pages(tree):
    root, pages = convert_tree(tree)
    assert len(pages) == 2
    root_actions = pages[root]["manifest"]["Controllers"][0]["Actions"]
    child_uuid = root_actions["3,0"]["Settings"]["ProfileUUID"].upper()
    assert child_uuid in pages
    assert "Children" not in root_actions["3,0"]


def test_convert_tree_drops_empty_slots(tree):
    root, pages = convert_tree(tree)
    assert set(pages[root]["manifest"]["Controllers"][0]["Actions"]) == {"0,0", "3,0"}


def test_website_settings_keep_url_not_path(tree):
    root, pages = convert_tree(tree)
    settings = pages[root]["manifest"]["Controllers"][0]["Actions"]["0,0"]["Settings"]
    assert settings["url"] == "https://plex.phew.blue"
    assert "path" not in settings


def test_plugin_state_has_no_title_or_image(tree):
    _root, pages = convert_tree(tree)
    plugin_states = [
        state
        for page in pages.values()
        for action in page["manifest"]["Controllers"][0]["Actions"].values()
        for state in action["States"]
        if is_plugin_action(action["UUID"])
    ]
    assert plugin_states
    for state in plugin_states:
        assert "Title" not in state
        assert "Image" not in state
        assert state["ShowTitle"] is True


def test_non_plugin_state_keeps_its_image(tree):
    root, pages = convert_tree(tree)
    state = pages[root]["manifest"]["Controllers"][0]["Actions"]["0,0"]["States"][0]
    assert state["Image"].startswith("Images/")
    assert state["TitleColor"] == "#ffffff"


def test_build_entries_produces_the_v3_skeleton(tree, tmp_path):
    entries = build_entries(
        tree,
        profile_uuid="AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
        icon_root=tmp_path,
    )
    assert "package.json" in entries
    sd = "Profiles/AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE.sdProfile"
    assert f"{sd}/manifest.json" in entries
    page_manifests = [k for k in entries if k.startswith(f"{sd}/Profiles/")
                      and k.endswith("manifest.json")]
    assert len(page_manifests) == 2

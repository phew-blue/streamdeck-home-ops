"""Tests for action factory functions."""
import pytest
from builder.actions import (
    website_action, folder_action, back_action, multi_back_action,
    open_file_action, plugin_status_action, empty_action
)


def test_website_action_structure():
    a = website_action("Plex", "https://plex.phew.blue", "Icons/plex")
    assert a["UUID"] == "com.elgato.streamdeck.system.website"
    assert a["Settings"]["url"] == "https://plex.phew.blue"
    assert a["States"][0]["Image"] == "Icons/plex"
    assert a["States"][0]["ShowTitle"] is False


def test_folder_action_has_children():
    children = {"AppearanceVersion": 2, "Actions": {}}
    a = folder_action("media", "Icons/ns-media", children)
    assert a["UUID"] == "com.elgato.streamdeck.profile.openchild"
    assert a["Children"] == children
    assert a["States"][0]["ShowTitle"] is True


def test_back_action_depth_1():
    a = back_action(depth=1, icon="Icons/home")
    assert a["UUID"] == "com.elgato.streamdeck.profile.backtoparent"


def test_back_action_depth_3_uses_multi():
    a = back_action(depth=3, icon="Icons/home")
    assert a["UUID"] == "com.elgato.streamdeck.multi"
    assert len(a["Settings"]["actions"]) == 3
    for sub in a["Settings"]["actions"]:
        assert sub["UUID"] == "com.elgato.streamdeck.profile.backtoparent"


def test_open_file_action():
    a = open_file_action("Restart", r"C:\scripts\media-plex-restart.bat", "Icons/restart")
    assert a["UUID"] == "com.elgato.streamdeck.system.open"
    assert a["Settings"]["path"] == r"C:\scripts\media-plex-restart.bat"


def test_plugin_status_action():
    a = plugin_status_action("plex", "media", "plex", "pods")
    assert a["UUID"] == "com.phew.blue.homeops.status"
    assert a["Settings"]["app"] == "plex"
    assert a["Settings"]["namespace"] == "media"
    assert a["Settings"]["metric"] == "pods"


def test_empty_action_is_none():
    assert empty_action() is None

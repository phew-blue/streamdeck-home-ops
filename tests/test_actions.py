"""Tests for action factory functions."""
import pytest
from builder.actions import (
    website_action, folder_action, single_back_action,
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


def test_folder_action_hidden_title():
    children = {"AppearanceVersion": 2, "Actions": {}}
    a = folder_action("Down", "Icons/actions/nav-down", children, show_title=False)
    assert a["States"][0]["ShowTitle"] is False
    assert a["States"][0]["Title"] == ""


def test_single_back_action():
    a = single_back_action("Home", "Icons/home")
    assert a["UUID"] == "com.elgato.streamdeck.profile.backtoparent"


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

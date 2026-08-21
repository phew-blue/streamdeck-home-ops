# tests/test_profile.py
"""Structural checks on the emitted archive.

Stream Deck 7.5 accepts only the 3.0 layout and refuses a 1.0 one with "unknown
file contents", so these tests assert the shape of the archive rather than the
shape of the intermediate page tree.
"""
import json
import zipfile

import pytest
import yaml


@pytest.fixture(scope="module")
def config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def archive(config, tmp_path_factory):
    """Generate the profile once; every test reads the same archive."""
    from generate import generate
    outfile = tmp_path_factory.mktemp("profile") / "test.streamDeckProfile"
    generate(config, output_path=str(outfile))
    return outfile


@pytest.fixture(scope="module")
def profile(archive):
    """Parse the archive into (profile_uuid, profile_manifest, pages, names)."""
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        sd_manifests = [
            n for n in names
            if n.startswith("Profiles/") and n.endswith(".sdProfile/manifest.json")
        ]
        assert len(sd_manifests) == 1, sd_manifests
        sd_key = sd_manifests[0]
        profile_uuid = sd_key.split("/")[1].replace(".sdProfile", "")
        manifest = json.loads(zf.read(sd_key))
        prefix = f"Profiles/{profile_uuid}.sdProfile/Profiles/"
        pages = {
            n[len(prefix):-len("/manifest.json")].upper(): json.loads(zf.read(n))
            for n in names
            if n.startswith(prefix) and n.endswith("/manifest.json")
            and n.count("/") == 4
        }
    return profile_uuid, manifest, pages, names


def _actions(page):
    for controller in page["Controllers"]:
        for coord, action in (controller["Actions"] or {}).items():
            if action:
                yield coord, action


def _all_actions(pages):
    for page_uuid, page in pages.items():
        for coord, action in _actions(page):
            yield page_uuid, coord, action


# --- archive skeleton ------------------------------------------------------

def test_package_json_at_archive_root(archive):
    with zipfile.ZipFile(archive) as zf:
        assert "package.json" in zf.namelist()
        pkg = json.loads(zf.read("package.json"))
    assert pkg["FormatVersion"] == 1
    assert pkg["DeviceModel"] == "20GAT9901"
    assert isinstance(pkg["RequiredPlugins"], list) and pkg["RequiredPlugins"]


def test_no_legacy_1_0_layout(archive):
    """A root manifest.json or an Icons/ dir is what 7.5 rejects outright."""
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    assert "manifest.json" not in names
    assert not [n for n in names if n.startswith("Icons/")]


def test_profile_manifest_is_v3(profile):
    _, manifest, _, _ = profile
    assert manifest["Version"] == "3.0"
    assert manifest["Device"]["Model"] == "20GAT9901"
    assert manifest["Pages"]["Pages"], "profile declares no top-level page"


def test_profile_uuid_is_pinned_to_config(config, profile):
    profile_uuid, manifest, _, _ = profile
    assert profile_uuid == config["profile"]["uuid"].upper()
    assert manifest["Name"] == config["profile"]["name"]


def test_every_profile_has_a_manifest(profile):
    profile_uuid, _, pages, names = profile
    prefix = f"Profiles/{profile_uuid}.sdProfile/Profiles/"
    page_dirs = {n[len(prefix):].split("/")[0].upper() for n in names if n.startswith(prefix)}
    page_dirs.discard("")  # the "Profiles/" directory entry itself
    assert page_dirs == set(pages), page_dirs ^ set(pages)


def test_declared_pages_exist(profile):
    _, manifest, pages, _ = profile
    for page_uuid in manifest["Pages"]["Pages"]:
        assert page_uuid.upper() in pages
    assert manifest["Pages"]["Default"].upper() in pages


# --- nesting ---------------------------------------------------------------

def test_child_profile_references_resolve(profile):
    _, _, pages, _ = profile
    for page_uuid, coord, action in _all_actions(pages):
        if action["UUID"] == "com.elgato.streamdeck.profile.openchild":
            child = action["Settings"]["ProfileUUID"].upper()
            assert child in pages, f"{page_uuid} {coord} -> missing page {child}"


def test_every_page_is_reachable(profile):
    _, manifest, pages, _ = profile
    seen = set()
    stack = [p.upper() for p in manifest["Pages"]["Pages"]]
    while stack:
        page_uuid = stack.pop()
        if page_uuid in seen:
            continue
        seen.add(page_uuid)
        for _c, action in _actions(pages[page_uuid]):
            if action["UUID"] == "com.elgato.streamdeck.profile.openchild":
                stack.append(action["Settings"]["ProfileUUID"].upper())
    assert seen == set(pages), f"orphaned pages: {sorted(set(pages) - seen)}"


def test_k8s_grid_is_a_folder_on_the_landing_page(profile):
    _, manifest, pages, _ = profile
    landing = pages[manifest["Pages"]["Pages"][0].upper()]
    actions = dict(_actions(landing))
    # row 0, col 3 -> "3,0" in 3.0 addressing
    assert "3,0" in actions
    assert actions["3,0"]["UUID"] == "com.elgato.streamdeck.profile.openchild"
    assert actions["3,0"]["Name"] == "K8s"


def test_key_coordinates_fit_an_xl(profile):
    _, _, pages, _ = profile
    for _p, coord, _a in _all_actions(pages):
        col, row = (int(x) for x in coord.split(","))
        assert 0 <= col < 8 and 0 <= row < 4, coord


# --- the reason strip-plugin-overrides.py existed --------------------------

def test_no_plugin_key_carries_title_or_image(profile):
    """A Title or Image on a plugin key makes setTitle/setImage silent no-ops."""
    _, _, pages, _ = profile
    offenders = []
    for page_uuid, coord, action in _all_actions(pages):
        if not action["UUID"].startswith("com.phew.blue.homeops."):
            continue
        for state in action["States"]:
            if "Title" in state or "Image" in state:
                offenders.append(f"{page_uuid} {coord} {action['UUID']}")
    assert not offenders, offenders


def test_plugin_keys_are_actually_present(profile):
    _, _, pages, _ = profile
    used = {a["UUID"] for _p, _c, a in _all_actions(pages)}
    assert {"com.phew.blue.homeops.status",
            "com.phew.blue.homeops.cluster",
            "com.phew.blue.homeops.node"} <= used


# --- images ----------------------------------------------------------------

def test_every_image_reference_resolves(profile, archive):
    profile_uuid, _, pages, _ = profile
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    missing = []
    for page_uuid, coord, action in _all_actions(pages):
        for state in action["States"]:
            ref = state.get("Image", "")
            if not ref:
                continue
            key = f"Profiles/{profile_uuid}.sdProfile/Profiles/{page_uuid}/{ref}"
            if key not in names:
                missing.append(f"{page_uuid} {coord} {ref}")
    assert not missing, missing


def test_required_plugins_covers_every_action_used(profile, archive):
    _, _, pages, _ = profile
    with zipfile.ZipFile(archive) as zf:
        pkg = json.loads(zf.read("package.json"))
    used = {a["UUID"] for _p, _c, a in _all_actions(pages)}
    assert used <= set(pkg["RequiredPlugins"]), used - set(pkg["RequiredPlugins"])


# --- determinism -----------------------------------------------------------

def test_regenerating_is_byte_identical(config, tmp_path, archive):
    """Stable UUIDs: a rerun must not orphan what the deck already imported."""
    from generate import generate
    second = tmp_path / "again.streamDeckProfile"
    generate(config, output_path=str(second))
    with zipfile.ZipFile(archive) as a, zipfile.ZipFile(second) as b:
        assert a.namelist() == b.namelist()
        for name in a.namelist():
            assert a.read(name) == b.read(name), name

# tests/test_profile.py
import zipfile
import json
import pytest
from pathlib import Path
import yaml


@pytest.fixture
def config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def test_generate_produces_valid_zip(config, tmp_path):
    from generate import generate
    outfile = tmp_path / "test.streamDeckProfile"
    generate(config, output_path=str(outfile))
    assert outfile.exists()
    with zipfile.ZipFile(outfile) as zf:
        assert "manifest.json" in zf.namelist()
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["DeviceType"] == 20
        assert manifest["Columns"] == 8
        assert manifest["Rows"] == 4
        assert len(manifest["Actions"]) > 0


def test_manifest_has_k8s_folder(config, tmp_path):
    from generate import generate
    outfile = tmp_path / "test.streamDeckProfile"
    generate(config, output_path=str(outfile))
    with zipfile.ZipFile(outfile) as zf:
        manifest = json.loads(zf.read("manifest.json"))
    # K8s folder at pos 3 (row 0 col 3)
    assert "3" in manifest["Actions"]
    assert manifest["Actions"]["3"]["UUID"] == "com.elgato.streamdeck.profile.openchild"

from __future__ import annotations

import lanzador_pesos as launcher


def test_parse_version_compares_numeric_parts() -> None:
    assert launcher.parse_version("1.10.0") > launcher.parse_version("1.2.9")
    assert launcher.parse_version("v1.2.3") == (1, 2, 3, 0)


def test_stable_channel_skips_prereleases() -> None:
    releases = [
        {"tag_name": "v1.2.0-beta.1", "prerelease": True, "draft": False},
        {"tag_name": "v1.1.0", "prerelease": False, "draft": False},
    ]
    selected = launcher.select_release_from_list(releases, beta_enabled=False)
    assert selected["tag_name"] == "v1.1.0"


def test_beta_channel_can_select_prerelease() -> None:
    releases = [
        {"tag_name": "v1.2.0-beta.1", "prerelease": True, "draft": False},
        {"tag_name": "v1.1.0", "prerelease": False, "draft": False},
    ]
    selected = launcher.select_release_from_list(releases, beta_enabled=True)
    assert selected["tag_name"] == "v1.2.0-beta.1"


def test_manifest_from_release_uses_zip_and_hash_asset(monkeypatch) -> None:
    release = {
        "tag_name": "v1.2.3",
        "prerelease": False,
        "body": "Cambios",
        "assets": [
            {
                "name": "Etiquetado_Pesos_v1.2.3_update.zip",
                "browser_download_url": "https://example.test/update.zip",
            },
            {
                "name": "Etiquetado_Pesos_v1.2.3_update.zip.sha256",
                "browser_download_url": "https://example.test/update.zip.sha256",
            },
        ],
    }
    monkeypatch.setattr(launcher, "read_text_url", lambda _url: "a" * 64 + "  update.zip")

    manifest = launcher.manifest_from_github_release(release)

    assert manifest["version"] == "1.2.3"
    assert manifest["auto_update"]["type"] == "zip"
    assert manifest["auto_update"]["sha256"] == "a" * 64

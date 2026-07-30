from __future__ import annotations

import actualizador_pesos as updater
import lanzador_pesos as launcher
import pytest


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


def test_copy_file_with_retry_replaces_destination_atomically(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.exe"
    destination = tmp_path / "destination.exe"
    source.write_bytes(b"new")
    destination.write_bytes(b"old")
    original_replace = updater.os.replace
    calls = 0

    def replace_after_one_lock(source_path, destination_path):
        nonlocal calls
        calls += 1
        if calls == 1:
            error = OSError("sharing violation")
            error.winerror = 32
            raise error
        return original_replace(source_path, destination_path)

    monkeypatch.setattr(updater.os, "replace", replace_after_one_lock)
    monkeypatch.setattr(updater.time, "sleep", lambda _seconds: None)

    updater.copy_file_with_retry(source, destination)

    assert calls == 2
    assert destination.read_bytes() == b"new"
    assert not list(tmp_path.glob(".destination.exe.update-*"))


def test_copy_file_with_retry_reports_the_locked_file(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.exe"
    destination = tmp_path / "destination.exe"
    source.write_bytes(b"new")
    destination.write_bytes(b"old")
    clock = iter((0.0, updater.FILE_REPLACE_TIMEOUT_SECONDS + 1.0))

    def always_locked(_source_path, _destination_path):
        error = OSError("sharing violation")
        error.winerror = 32
        raise error

    monkeypatch.setattr(updater.os, "replace", always_locked)
    monkeypatch.setattr(updater.time, "monotonic", lambda: next(clock))

    with pytest.raises(updater.UpdateFileLockedError, match="destination.exe"):
        updater.copy_file_with_retry(source, destination)


def test_access_denied_is_treated_as_a_retriable_file_lock() -> None:
    error = OSError("access denied")
    error.winerror = 5

    assert updater._is_file_lock_error(error)


def test_local_salazon_csv_is_preserved_during_updates(tmp_path) -> None:
    source = tmp_path / "package" / "config" / "config_salazon.csv"
    destination = tmp_path / "installed" / "config" / "config_salazon.csv"
    source.parent.mkdir(parents=True)
    destination.parent.mkdir(parents=True)
    source.write_text("CODIGO;Nombre\n100;CATALOGO PUBLICADO\n", encoding="utf-8")
    destination.write_text("CODIGO;Nombre\n200;CATALOGO LOCAL\n", encoding="utf-8")

    updater.copy_file_preserving_user_data(source, destination, destination.parents[1])

    assert destination.read_text(encoding="utf-8") == "CODIGO;Nombre\n200;CATALOGO LOCAL\n"


def test_wait_for_process_exit_waits_until_parent_has_finished(monkeypatch) -> None:
    states = iter((True, False))
    monkeypatch.setattr(updater, "is_process_running", lambda _pid: next(states))
    monkeypatch.setattr(updater.time, "sleep", lambda _seconds: None)

    assert updater.wait_for_process_exit(123, timeout=1.0)


def test_launcher_passes_application_and_launcher_pids_to_updater(monkeypatch, tmp_path) -> None:
    received: list[str] = []
    updater_path = tmp_path / "Etiquetado_Pesos_Updater.exe"
    monkeypatch.setattr(launcher, "wait_for_process_exit", lambda _pid, **_kwargs: True)
    monkeypatch.setattr(launcher, "copy_updater_to_temp", lambda: updater_path)
    monkeypatch.setattr(launcher, "write_update_status", lambda **_values: None)
    monkeypatch.setattr(launcher, "log_update_check", lambda _message: None)
    monkeypatch.setattr(launcher.os, "getpid", lambda: 456)

    def capture_popen(args, **_kwargs):
        received.extend(args)
        return None

    monkeypatch.setattr(launcher.subprocess, "Popen", capture_popen)

    assert launcher.start_package_update("zip", "https://example.test/update.zip", "update.zip", "a" * 64, "1.0.9", app_pid=123) == 0
    assert received[-4:] == ["--wait-pid", "123", "--wait-pid", "456"]

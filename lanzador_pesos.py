from __future__ import annotations

import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


APP_NAME = "Etiquetado Pesos"
MAIN_EXE = "Etiquetado_Pesos_App.exe"
MAIN_SCRIPT = "app_etiquetado_pesos.py"
UPDATER_EXE = "Etiquetado_Pesos_Updater.exe"
UPDATER_SCRIPT = "actualizador_pesos.py"
LOCAL_VERSION_FILE = "version_local.json"
UPDATE_CONFIG_FILE = "update_config.json"
DEFAULT_VERSION_URL = "https://raw.githubusercontent.com/irodriguezfino/etiquetas_pesos/main/version.json"
DEFAULT_GITHUB_OWNER = "irodriguezfino"
DEFAULT_GITHUB_REPO = "etiquetas_pesos"
HTTP_TIMEOUT_SECONDS = 20

UPDATE_LOG_FILE = (
    Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
    / APP_NAME
    / "logs"
    / "launcher_update_check.log"
)

MB_OK = 0x00000000
MB_YESNO = 0x00000004
MB_ICONERROR = 0x00000010
MB_ICONQUESTION = 0x00000020
MB_ICONWARNING = 0x00000030
MB_ICONINFORMATION = 0x00000040
IDYES = 6


def show_warning(title: str, text: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, text, title, MB_OK | MB_ICONWARNING)


def show_error(title: str, text: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, text, title, MB_OK | MB_ICONERROR)


def show_info(title: str, text: str) -> None:
    ctypes.windll.user32.MessageBoxW(None, text, title, MB_OK | MB_ICONINFORMATION)


def ask_yes_no(title: str, text: str) -> bool:
    return ctypes.windll.user32.MessageBoxW(None, text, title, MB_YESNO | MB_ICONQUESTION) == IDYES


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def log_update_check(message: str) -> None:
    try:
        UPDATE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with UPDATE_LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(f"[{stamp}] {message}\n")
    except Exception:
        pass


def update_status_file() -> Path:
    return UPDATE_LOG_FILE.parent / "update_status.json"


def read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_update_status(**values) -> None:
    status = read_json(update_status_file())
    status.update(values)
    status["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        update_status_file().parent.mkdir(parents=True, exist_ok=True)
        with update_status_file().open("w", encoding="utf-8") as handle:
            json.dump(status, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except Exception:
        pass


def read_json_url(url: str) -> dict:
    try:
        request = Request(
            url,
            headers={
                "User-Agent": "Etiquetado-Pesos-Updater",
                "Accept": "application/vnd.github+json,application/json,text/plain,*/*",
            },
        )
        with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read(4 * 1024 * 1024)
        data = json.loads(raw.decode("utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        log_update_check(f"No se pudo leer version.json online: {exc}")
        return {}


def read_json_list_url(url: str) -> list[dict]:
    try:
        request = Request(
            url,
            headers={
                "User-Agent": "Etiquetado-Pesos-Updater",
                "Accept": "application/vnd.github+json,application/json,*/*",
            },
        )
        with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read(4 * 1024 * 1024)
        data = json.loads(raw.decode("utf-8-sig"))
        return data if isinstance(data, list) else []
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        log_update_check(f"No se pudo leer lista de GitHub Releases: {exc}")
        return []


def read_text_url(url: str, max_bytes: int = 128 * 1024) -> str:
    try:
        request = Request(
            url,
            headers={
                "User-Agent": "Etiquetado-Pesos-Updater",
                "Accept": "text/plain,application/json,*/*",
            },
        )
        with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return response.read(max_bytes).decode("utf-8-sig", errors="replace")
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, OSError) as exc:
        log_update_check(f"No se pudo leer recurso remoto: {exc}")
        return ""


def filename_from_url(url: str, default: str) -> str:
    try:
        name = Path(unquote(urlparse(url).path)).name
        return name or default
    except Exception:
        return default


def parse_version(value: str) -> tuple[int, int, int, int]:
    parts = re.findall(r"\d+", str(value or "0"))
    nums = [int(part) for part in parts[:4]]
    while len(nums) < 4:
        nums.append(0)
    return tuple(nums)


def version_from_tag(tag_name: str) -> str:
    match = re.search(r"(\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.\-]+)?)", str(tag_name or ""))
    return match.group(1) if match else "0.0.0"


def get_local_version() -> str:
    data = read_json(app_dir() / LOCAL_VERSION_FILE)
    return str(data.get("version", "0.0.0"))


def configured_version_url() -> str:
    config = read_json(app_dir() / UPDATE_CONFIG_FILE)
    for key in ("manifest_url", "version_url", "remote_version_url", "github_version_url"):
        value = str(config.get(key, "")).strip()
        if value:
            return value
    return DEFAULT_VERSION_URL


def configured_update_source() -> dict:
    config = read_json(app_dir() / UPDATE_CONFIG_FILE)
    owner = str(config.get("github_owner") or DEFAULT_GITHUB_OWNER).strip()
    repo = str(config.get("github_repo") or DEFAULT_GITHUB_REPO).strip()
    channel = str(config.get("channel") or "stable").strip().lower()
    beta_enabled = bool(config.get("enable_beta")) or channel in {"beta", "preview", "prerelease"}
    return {
        "owner": owner,
        "repo": repo,
        "channel": channel,
        "beta_enabled": beta_enabled,
        "manifest_url": str(config.get("manifest_url") or config.get("version_url") or "").strip(),
    }


def github_release_api_url(owner: str, repo: str, beta_enabled: bool) -> str:
    base = f"https://api.github.com/repos/{owner}/{repo}/releases"
    return base if beta_enabled else f"{base}/latest"


def release_asset(release: dict, name: str) -> dict:
    for asset in release.get("assets") or []:
        if str(asset.get("name", "")).lower() == name.lower():
            return asset if isinstance(asset, dict) else {}
    return {}


def first_update_zip_asset(release: dict, remote_version: str) -> dict:
    expected = f"Etiquetado_Pesos_v{remote_version}_update.zip".lower()
    for asset in release.get("assets") or []:
        name = str(asset.get("name", ""))
        lowered = name.lower()
        if lowered == expected or lowered.endswith("_update.zip"):
            return asset if isinstance(asset, dict) else {}
    return {}


def select_release_from_list(releases: list[dict], beta_enabled: bool) -> dict:
    best: dict = {}
    for release in releases:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        if release.get("prerelease") and not beta_enabled:
            continue
        if not best or parse_version(version_from_tag(release.get("tag_name", ""))) > parse_version(version_from_tag(best.get("tag_name", ""))):
            best = release
    return best


def manifest_from_github_release(release: dict) -> dict:
    remote_version = version_from_tag(str(release.get("tag_name", "")))
    manifest_asset = release_asset(release, "update-manifest.json")
    if manifest_asset.get("browser_download_url"):
        manifest = read_json_url(str(manifest_asset["browser_download_url"]))
        if manifest:
            manifest.setdefault("version", remote_version)
            manifest.setdefault("notes", str(release.get("body") or "").strip())
            return manifest

    zip_asset = first_update_zip_asset(release, remote_version)
    if not zip_asset.get("browser_download_url"):
        return {}

    zip_name = str(zip_asset.get("name") or f"Etiquetado_Pesos_v{remote_version}_update.zip")
    sha256 = ""
    hash_asset = release_asset(release, f"{zip_name}.sha256") or release_asset(release, "SHA256SUMS.txt")
    if hash_asset.get("browser_download_url"):
        hash_text = read_text_url(str(hash_asset["browser_download_url"]))
        hash_match = re.search(r"\b([a-fA-F0-9]{64})\b", hash_text)
        sha256 = hash_match.group(1).lower() if hash_match else ""

    return {
        "version": remote_version,
        "tag_name": str(release.get("tag_name") or ""),
        "prerelease": bool(release.get("prerelease")),
        "notes": str(release.get("body") or "").strip(),
        "auto_update": {
            "type": "zip",
            "url": str(zip_asset.get("browser_download_url") or ""),
            "file": zip_name,
            "sha256": sha256,
        },
    }


def read_remote_update_manifest() -> dict:
    source = configured_update_source()
    if source["manifest_url"]:
        return read_json_url(source["manifest_url"])

    owner = source["owner"]
    repo = source["repo"]
    beta_enabled = bool(source["beta_enabled"])
    url = github_release_api_url(owner, repo, beta_enabled)
    log_update_check(f"Consultando GitHub Releases: {url}; beta={beta_enabled}")
    if beta_enabled:
        release = select_release_from_list(read_json_list_url(url), beta_enabled=True)
    else:
        release = read_json_url(url)
        if release.get("draft") or release.get("prerelease"):
            release = {}
    if not release:
        return {}
    return manifest_from_github_release(release)


def creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def launch_main() -> subprocess.Popen | None:
    root = app_dir()
    env = os.environ.copy()
    env["ETIQUETADO_SKIP_AUTO_UPDATE"] = "1"
    main_exe = root / MAIN_EXE
    if main_exe.exists():
        return subprocess.Popen(
            [str(main_exe)],
            cwd=str(root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags(),
        )

    script = root / MAIN_SCRIPT
    if script.exists():
        return subprocess.Popen(
            [sys.executable, str(script)],
            cwd=str(root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags(),
        )

    show_error(
        APP_NAME,
        "No se encuentra una instalacion valida.\n\n"
        f"Ejecutable esperado:\n{main_exe}\n\n"
        f"Script esperado:\n{script}\n\n"
        "Reinstala la aplicacion con el ultimo instalador disponible.",
    )
    return None


def close_windows_for_pid(pid: int) -> None:
    if pid <= 0:
        return
    user32 = ctypes.windll.user32
    WM_CLOSE = 0x0010

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_handler(hwnd, _lparam):
        window_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if window_pid.value == pid and user32.IsWindowVisible(hwnd):
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        return True

    user32.EnumWindows(enum_handler, 0)


def wait_for_process_exit(pid: int, timeout_seconds: float = 12.0) -> bool:
    if pid <= 0:
        return True
    kernel32 = ctypes.windll.kernel32
    SYNCHRONIZE = 0x00100000
    PROCESS_TERMINATE = 0x0001
    handle = kernel32.OpenProcess(SYNCHRONIZE | PROCESS_TERMINATE, False, pid)
    if not handle:
        return True
    try:
        close_windows_for_pid(pid)
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            result = kernel32.WaitForSingleObject(handle, 250)
            if result == 0:
                return True
        return False
    finally:
        kernel32.CloseHandle(handle)


def terminate_process(pid: int) -> None:
    if pid <= 0:
        return
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=creation_flags(),
        )
    except Exception:
        pass


def copy_updater_to_temp() -> Path:
    root = app_dir()
    temp_root = Path(tempfile.gettempdir()) / "Etiquetado_Pesos_Update"
    helper_dir = temp_root / f"helper_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    helper_dir.mkdir(parents=True, exist_ok=True)

    if getattr(sys, "frozen", False):
        updater_src = root / UPDATER_EXE
        if not updater_src.exists():
            raise FileNotFoundError(f"No se encuentra el actualizador:\n\n{updater_src}")
        updater_dst = helper_dir / UPDATER_EXE
        shutil.copy2(updater_src, updater_dst)
        return updater_dst

    updater_src = root / UPDATER_SCRIPT
    if not updater_src.exists():
        raise FileNotFoundError(f"No se encuentra el actualizador:\n\n{updater_src}")
    updater_dst = helper_dir / UPDATER_SCRIPT
    shutil.copy2(updater_src, updater_dst)
    return updater_dst


def start_package_update(
    package_type: str,
    package_url: str,
    package_name: str,
    expected_sha256: str,
    expected_version: str,
    app_pid: int = 0,
) -> int:
    try:
        if app_pid:
            log_update_check(f"Cerrando aplicacion antes de actualizar: pid={app_pid}")
            if not wait_for_process_exit(app_pid):
                terminate_process(app_pid)
                time.sleep(0.75)
        updater_path = copy_updater_to_temp()
        if updater_path.suffix.lower() == ".exe":
            args = [
                str(updater_path),
                "--package",
                package_type,
                package_url,
                package_name,
                expected_sha256,
                str(app_dir()),
                str(expected_version),
            ]
        else:
            args = [
                sys.executable,
                str(updater_path),
                "--package",
                package_type,
                package_url,
                package_name,
                expected_sha256,
                str(app_dir()),
                str(expected_version),
            ]
        subprocess.Popen(
            args,
            cwd=str(updater_path.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags(),
        )
        log_update_check(
            "Actualizador iniciado: "
            f"type={package_type}; version={expected_version}; package={package_name}; url={package_url}"
        )
        write_update_status(
            status="updater_started",
            message="Actualizador iniciado.",
            target_version=expected_version,
            package_type=package_type,
            package_name=package_name,
            package_url=package_url,
            expected_sha256=expected_sha256,
        )
        return 0
    except Exception as exc:
        log_update_check(f"No se pudo preparar el actualizador: {exc}")
        write_update_status(status="error", message=f"No se pudo preparar el actualizador: {exc}")
        show_error(APP_NAME, f"No se pudo preparar el actualizador:\n\n{exc}")
        return 1


def update_package_from_manifest(remote_data: dict, remote_version: str) -> tuple[str, str, str, str]:
    auto_update = remote_data.get("auto_update")
    if not isinstance(auto_update, dict):
        auto_update = {}

    package_type = str(
        auto_update.get("type")
        or auto_update.get("package_type")
        or remote_data.get("package_type")
        or "zip"
    ).strip().lower()
    package_url = str(
        auto_update.get("url")
        or auto_update.get("package_url")
        or remote_data.get("package_url")
        or ""
    ).strip()
    expected_sha256 = str(
        auto_update.get("sha256")
        or remote_data.get("sha256")
        or ""
    ).strip().lower()
    package_name = str(
        auto_update.get("file")
        or auto_update.get("package")
        or remote_data.get("package")
        or ""
    ).strip()

    if not package_name:
        package_name = filename_from_url(package_url, f"Etiquetado_Pesos_v{remote_version}_update.zip")

    return package_type, package_url, package_name, expected_sha256


def recently_skipped_version(remote_version: str, minutes: int = 30) -> bool:
    status = read_json(update_status_file())
    if status.get("target_version") != remote_version:
        return False
    if status.get("status") not in {"cancelled", "error", "failed"}:
        return False
    try:
        stamp = time.strptime(str(status.get("updated_at", "")), "%Y-%m-%d %H:%M:%S")
        age_seconds = time.time() - time.mktime(stamp)
        return age_seconds < minutes * 60
    except Exception:
        return False


def check_and_update(manual: bool = False, app_pid: int = 0) -> bool:
    local_version = get_local_version()
    source = configured_update_source()
    log_update_check(
        "Comprobando actualizaciones online: "
        f"owner={source['owner']}; repo={source['repo']}; channel={source['channel']}; "
        f"manifest_url={source['manifest_url'] or 'github_releases'}"
    )
    write_update_status(
        status="checking",
        message="Comprobando actualizaciones.",
        local_version=local_version,
        log_file=str(UPDATE_LOG_FILE),
        channel=source["channel"],
    )

    remote_data = read_remote_update_manifest()
    if not remote_data:
        write_update_status(status="offline", message="No se pudo leer el manifiesto remoto.")
        if manual:
            show_warning(APP_NAME, "No se pudo consultar GitHub ahora.\n\nSe mantiene la version instalada.")
        return False

    remote_version = str(remote_data.get("version", "0.0.0"))
    if bool(remote_data.get("prerelease")) and not source["beta_enabled"]:
        log_update_check(f"Release preliminar ignorada en canal estable: {remote_version}")
        write_update_status(status="up_to_date", message="Version preliminar ignorada.", remote_version=remote_version)
        if manual:
            show_info(APP_NAME, f"No hay actualizaciones estables disponibles.\n\nVersion instalada: {local_version}")
        return False

    log_update_check(f"Version local={local_version}; version remota={remote_version}")
    write_update_status(
        status="checked",
        message="Comprobacion completada.",
        local_version=local_version,
        remote_version=remote_version,
        channel=source["channel"],
    )

    if parse_version(remote_version) <= parse_version(local_version):
        log_update_check("No hay actualizacion aplicable.")
        write_update_status(status="up_to_date", message="No hay actualizacion disponible.", remote_version=remote_version)
        if manual:
            show_info(APP_NAME, f"No hay actualizaciones disponibles.\n\nVersion instalada: {local_version}")
        return False

    if not manual and recently_skipped_version(remote_version):
        log_update_check(f"Se omite aviso automatico reciente para version {remote_version}.")
        return False

    package_type, package_url, package_name, expected_sha256 = update_package_from_manifest(remote_data, remote_version)
    if not package_url or not expected_sha256 or package_type != "zip":
        write_update_status(
            status="invalid_manifest",
            message="Canal remoto incompleto o no admitido.",
            remote_version=remote_version,
            package_type=package_type,
            package_url=package_url,
        )
        show_warning(
            APP_NAME,
            "Se ha detectado una version nueva, pero el canal de actualizacion no es valido.\n\n"
            "Por seguridad se abrira la version instalada actualmente.",
        )
        return False

    notes = str(remote_data.get("notes", "")).strip()
    msg = (
        f"Hay una actualizacion disponible de {APP_NAME}.\n\n"
        f"Version instalada: {local_version}\n"
        f"Version disponible: {remote_version}\n\n"
    )
    if notes:
        msg += f"Notas:\n{notes}\n\n"
    msg += "Pulsa Si para descargarla e instalarla ahora. La aplicacion se abrira despues de actualizar."

    if not ask_yes_no(APP_NAME, msg):
        log_update_check("Usuario cancelo la actualizacion.")
        write_update_status(
            status="cancelled",
            message="Usuario cancelo la actualizacion.",
            target_version=remote_version,
            package_type=package_type,
            package_name=package_name,
            package_url=package_url,
        )
        return False

    start_package_update(package_type, package_url, package_name, expected_sha256, remote_version, app_pid=app_pid)
    return True


def main() -> int:
    manual = "--check-update" in sys.argv
    check_only = "--check-only" in sys.argv
    app_pid = 0
    if "--app-pid" in sys.argv:
        try:
            app_pid = int(sys.argv[sys.argv.index("--app-pid") + 1])
        except Exception:
            app_pid = 0
    try:
        if manual:
            check_and_update(manual=True, app_pid=app_pid)
            return 0
        if check_only:
            check_and_update(manual=False, app_pid=app_pid)
            return 0

        process = launch_main()
        if process is None:
            return 1
        time.sleep(4.0)
        check_and_update(manual=False, app_pid=process.pid)
        return 0
    except Exception as exc:
        show_warning(
            APP_NAME,
            "No se pudo comprobar correctamente si hay actualizaciones.\n\n"
            f"Detalle: {exc}\n\n"
            "Se abrira la version instalada actualmente.",
        )
        return 0 if launch_main() else 1


if __name__ == "__main__":
    raise SystemExit(main())

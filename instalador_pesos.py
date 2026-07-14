from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tkinter import messagebox


APP_NAME = "Etiquetado Pesos"
LAUNCHER_EXE = "Etiquetado_Pesos.exe"
INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / APP_NAME


def payload_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "payload"
    return Path(__file__).resolve().parent / "dist" / "Etiquetado_Pesos_Instalado"


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    if not getattr(sys, "frozen", False):
        return False
    try:
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, "", None, 1)
        return int(result) > 32
    except Exception:
        return False


def should_preserve(destination: Path, install_dir: Path) -> bool:
    if not destination.exists():
        return False
    try:
        relative = destination.relative_to(install_dir).as_posix().lower()
    except ValueError:
        return False
    preserved = {
        "config_usuario.json",
        "update_config.json",
        "config/plantilla_etiqueta_pesos.json",
        "config/editor_password.txt",
    }
    return relative in preserved or relative.startswith("config/backups/") or relative.startswith("exportaciones/")


def copy_payload(source_dir: Path, install_dir: Path) -> None:
    if not source_dir.exists():
        raise FileNotFoundError(f"No se encuentra el contenido del instalador:\n\n{source_dir}")
    install_dir.mkdir(parents=True, exist_ok=True)
    for source in source_dir.rglob("*"):
        relative = source.relative_to(source_dir)
        destination = install_dir / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        if should_preserve(destination, install_dir):
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def grant_user_permissions(install_dir: Path) -> None:
    try:
        subprocess.run(
            ["icacls", str(install_dir), "/grant", "*S-1-5-32-545:(OI)(CI)M", "/T"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass


def create_shortcut(install_dir: Path) -> None:
    desktop = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop" / f"{APP_NAME}.lnk"
    target = install_dir / LAUNCHER_EXE
    command = (
        "$shortcut=(New-Object -ComObject WScript.Shell).CreateShortcut("
        + repr(str(desktop))
        + "); "
        "$shortcut.TargetPath="
        + repr(str(target))
        + "; "
        "$shortcut.WorkingDirectory="
        + repr(str(install_dir))
        + "; "
        "$shortcut.IconLocation="
        + repr(f"{target},0")
        + "; "
        "$shortcut.Save()"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass


def launch_app(install_dir: Path) -> None:
    launcher = install_dir / LAUNCHER_EXE
    if launcher.exists():
        subprocess.Popen(
            [str(launcher)],
            cwd=str(install_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


def main() -> int:
    try:
        source_dir = payload_dir()
        copy_payload(source_dir, INSTALL_DIR)
        (INSTALL_DIR / "exportaciones").mkdir(parents=True, exist_ok=True)
        (INSTALL_DIR / "config").mkdir(parents=True, exist_ok=True)
        create_shortcut(INSTALL_DIR)
        messagebox.showinfo(
            APP_NAME,
            "Instalacion completada correctamente.\n\n"
            f"Carpeta:\n{INSTALL_DIR}\n\n"
            "La aplicacion se abrira ahora.",
        )
        launch_app(INSTALL_DIR)
        return 0
    except Exception as exc:
        messagebox.showerror(APP_NAME, f"No se pudo completar la instalacion:\n\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

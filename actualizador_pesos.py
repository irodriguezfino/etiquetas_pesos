from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import tkinter as tk
from tkinter import messagebox, ttk


APP_NAME = "Etiquetado Pesos"
LAUNCHER_EXE = "Etiquetado_Pesos.exe"
LOCAL_VERSION_FILE = "version_local.json"
HTTP_TIMEOUT_SECONDS = 20
UPDATE_LOG_FILE = (
    Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
    / APP_NAME
    / "logs"
    / "updater.log"
)
UPDATE_STATUS_FILE = UPDATE_LOG_FILE.parent / "update_status.json"


def creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def log_update(message: str) -> None:
    try:
        UPDATE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with UPDATE_LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(f"[{stamp}] {message}\n")
    except Exception:
        pass


def read_update_status() -> dict:
    try:
        with UPDATE_STATUS_FILE.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_update_status(**values) -> None:
    status = read_update_status()
    status.update(values)
    status["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        UPDATE_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with UPDATE_STATUS_FILE.open("w", encoding="utf-8") as handle:
            json.dump(status, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except Exception:
        pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def download_file(url: str, target: Path, progress_callback=None, cancel_event: threading.Event | None = None) -> None:
    log_update(f"Descargando paquete: url={url}; target={target}")
    request = Request(url, headers={"User-Agent": "Etiquetado-Pesos-Updater"})
    target.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response, target.open("wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        while True:
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError("Actualizacion cancelada por el usuario.")
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            downloaded += len(chunk)
            if progress_callback is not None:
                progress_callback(downloaded, total)
    log_update(f"Descarga completada: target={target}; bytes={target.stat().st_size}")


def unique_temp_package(name: str) -> Path:
    temp_dir = Path(tempfile.gettempdir()) / "Etiquetado_Pesos_Update"
    base = Path(name or "Etiquetado_Pesos_Update.zip").name
    suffix = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    path = Path(base)
    return temp_dir / f"{path.stem}_{suffix}{path.suffix or '.zip'}"


def read_installed_version(install_dir: Path) -> str:
    try:
        with (install_dir / LOCAL_VERSION_FILE).open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        return str(data.get("version", "")).strip()
    except Exception:
        return ""


def wait_for_installed_version(install_dir: Path, expected_version: str = "", timeout: float = 12.0) -> None:
    if not expected_version:
        return
    deadline = time.time() + timeout
    while time.time() < deadline:
        if read_installed_version(install_dir) == expected_version:
            return
        time.sleep(0.35)
    current = read_installed_version(install_dir) or "desconocida"
    raise RuntimeError(
        "La actualizacion no dejo la version esperada.\n\n"
        f"Version esperada: {expected_version}\n"
        f"Version encontrada: {current}"
    )


def launch_app(install_dir: Path) -> None:
    launcher = install_dir / LAUNCHER_EXE
    if not launcher.exists():
        raise FileNotFoundError(f"No se encuentra el lanzador actualizado:\n\n{launcher}")
    subprocess.Popen(
        [str(launcher)],
        cwd=str(install_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags(),
    )


def safe_extract_zip(zip_path: Path, target_dir: Path) -> Path:
    extract_dir = target_dir / f"extract_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    log_update(f"Extrayendo ZIP: zip={zip_path}; extract_dir={extract_dir}")
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            destination = (extract_dir / member.filename).resolve()
            if not str(destination).lower().startswith(str(extract_dir.resolve()).lower()):
                raise RuntimeError("El paquete de actualizacion contiene rutas no validas.")
        archive.extractall(extract_dir)

    children = [child for child in extract_dir.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        log_update(f"ZIP extraido con carpeta raiz: source_dir={children[0]}")
        return children[0]
    log_update(f"ZIP extraido sin carpeta raiz unica: source_dir={extract_dir}")
    return extract_dir


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


def copy_file_preserving_user_data(source: Path, destination: Path, install_dir: Path) -> None:
    if should_preserve(destination, install_dir):
        log_update(f"Conservado archivo local: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree_preserving_user_data(source_dir: Path, destination_dir: Path, install_dir: Path) -> None:
    for source in source_dir.rglob("*"):
        if source.name == "__pycache__":
            continue
        relative = source.relative_to(source_dir)
        destination = destination_dir / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        else:
            copy_file_preserving_user_data(source, destination, install_dir)


def copy_package_files(source_dir: Path, install_dir: Path) -> None:
    skip_names = {"__pycache__", "build", "dist"}
    log_update(f"Copiando paquete: source_dir={source_dir}; install_dir={install_dir}")
    for source in source_dir.iterdir():
        if source.name in skip_names:
            continue
        destination = install_dir / source.name
        if source.is_dir():
            copy_tree_preserving_user_data(source, destination, install_dir)
        else:
            copy_file_preserving_user_data(source, destination, install_dir)
    log_update("Copia de paquete completada.")


class UpdateWindow:
    def __init__(
        self,
        package_type: str,
        package_url: str,
        package_name: str,
        expected_sha256: str,
        install_dir: Path,
        expected_version: str,
    ) -> None:
        self.package_type = package_type.lower().strip() or "zip"
        self.package_url = package_url
        self.package_name = package_name
        self.expected_sha256 = expected_sha256.lower().strip()
        self.install_dir = install_dir
        self.expected_version = expected_version
        self.error_text = ""
        self.finished_ok = False
        self.cancel_requested = threading.Event()

        self.root = tk.Tk()
        self.root.title(f"Actualizando {APP_NAME}")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.request_cancel)
        self.root.configure(bg="#F6F8FC")

        frame = ttk.Frame(self.root, padding=24)
        frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(frame, text=f"Actualizando {APP_NAME}", font=("Segoe UI", 15, "bold")).grid(row=0, column=0, sticky="w")
        self.status = tk.StringVar(value="Preparando la actualizacion. No cierres esta ventana.")
        ttk.Label(frame, textvariable=self.status, font=("Segoe UI", 10), wraplength=430).grid(row=1, column=0, sticky="w", pady=(12, 12))
        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=430, maximum=100)
        self.progress.grid(row=2, column=0, sticky="ew")
        self.cancel_button = ttk.Button(frame, text="Cancelar", command=self.request_cancel)
        self.cancel_button.grid(row=3, column=0, sticky="e", pady=(12, 0))
        ttk.Label(frame, text="La aplicacion se abrira automaticamente al finalizar.", font=("Segoe UI", 9)).grid(row=4, column=0, sticky="w", pady=(12, 0))
        self.progress.start(12)
        self.center()

    def center(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = max((self.root.winfo_screenwidth() - width) // 2, 0)
        y = max((self.root.winfo_screenheight() - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def post_status(self, text: str) -> None:
        self.root.after(0, lambda: self.status.set(text))

    def post_progress(self, downloaded: int, total: int) -> None:
        def update() -> None:
            if total > 0:
                self.progress.configure(mode="determinate")
                self.progress.stop()
                self.progress["value"] = min(100, downloaded * 100 / total)
                self.status.set(f"Descargando el paquete de actualizacion... {downloaded * 100 // total}%")
            else:
                self.progress.configure(mode="indeterminate")

        self.root.after(0, update)

    def request_cancel(self) -> None:
        self.cancel_requested.set()
        self.cancel_button.configure(state="disabled")
        self.status.set("Cancelando la actualizacion...")

    def run(self) -> int:
        threading.Thread(target=self.install, daemon=True).start()
        self.root.mainloop()
        return 0 if self.finished_ok else 1

    def install(self) -> None:
        try:
            if not self.package_url:
                raise RuntimeError("No se ha recibido el paquete de actualizacion.")
            if self.package_type != "zip":
                raise RuntimeError("Las actualizaciones automaticas solo admiten ZIP.")

            log_update(
                "Inicio de actualizacion: "
                f"type={self.package_type}; expected_version={self.expected_version}; "
                f"package={self.package_name}; url={self.package_url}; sha256={self.expected_sha256}; "
                f"install_dir={self.install_dir}"
            )
            write_update_status(
                status="updating",
                message="Actualizacion en curso.",
                target_version=self.expected_version,
                package_type=self.package_type,
                package_name=self.package_name,
                package_url=self.package_url,
                expected_sha256=self.expected_sha256,
                updater_log=str(UPDATE_LOG_FILE),
            )

            temp_dir = Path(tempfile.gettempdir()) / "Etiquetado_Pesos_Update"
            package = unique_temp_package(self.package_name)
            self.post_status("Descargando el paquete de actualizacion...")
            download_file(self.package_url, package, progress_callback=self.post_progress, cancel_event=self.cancel_requested)
            if self.cancel_requested.is_set():
                raise RuntimeError("Actualizacion cancelada por el usuario.")

            self.post_status("Validando la descarga...")
            actual_sha256 = sha256_file(package)
            log_update(f"Hash descarga: esperado={self.expected_sha256}; obtenido={actual_sha256}")
            if self.expected_sha256 and actual_sha256 != self.expected_sha256:
                write_update_status(
                    status="failed",
                    message="El hash del paquete descargado no coincide.",
                    target_version=self.expected_version,
                    expected_sha256=self.expected_sha256,
                    actual_sha256=actual_sha256,
                )
                raise RuntimeError(
                    "El paquete descargado no coincide con el hash esperado.\n\n"
                    f"Hash esperado: {self.expected_sha256}\n"
                    f"Hash obtenido: {actual_sha256}"
                )

            self.post_status("Preparando archivos...")
            source_dir = safe_extract_zip(package, temp_dir)
            self.post_status("Aplicando la actualizacion...")
            copy_package_files(source_dir, self.install_dir)

            self.post_status("Comprobando la version instalada...")
            wait_for_installed_version(self.install_dir, self.expected_version)
            write_update_status(
                status="updated",
                message="Actualizacion aplicada correctamente.",
                local_version=self.expected_version,
                target_version=self.expected_version,
                package_type=self.package_type,
                package_name=self.package_name,
                package_url=self.package_url,
            )

            self.post_status("Abriendo la aplicacion actualizada...")
            launch_app(self.install_dir)
            log_update("Aplicacion actualizada abierta correctamente.")
            self.finished_ok = True
            self.root.after(500, self.root.destroy)
        except Exception as exc:
            self.error_text = str(exc)
            log_update(f"ERROR actualizando: {exc}")
            status = "cancelled" if self.cancel_requested.is_set() else "failed"
            write_update_status(
                status=status,
                message=str(exc),
                target_version=self.expected_version,
                package_type=self.package_type,
                package_name=self.package_name,
                package_url=self.package_url,
            )
            self.root.after(0, self.show_error)

    def show_error(self) -> None:
        self.progress.stop()
        if self.cancel_requested.is_set():
            self.status.set("Actualizacion cancelada.")
            messagebox.showinfo(
                APP_NAME,
                "La actualizacion se ha cancelado.\n\nPuedes volver a buscar actualizaciones cuando quieras.",
                parent=self.root,
            )
            self.root.destroy()
            return
        self.status.set("No se pudo completar la actualizacion.")
        messagebox.showerror(
            APP_NAME,
            "No se pudo completar la actualizacion.\n\n"
            f"Detalle: {self.error_text}\n\n"
            "Vuelve a intentarlo o instala la ultima version manualmente.",
            parent=self.root,
        )
        self.root.destroy()


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--package":
        if len(sys.argv) < 8:
            messagebox.showerror(APP_NAME, "No se han recibido los datos del paquete de actualizacion.")
            return 1
        try:
            return UpdateWindow(
                package_type=sys.argv[2].strip(),
                package_url=sys.argv[3].strip(),
                package_name=sys.argv[4].strip(),
                expected_sha256=sys.argv[5].strip(),
                install_dir=Path(sys.argv[6]).resolve(),
                expected_version=str(sys.argv[7]).strip(),
            ).run()
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"No se pudo preparar la actualizacion:\n\n{exc}")
            return 1

    messagebox.showerror(APP_NAME, "No se ha recibido un paquete de actualizacion valido.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

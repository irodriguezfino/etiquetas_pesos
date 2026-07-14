from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageTk

from editor_etiquetas import CanvasButton, LabelTemplateEditor, ModernScrollBar
from estilos_suite import (
    BG,
    BORDER,
    FINURA_LOGO,
    MUTED,
    PRIMARY_BLUE,
    RODRIGUEZ_LOGO,
    SURFACE,
    TEXT,
    ToolTip,
    center_window,
    configure_style,
    set_window_icon,
)
from logica_etiquetas import (
    LABEL_TEMPLATE_PATH,
    SALAZON_CONFIG_PATH,
    BoxEtiqueta,
    RangoSalazon,
    article_name_without_weight_range,
    default_windows_printer,
    expand_labels,
    list_windows_printers,
    load_salazon_ranges,
    print_labels_windows,
    render_label,
    reset_label_template,
    save_label_contact_sheet,
    salazon_ranges_for_article,
    unique_article_options,
)


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
EXPORTS_DIR = APP_DIR / "exportaciones"
STATE_PATH = APP_DIR / "config_usuario.json"
VERSION_PATH = APP_DIR / "version_local.json"
APP_NAME = "Etiquetado Pesos"
LAUNCHER_EXE = "Etiquetado_Pesos.exe"
LAUNCHER_SCRIPT = "lanzador_pesos.py"


class PesoLabelTemplateEditor(LabelTemplateEditor):
    REQUIRED_IDS = {"titulo", "articulo", "albaran", "partida", "rango_pesos"}
    STRUCTURE_IDS = {"outer_border", "header_bar", "titulo", "linea_articulo", "linea_albaran", "linea_partida"}
    VARIABLE_CHOICES = (
        "titulo",
        "articulo_codigo",
        "articulo_nombre",
        "articulo",
        "albaran",
        "numero_albaran",
        "partida",
        "numero_partida",
        "rango_pesos",
        "rango_peso",
        "etiquetas",
        "pie",
    )
    ELEMENT_LABELS = {
        "outer_border": "Borde exterior",
        "header_bar": "Cabecera negra",
        "titulo": "Titulo",
        "articulo": "Articulo",
        "albaran": "Albaran",
        "partida": "Partida",
        "rango_label": "Rotulo rango",
        "rango_pesos": "Rango de pesos",
        "pie": "Pie de etiqueta",
        "linea_articulo": "Linea articulo",
        "linea_albaran": "Linea albaran",
        "linea_partida": "Linea partida",
    }
    VARIABLE_LABELS = {
        "titulo": "Titulo",
        "articulo_codigo": "Codigo articulo",
        "articulo_nombre": "Nombre articulo",
        "articulo": "Articulo",
        "albaran": "Numero de albaran",
        "numero_albaran": "Numero de albaran",
        "partida": "Numero de partida",
        "numero_partida": "Numero de partida",
        "rango_pesos": "Rango de pesos",
        "rango_peso": "Rango de pesos",
        "etiquetas": "Copias",
        "pie": "Pie calculado",
    }
    FIELD_PRESETS = (
        ("Articulo", "articulo_nombre", "ARTICULO"),
        ("Albaran", "albaran", "ALBARAN"),
        ("Partida", "partida", "PARTIDA"),
        ("Rango pesos", "rango_pesos", "RANGO DE PESOS"),
    )
    FOOTER_PRESETS = (
        "{articulo_codigo} | ALB {albaran} | PART {partida}",
        "ALBARAN {albaran} | PARTIDA {partida}",
        "{articulo_nombre}",
    )
    QUICK_VARIABLES = (
        ("Articulo", "articulo_nombre"),
        ("Alb.", "albaran"),
        ("Part.", "partida"),
        ("Rango", "rango_pesos"),
    )

    def _sample_box(self) -> BoxEtiqueta:
        if callable(self.sample_box_provider):
            try:
                box = self.sample_box_provider()
                if box is not None:
                    return box
            except Exception:
                pass
        return BoxEtiqueta(
            box_numero=1,
            lote="P-260630",
            articulo_codigo="607",
            articulo_nombre="JAMON DE CEBO IBERICO 10 - 12 KG",
            fecha_recepcion=date.today(),
            fecha_entrada=date.today(),
            fecha_salida=date.today(),
            dia_salida="",
            dias_sal=0,
            unidades=0,
            total_piezas_rango=0,
            rango_min=10.0,
            rango_max=12.0,
            rango_real_min=10.0,
            rango_real_max=12.0,
            etiquetas=1,
            pesos=(),
            albaran="A-12345",
            partida="P-260630",
            rango_pesos="10 - 12 kg",
        )

    def _sample_values(self) -> dict[str, str]:
        box = self._sample_box()
        return {
            "titulo": "ETIQUETA PESOS",
            "articulo_codigo": box.articulo_codigo,
            "articulo_nombre": box.articulo_nombre,
            "articulo": box.articulo_nombre,
            "albaran": box.albaran,
            "numero_albaran": box.albaran,
            "partida": box.partida,
            "numero_partida": box.partida,
            "rango_peso": box.rango_pesos,
            "rango_pesos": box.rango_pesos,
            "etiquetas": str(box.etiquetas),
            "pie": f"{box.articulo_codigo} | ALB {box.albaran} | PART {box.partida}",
        }


class EtiquetadoPesosApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {self._current_version()}")
        self.geometry("1180x760")
        self.minsize(980, 650)
        self.configure(bg=BG)
        configure_style(self)
        set_window_icon(self)

        self.article_values: list[tuple[str, str, str]] = []
        self.salazon_ranges: tuple[RangoSalazon, ...] = ()
        self.range_values: list[RangoSalazon] = []
        self.current_image: Image.Image | None = None
        self.current_photo: ImageTk.PhotoImage | None = None
        self.current_label: BoxEtiqueta | None = None
        self.template_editor: PesoLabelTemplateEditor | None = None

        self.var_articulo = tk.StringVar()
        self.var_albaran = tk.StringVar()
        self.var_partida = tk.StringVar()
        self.var_rango = tk.StringVar()
        self.var_etiquetas = tk.StringVar(value="1")
        self.var_printer = tk.StringVar()
        self.status = tk.StringVar(value="Selecciona un articulo para comenzar.")
        self.validation = tk.StringVar(value="Pendiente")

        self._load_state()
        self._load_articles()
        self._build_menu()
        self._build_ui()
        self._load_printers()
        self._bind_shortcuts()
        center_window(self)
        self.after(100, self._refresh_ranges_for_article)
        self.after(4500, self._check_updates_auto)

    def _load_state(self) -> None:
        if not STATE_PATH.exists():
            return
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        self.var_albaran.set(str(data.get("albaran", "")))
        self.var_partida.set(str(data.get("partida", "")))
        self.var_etiquetas.set(str(data.get("etiquetas", "1")))
        self.var_printer.set(str(data.get("impresora", "")))

    def _save_state(self) -> None:
        data = {
            "albaran": self.var_albaran.get().strip(),
            "partida": self.var_partida.get().strip(),
            "etiquetas": self.var_etiquetas.get().strip() or "1",
            "impresora": self.var_printer.get().strip(),
        }
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_articles(self) -> None:
        try:
            self.salazon_ranges = load_salazon_ranges(SALAZON_CONFIG_PATH)
            self.article_values = unique_article_options(SALAZON_CONFIG_PATH)
        except Exception as exc:
            self.salazon_ranges = ()
            self.article_values = []
            self.status.set(str(exc))

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-g>", lambda _e: self.generate_preview())
        self.bind("<Control-p>", lambda _e: self.print_labels())
        self.bind("<Control-Alt-d>", lambda _e: self.open_template_editor())
        self.bind("<Control-Alt-D>", lambda _e: self.open_template_editor())
        self.bind("<Escape>", lambda _e: self.focus())

    def _current_version(self) -> str:
        try:
            data = json.loads(VERSION_PATH.read_text(encoding="utf-8-sig"))
            return str(data.get("version", "0.0.0")).strip() or "0.0.0"
        except Exception:
            return "0.0.0"

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(label="Buscar actualizaciones", command=self._check_updates_manual)
        tools_menu.add_separator()
        tools_menu.add_command(label="Restaurar plantilla", command=self.reset_template)
        menubar.add_cascade(label="Herramientas", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Acerca de", command=self._show_about)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        self.configure(menu=menubar)

    def _launcher_command(self, manual: bool) -> list[str]:
        args = ["--app-pid", str(os.getpid())]
        if manual:
            args.insert(0, "--check-update")
        else:
            args.insert(0, "--check-only")

        launcher = APP_DIR / LAUNCHER_EXE
        if launcher.exists():
            return [str(launcher), *args]

        script = APP_DIR / LAUNCHER_SCRIPT
        return [sys.executable, str(script), *args]

    def _run_update_check(self, manual: bool) -> None:
        script = APP_DIR / LAUNCHER_SCRIPT
        launcher = APP_DIR / LAUNCHER_EXE
        if not launcher.exists() and not script.exists():
            if manual:
                messagebox.showwarning(APP_NAME, "No se encuentra el lanzador de actualizaciones.", parent=self)
            return

        try:
            subprocess.Popen(
                self._launcher_command(manual),
                cwd=str(APP_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as exc:
            if manual:
                messagebox.showerror(APP_NAME, f"No se pudo iniciar la comprobacion:\n\n{exc}", parent=self)

    def _check_updates_manual(self) -> None:
        self._run_update_check(manual=True)

    def _check_updates_auto(self) -> None:
        if os.environ.get("ETIQUETADO_SKIP_AUTO_UPDATE") == "1":
            return
        self._run_update_check(manual=False)

    def _show_about(self) -> None:
        messagebox.showinfo(
            f"Acerca de {APP_NAME}",
            f"{APP_NAME}\nVersion {self._current_version()}\n\n"
            "Aplicacion de etiquetado de pesos con actualizaciones desde GitHub Releases.",
            parent=self,
        )

    def _load_logo(self, path: Path, max_width: int, max_height: int) -> ImageTk.PhotoImage | None:
        try:
            if not path.exists():
                return None
            image = Image.open(path)
            image.thumbnail((max_width, max_height), Image.LANCZOS)
            return ImageTk.PhotoImage(image)
        except Exception:
            return None

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll = ModernScrollBar(self, command=canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scroll.set)

        main = ttk.Frame(canvas, padding=18, style="App.TFrame")
        window = canvas.create_window((0, 0), window=main, anchor="nw")
        main.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))

        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        self._build_header(main)

        body = ttk.Frame(main, style="App.TFrame")
        body.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        body.columnconfigure(0, weight=1, uniform="body")
        body.columnconfigure(1, weight=1, uniform="body")
        body.rowconfigure(0, weight=1)

        self._build_input_panel(body)
        self._build_preview_panel(body)
        self._build_status(main)

    def _build_header(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent, padding=16, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        left_logo = self._load_logo(RODRIGUEZ_LOGO, 140, 54)
        right_logo = self._load_logo(FINURA_LOGO, 120, 48)
        if left_logo:
            self.left_logo = left_logo
            ttk.Label(header, image=left_logo, background=SURFACE).grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 18))

        title_box = ttk.Frame(header, style="Header.TFrame")
        title_box.grid(row=0, column=1, sticky="ew")
        ttk.Label(title_box, text="Etiquetado pesos", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="Etiqueta manual para articulo y rango de pesos; albaran y partida son opcionales.", style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))

        if right_logo:
            self.right_logo = right_logo
            ttk.Label(header, image=right_logo, background=SURFACE).grid(row=0, column=2, rowspan=2, sticky="e", padx=(18, 0))

    def _build_input_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Datos de etiqueta", padding=14, style="Section.TLabelframe")
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel.columnconfigure(1, weight=1)

        ttk.Label(panel, text="Articulo", style="Surface.TLabel").grid(row=0, column=0, sticky="w")
        self.article_combo = ttk.Combobox(panel, textvariable=self.var_articulo, values=self._article_display_values(), height=14)
        self.article_combo.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        self.article_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_ranges_for_article())
        self.article_combo.bind("<KeyRelease>", self._filter_articles)
        ToolTip(self.article_combo, "Escribe parte del nombre y selecciona el articulo.")

        ttk.Label(panel, text="Rango de pesos", style="Surface.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.range_combo = ttk.Combobox(panel, textvariable=self.var_rango, values=(), height=8, state="readonly")
        self.range_combo.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(10, 0))
        self.range_combo.bind("<<ComboboxSelected>>", lambda _e: self._validate_silently())
        ToolTip(self.range_combo, "Selecciona el rango disponible para el articulo elegido.")

        rows = (
            ("Numero de albaran (opcional)", self.var_albaran, False),
            ("Numero de partida (opcional)", self.var_partida, False),
            ("Etiquetas", self.var_etiquetas, True),
        )
        for index, (label, variable, with_stepper) in enumerate(rows, start=2):
            ttk.Label(panel, text=label, style="Surface.TLabel").grid(row=index, column=0, sticky="w", pady=(10, 0))
            if with_stepper:
                stepper = ttk.Frame(panel, style="Surface.TFrame")
                stepper.grid(row=index, column=1, sticky="ew", padx=(12, 0), pady=(10, 0))
                stepper.columnconfigure(1, weight=1)
                CanvasButton(stepper, text="-", command=lambda: self.adjust_labels(-1), variant="secondary", width=38, height=34).grid(row=0, column=0, sticky="w")
                entry = ttk.Entry(stepper, textvariable=variable, justify="center")
                entry.grid(row=0, column=1, sticky="ew", padx=6)
                CanvasButton(stepper, text="+", command=lambda: self.adjust_labels(1), variant="secondary", width=38, height=34).grid(row=0, column=2, sticky="e")
            else:
                entry = ttk.Entry(panel, textvariable=variable)
                entry.grid(row=index, column=1, sticky="ew", padx=(12, 0), pady=(10, 0))
            entry.bind("<KeyRelease>", lambda _e: self._validate_silently())

        ttk.Label(panel, text="Impresora", style="Surface.TLabel").grid(row=5, column=0, sticky="w", pady=(10, 0))
        self.printer_combo = ttk.Combobox(panel, textvariable=self.var_printer, values=(), height=8)
        self.printer_combo.grid(row=5, column=1, sticky="ew", padx=(12, 0), pady=(10, 0))

        actions = ttk.Frame(panel, style="Surface.TFrame")
        actions.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        actions.columnconfigure(0, weight=1)
        CanvasButton(actions, text="Generar vista", command=self.generate_preview, variant="primary", width=142, height=40).grid(row=0, column=0, sticky="w")
        CanvasButton(actions, text="Imprimir", command=self.print_labels, variant="dark", width=110, height=40).grid(row=0, column=1, sticky="e", padx=(8, 0))

        secondary = ttk.Frame(panel, style="Surface.TFrame")
        secondary.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        CanvasButton(secondary, text="Guardar PNG", command=self.save_preview, variant="secondary", width=120, height=34).pack(side="left")

        ttk.Label(panel, textvariable=self.validation, style="Result.TLabel", wraplength=480, justify="left").grid(row=8, column=0, columnspan=2, sticky="ew", pady=(18, 0))

        table_box = ttk.Frame(panel, style="Surface.TFrame")
        table_box.grid(row=9, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        panel.rowconfigure(9, weight=1)
        columns = ("articulo", "albaran", "partida", "rango", "etiquetas")
        self.table = ttk.Treeview(table_box, columns=columns, show="headings", height=5)
        for col, text, width in (
            ("articulo", "Articulo", 190),
            ("albaran", "Albaran", 90),
            ("partida", "Partida", 90),
            ("rango", "Rango", 90),
            ("etiquetas", "Etiquetas", 70),
        ):
            self.table.heading(col, text=text)
            self.table.column(col, width=width, anchor="w")
        self.table.pack(fill="both", expand=True)

    def _build_preview_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Vista previa etiqueta", padding=14, style="Section.TLabelframe")
        panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        panel.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)

        self.preview_label = tk.Label(
            panel,
            text="Genera la vista previa para comprobar la etiqueta.",
            bg="white",
            fg=MUTED,
            relief="solid",
            bd=1,
            padx=20,
            pady=20,
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew")

    def _build_status(self, parent: ttk.Frame) -> None:
        status = ttk.Frame(parent, padding=(12, 8), style="Surface.TFrame")
        status.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        status.columnconfigure(0, weight=1)
        ttk.Label(status, textvariable=self.status, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(status, text=f"Articulos: {SALAZON_CONFIG_PATH}", style="Muted.TLabel").grid(row=0, column=1, sticky="e")

    def _article_display_values(self) -> list[str]:
        return [display for _code, _name, display in self.article_values]

    def _range_display_values(self) -> list[str]:
        values: list[str] = []
        for item in self.range_values:
            if item.range_label not in values:
                values.append(item.range_label)
        return values

    def _filter_articles(self, _event=None) -> None:
        typed = self.var_articulo.get().strip().lower()
        if not typed:
            values = self._article_display_values()
        else:
            values = [
                display
                for code, name, display in self.article_values
                if typed in code.lower() or typed in name.lower()
            ]
        self.article_combo.configure(values=values[:80])
        self._refresh_ranges_for_article()

    def _selected_article(self) -> tuple[str, str, str] | None:
        raw = self.var_articulo.get().strip()
        if not raw:
            return None
        for code, name, display in self.article_values:
            if raw == display:
                return code, name, display
        digits = re.match(r"^\s*(\d+)", raw)
        if digits:
            code = digits.group(1)
            for item in self.article_values:
                if item[0] == code:
                    return item
        lowered = raw.lower()
        matches = [item for item in self.article_values if lowered in item[0].lower() or lowered in item[1].lower()]
        return matches[0] if len(matches) == 1 else None

    def _refresh_ranges_for_article(self) -> None:
        selected = self._selected_article()
        if not selected:
            self.range_values = []
            self.var_rango.set("")
            if hasattr(self, "range_combo"):
                self.range_combo.configure(values=())
            self._validate_silently()
            return
        code, _name, _display = selected
        ranges = salazon_ranges_for_article(code, self.salazon_ranges)
        selected_name = _name.lower()
        self.range_values = [item for item in ranges if article_name_without_weight_range(item.articulo_nombre).lower() == selected_name]
        if not self.range_values:
            self.range_values = list(ranges)
        displays = self._range_display_values()
        if hasattr(self, "range_combo"):
            self.range_combo.configure(values=displays)
        if self.var_rango.get() not in displays:
            self.var_rango.set(displays[0] if displays else "")
        self._validate_silently()

    def _selected_range(self) -> RangoSalazon | None:
        raw = self.var_rango.get().strip()
        if not raw:
            return None
        for item in self.range_values:
            if raw == item.range_label:
                return item
        matches = [item for item in self.range_values if raw.lower() in item.range_label.lower()]
        return matches[0] if len(matches) == 1 else None

    def _validate_silently(self) -> bool:
        self.current_label = None
        try:
            self._read_inputs()
        except Exception as exc:
            self.validation.set(f"Pendiente: {exc}")
            return False
        self.validation.set("Listo para generar e imprimir.")
        return True

    def adjust_labels(self, delta: int) -> None:
        try:
            current = int(self.var_etiquetas.get().strip() or "1")
        except ValueError:
            current = 1
        self.var_etiquetas.set(str(max(1, current + delta)))
        self._validate_silently()

    def _read_inputs(self) -> tuple[str, str, str, str, str, int]:
        selected = self._selected_article()
        if not selected:
            raise ValueError("selecciona un articulo valido")
        code, name, _display = selected
        selected_range = self._selected_range()
        if not selected_range:
            raise ValueError("selecciona un rango de pesos")
        albaran = self.var_albaran.get().strip().upper()
        partida = self.var_partida.get().strip().upper()
        rango = selected_range.range_label
        try:
            etiquetas = int(self.var_etiquetas.get().strip() or "1")
        except ValueError as exc:
            raise ValueError("las etiquetas deben ser un numero entero") from exc
        if etiquetas <= 0:
            raise ValueError("las etiquetas deben ser mayores que cero")
        return code, name, albaran, partida, rango, etiquetas

    def _range_numbers(self, rango: str) -> tuple[float, float]:
        numbers = re.findall(r"\d+(?:[,.]\d+)?", rango)
        if len(numbers) >= 2:
            return float(numbers[0].replace(",", ".")), float(numbers[1].replace(",", "."))
        if len(numbers) == 1:
            value = float(numbers[0].replace(",", "."))
            clean = rango.strip()
            if clean.startswith("<"):
                return 0.0, value
            if clean.startswith(">") or clean.startswith("+"):
                return value, 999.0
        return 0.0, 0.0

    def _build_label(self) -> BoxEtiqueta:
        code, name, albaran, partida, rango, etiquetas = self._read_inputs()
        low, high = self._range_numbers(rango)
        today = date.today()
        return BoxEtiqueta(
            box_numero=1,
            lote=partida,
            articulo_codigo=code,
            articulo_nombre=name,
            fecha_recepcion=today,
            fecha_entrada=today,
            fecha_salida=today,
            dia_salida="",
            dias_sal=0,
            unidades=0,
            total_piezas_rango=0,
            rango_min=low,
            rango_max=high,
            rango_real_min=low,
            rango_real_max=high,
            etiquetas=etiquetas,
            pesos=(),
            albaran=albaran,
            partida=partida,
            rango_pesos=rango,
        )

    def generate_preview(self) -> None:
        try:
            label = self._build_label()
        except Exception as exc:
            messagebox.showerror("Datos incompletos", str(exc), parent=self)
            self.status.set(str(exc))
            self._validate_silently()
            return
        self.current_label = label
        self.current_image = render_label(label, dpi=140)
        preview = self.current_image.copy()
        preview.thumbnail((430, 610), Image.LANCZOS)
        self.current_photo = ImageTk.PhotoImage(preview)
        self.preview_label.configure(image=self.current_photo, text="", padx=6, pady=6)
        self._fill_table(label)
        self._save_state()
        albaran_text = label.albaran or "sin albaran"
        partida_text = label.partida or "sin partida"
        self.status.set(f"Vista previa generada: {label.articulo_codigo} | {albaran_text} | {partida_text} | {label.rango_pesos}")

    def _fill_table(self, label: BoxEtiqueta) -> None:
        self.table.delete(*self.table.get_children())
        self.table.insert("", "end", values=(label.articulo_nombre, label.albaran, label.partida, label.rango_pesos, label.etiquetas))

    def _ensure_label(self) -> BoxEtiqueta | None:
        if self.current_label is None:
            try:
                self.current_label = self._build_label()
            except Exception as exc:
                messagebox.showerror("Datos incompletos", str(exc), parent=self)
                return None
        return self.current_label

    def save_preview(self) -> None:
        label = self._ensure_label()
        if label is None:
            return
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        safe_partida = re.sub(r"[^A-Za-z0-9_-]+", "_", label.partida) or "partida"
        path = filedialog.asksaveasfilename(
            title="Guardar etiqueta como PNG",
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            initialdir=str(EXPORTS_DIR),
            initialfile=f"etiqueta_pesos_{safe_partida}.png",
        )
        if not path:
            return
        save_label_contact_sheet(expand_labels([label]), Path(path), dpi=160)
        self.status.set(f"Etiqueta guardada: {path}")

    def print_labels(self) -> None:
        if self.current_label is None:
            messagebox.showinfo("Vista previa pendiente", "Genera la vista previa antes de imprimir.", parent=self)
            self.status.set("Genera la vista previa antes de imprimir.")
            return
        label = self.current_label
        printer = self.var_printer.get().strip()
        if not printer:
            messagebox.showerror("Impresora", "Selecciona una impresora.", parent=self)
            return
        total = len(expand_labels([label]))
        if not messagebox.askyesno("Confirmar impresion", f"Se enviaran {total} etiquetas a:\n\n{printer}\n\nContinuar?", parent=self):
            return
        try:
            printed = print_labels_windows([label], printer)
        except Exception as exc:
            messagebox.showerror("Error imprimiendo", str(exc), parent=self)
            self.status.set(str(exc))
            return
        self._save_state()
        self.status.set(f"Etiquetas enviadas a impresion: {printed}")

    def open_template_editor(self) -> str:
        password_path = LABEL_TEMPLATE_PATH.parent / "editor_password.txt"
        expected = "admin"
        try:
            if password_path.exists():
                value = password_path.read_text(encoding="utf-8").strip()
                if value:
                    expected = value
        except Exception:
            expected = "admin"
        answer = simpledialog.askstring("Acceso administrador", "Contraseña del editor de etiquetas:", show="*", parent=self)
        if answer is None:
            return "break"
        if answer != expected:
            messagebox.showerror("Acceso denegado", "Contraseña incorrecta.", parent=self)
            return "break"
        if self.template_editor is not None and self.template_editor.winfo_exists():
            self.template_editor.lift()
            self.template_editor.focus_force()
            return "break"
        self.template_editor = PesoLabelTemplateEditor(self, on_saved=self._on_template_saved, sample_box_provider=self._editor_sample_label, printer_provider=lambda: self.var_printer.get().strip())
        self.template_editor.protocol("WM_DELETE_WINDOW", self._close_template_editor)
        return "break"

    def _close_template_editor(self) -> None:
        if self.template_editor is not None:
            if hasattr(self.template_editor, "request_close") and not self.template_editor.request_close():
                return
            if self.template_editor is not None and self.template_editor.winfo_exists():
                self.template_editor.destroy()
        self.template_editor = None

    def _editor_sample_label(self) -> BoxEtiqueta:
        try:
            return self._build_label()
        except Exception:
            today = date.today()
            return BoxEtiqueta(
                box_numero=1,
                lote="P-260630",
                articulo_codigo="607",
                articulo_nombre="JAMON DE CEBO IBERICO 10 - 12 KG",
                fecha_recepcion=today,
                fecha_entrada=today,
                fecha_salida=today,
                dia_salida="",
                dias_sal=0,
                unidades=0,
                total_piezas_rango=0,
                rango_min=10.0,
                rango_max=12.0,
                rango_real_min=10.0,
                rango_real_max=12.0,
                etiquetas=1,
                pesos=(),
                albaran="A-12345",
                partida="P-260630",
                rango_pesos="10 - 12 kg",
            )

    def _on_template_saved(self) -> None:
        self.status.set("Plantilla de etiqueta guardada.")
        if self.current_label is not None:
            self.generate_preview()

    def reset_template(self) -> None:
        if not messagebox.askyesno("Restaurar plantilla", "Se restaurara la plantilla de pesos por defecto. Continuar?", parent=self):
            return
        reset_label_template()
        self.status.set("Plantilla restaurada.")
        if self.current_label is not None:
            self.generate_preview()

    def _load_printers(self) -> None:
        printers = list_windows_printers()
        self.printer_combo.configure(values=printers)
        if not self.var_printer.get():
            self.var_printer.set(default_windows_printer() or (printers[0] if printers else ""))


def main() -> None:
    app = EtiquetadoPesosApp()
    app.mainloop()


if __name__ == "__main__":
    main()

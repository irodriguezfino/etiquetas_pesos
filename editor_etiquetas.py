from __future__ import annotations

import os
import calendar
import json
import re
import sys
import traceback
from dataclasses import replace
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageTk

from estilos_suite import (
    ACCENT_RED,
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
    ARTICULOS_PATH,
    BASE_LABEL_HEIGHT,
    BASE_LABEL_WIDTH,
    BoxEtiqueta,
    CITIZEN_LABEL_SIZE_PRESETS,
    DEFAULT_LABEL_TEMPLATE,
    DEFAULT_DPI,
    LABEL_TEMPLATE_PATH,
    SALAZON_CONFIG_PATH,
    ResultadoGeneracion,
    RangoSalazon,
    SAFE_MARGIN_MAX_MM,
    SAFE_MARGIN_MIN_MM,
    build_boxes,
    calculate_exit_date,
    default_windows_printer,
    expand_labels,
    format_decimal,
    holidays_for_year,
    list_windows_printers,
    load_label_template,
    load_article_legend,
    load_salazon_ranges,
    normalize_template_to_safe_area,
    normalize_lote_from_filename,
    parse_partida_file,
    parse_date,
    print_labels_windows,
    render_label,
    reset_label_template,
    save_label_contact_sheet,
    save_label_template,
    save_salazon_range_units,
    safe_margin_mm_from_template,
    salazon_ranges_for_article,
    validate_workday,
)


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
EXPORTS_DIR = APP_DIR / "exportaciones"
STATE_PATH = APP_DIR / "config_usuario.json"




def _canvas_round_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs):
    radius = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=18, **kwargs)


class CanvasButton(tk.Canvas):
    COLORS = {
        "primary": (PRIMARY_BLUE, "#0050B8", "#002E70", "white", PRIMARY_BLUE),
        "secondary": ("#EEF4FF", "#DCEBFF", "#CFE2FF", PRIMARY_BLUE, "#C8D6EA"),
        "danger": (ACCENT_RED, "#C91616", "#A90F0F", "white", ACCENT_RED),
        "ghost": (SURFACE, "#F3F7FF", "#E9F1FF", PRIMARY_BLUE, BORDER),
        "ribbon": ("#F8FAFD", "#EEF4FF", "#E3ECFA", TEXT, "#DCE5F2"),
        "tab": ("#EEF3FA", "#E6EEF9", "#DCE8F7", PRIMARY_BLUE, "#D7E1EF"),
        "tab_active": (PRIMARY_BLUE, "#0050B8", "#002E70", "white", PRIMARY_BLUE),
        "dark": (TEXT, "#263146", "#101827", "white", TEXT),
        "disabled": ("#EEF1F6", "#EEF1F6", "#EEF1F6", "#8A93A5", "#D7DEE9"),
    }

    def __init__(self, master, text: str, command=None, variant: str = "secondary", width: int = 132, height: int = 38, radius: int = 9, font=None, enabled: bool = True):
        try:
            bg = master.cget("background")
        except Exception:
            bg = SURFACE
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0, bd=0, takefocus=1 if enabled else 0)
        self.text = text
        self.command = command
        self.variant = variant
        self.button_width = width
        self.button_height = height
        self.radius = radius
        self.font = font or ("Segoe UI", 10, "bold")
        self.enabled = enabled
        self.is_hover = False
        self.is_pressed = False
        self.has_focus = False
        self.configure(cursor="hand2" if enabled else "arrow")
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Return>", self._on_key_activate)
        self.bind("<space>", self._on_key_activate)
        self._draw()

    def _palette(self):
        if not self.enabled:
            return self.COLORS["disabled"]
        return self.COLORS.get(self.variant, self.COLORS["secondary"])

    def _draw(self) -> None:
        normal, hover, pressed, fg, border = self._palette()
        fill = pressed if self.enabled and self.is_pressed else hover if self.enabled and self.is_hover else normal
        self.delete("all")
        _canvas_round_rect(self, 1, 1, self.button_width - 1, self.button_height - 1, self.radius, fill=fill, outline=border, width=1)
        if self.has_focus and self.enabled:
            _canvas_round_rect(self, 4, 4, self.button_width - 4, self.button_height - 4, max(self.radius - 2, 3), fill="", outline=ACCENT_RED, width=2)
        self.create_text(self.button_width // 2, self.button_height // 2, text=self.text, fill=fg, font=self.font)

    def _on_enter(self, _event=None) -> None:
        if not self.enabled:
            return
        self.is_hover = True
        self._draw()

    def _on_leave(self, _event=None) -> None:
        self.is_hover = False
        self.is_pressed = False
        self._draw()

    def _on_press(self, _event=None) -> None:
        if not self.enabled:
            return
        self.focus_set()
        self.is_pressed = True
        self._draw()

    def _on_release(self, event=None) -> None:
        if not self.enabled:
            return
        inside = event is not None and 0 <= event.x <= self.button_width and 0 <= event.y <= self.button_height
        self.is_pressed = False
        self._draw()
        if inside and callable(self.command):
            self.command()

    def _on_focus_in(self, _event=None) -> None:
        self.has_focus = True
        self._draw()

    def _on_focus_out(self, _event=None) -> None:
        self.has_focus = False
        self.is_pressed = False
        self._draw()

    def _on_key_activate(self, _event=None) -> str:
        if self.enabled and callable(self.command):
            self.command()
        return "break"

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow", takefocus=1 if enabled else 0)
        self.is_hover = False
        self.is_pressed = False
        self._draw()

    def set_text(self, text: str) -> None:
        self.text = text
        self._draw()

    def set_variant(self, variant: str) -> None:
        self.variant = variant
        self._draw()


class ModernScrollBar(tk.Canvas):
    def __init__(self, master, command=None, width: int = 14):
        try:
            bg = master.cget("background")
        except Exception:
            bg = BG
        super().__init__(master, width=width, bg=bg, highlightthickness=0, bd=0, takefocus=0)
        self.command = command
        self.first = 0.0
        self.last = 1.0
        self.drag_offset = 0
        self.bind("<Configure>", self._draw)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)

    def set(self, first, last) -> None:
        self.first = max(0.0, min(float(first), 1.0))
        self.last = max(self.first, min(float(last), 1.0))
        self._draw()

    def _thumb_bounds(self) -> tuple[int, int]:
        height = max(self.winfo_height(), 1)
        track_top = 8
        track_bottom = max(height - 8, track_top + 1)
        track_h = track_bottom - track_top
        visible = max(self.last - self.first, 0.08)
        thumb_h = max(int(track_h * visible), 34)
        y1 = track_top + int(track_h * self.first)
        y2 = min(y1 + thumb_h, track_bottom)
        y1 = max(track_top, y2 - thumb_h)
        return y1, y2

    def _draw(self, _event=None) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        x1 = max(width // 2 - 4, 2)
        x2 = min(width // 2 + 4, width - 2)
        _canvas_round_rect(self, x1, 8, x2, height - 8, 4, fill="#E6ECF5", outline="#E6ECF5")
        if self.last >= 0.999 and self.first <= 0.001:
            return
        y1, y2 = self._thumb_bounds()
        _canvas_round_rect(self, x1 - 2, y1, x2 + 2, y2, 6, fill=PRIMARY_BLUE, outline=PRIMARY_BLUE)

    def _on_press(self, event) -> None:
        y1, y2 = self._thumb_bounds()
        if y1 <= event.y <= y2:
            self.drag_offset = event.y - y1
            return
        self._move_to_event(event.y, centered=True)

    def _on_drag(self, event) -> None:
        self._move_to_event(event.y - self.drag_offset, centered=False)

    def _move_to_event(self, y: int, centered: bool) -> None:
        height = max(self.winfo_height(), 1)
        track_top = 8
        track_bottom = max(height - 8, track_top + 1)
        track_h = track_bottom - track_top
        span = max(self.last - self.first, 0.01)
        if centered:
            y = y - int(track_h * span / 2)
        fraction = (y - track_top) / max(track_h, 1)
        fraction = max(0.0, min(fraction, 1.0 - span))
        if callable(self.command):
            self.command("moveto", fraction)


class CanvasPanel(tk.Canvas):
    def __init__(self, master, title: str, min_height: int = 120, header_height: int = 44, padding: int = 16, auto_height: bool = True):
        try:
            bg = master.cget("background")
        except Exception:
            bg = BG
        super().__init__(master, bg=bg, highlightthickness=0, bd=0, height=min_height)
        self.title = title
        self.min_height = min_height
        self.header_height = header_height
        self.padding = padding
        self.bottom_padding = max(22, padding)
        self.body_gap = 8
        self.auto_height = auto_height
        self.body = tk.Frame(self, bg=SURFACE, highlightthickness=0, bd=0, padx=12, pady=10)
        self.body_window = self.create_window((padding + 1, header_height + self.body_gap + 1), window=self.body, anchor="nw")
        self.bind("<Configure>", self._draw)
        self.body.bind("<Configure>", self._fit_height)

    def _fit_height(self, _event=None) -> None:
        if not self.auto_height:
            return
        requested = self.body.winfo_reqheight() + self.header_height + self.body_gap + self.bottom_padding
        self.configure(height=max(self.min_height, requested))

    def _draw(self, event=None) -> None:
        width = max((event.width if event is not None else self.winfo_width()), 1)
        height = max((event.height if event is not None else self.winfo_height()), self.min_height)
        self.delete("panel")
        _canvas_round_rect(self, 4, 5, width - 2, height - 2, 12, fill="#E5ECF6", outline="#E5ECF6", width=1, tags="panel")
        _canvas_round_rect(self, 1, 1, width - 4, height - 4, 12, fill=SURFACE, outline="#C8D3E3", width=1, tags="panel")
        self.create_text(24, 34, text=self.title.upper(), anchor="w", fill=PRIMARY_BLUE, font=("Segoe UI", 10, "bold"), tags="panel")
        body_y = self.header_height + self.body_gap
        _canvas_round_rect(self, self.padding, body_y, width - self.padding, height - self.bottom_padding, 8, fill=SURFACE, outline="#D7E0EE", width=1, tags="panel")
        self.itemconfigure(self.body_window, width=max(width - self.padding * 2 - 2, 1))
        self.itemconfigure(self.body_window, height=max(height - self.header_height - self.body_gap - self.bottom_padding - 2, 1))
        self.tag_lower("panel")


class CanvasFlowBar(tk.Canvas):
    def __init__(self, master, steps: tuple[str, ...]):
        super().__init__(master, height=66, bg=SURFACE, highlightthickness=0, bd=0)
        self.steps = steps
        self.active_index = 0
        self.completed_until = -1
        self.bind("<Configure>", self._draw)

    def set_state(self, active_index: int, completed_until: int) -> None:
        self.active_index = max(0, min(active_index, len(self.steps) - 1))
        self.completed_until = max(-1, min(completed_until, len(self.steps) - 1))
        self._draw()

    def _draw(self, _event=None) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        _canvas_round_rect(self, 1, 1, width - 2, height - 2, 12, fill="#F8FBFF", outline="#D7E0EE", width=1)
        side = 78
        usable = max(width - side * 2, 1)
        node_y = 26
        label_y = 52
        if len(self.steps) > 1:
            start_x = side
            end_x = width - side
            self.create_line(start_x, node_y, end_x, node_y, fill="#D7E0EE", width=4, capstyle="round")
            if self.completed_until >= 0:
                done_end = start_x + (usable / max(len(self.steps) - 1, 1)) * min(self.completed_until, len(self.steps) - 1)
                self.create_line(start_x, node_y, done_end, node_y, fill=PRIMARY_BLUE, width=4, capstyle="round")
        for index, text in enumerate(self.steps):
            if len(self.steps) == 1:
                cx = width // 2
            else:
                cx = int(side + (usable / (len(self.steps) - 1)) * index)
            done = index <= self.completed_until
            active = index == self.active_index
            fill = PRIMARY_BLUE if done or active else SURFACE
            fg = "white" if done or active else PRIMARY_BLUE
            outline = ACCENT_RED if active else PRIMARY_BLUE if done else "#9EACC2"
            radius = 17 if active else 15
            if active:
                self.create_oval(cx - 21, node_y - 21, cx + 21, node_y + 21, fill="#EEF4FF", outline="")
            self.create_oval(cx - radius, node_y - radius, cx + radius, node_y + radius, fill=fill, outline=outline, width=3)
            self.create_text(cx, node_y, text=str(index + 1), fill=fg, font=("Segoe UI", 11, "bold"))
            label = text.split(". ", 1)[-1]
            self.create_text(cx, label_y, text=label, fill=PRIMARY_BLUE if active or done else MUTED, font=("Segoe UI", 9, "bold"), anchor="center")


class CanvasSummaryBar(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, height=82, bg=SURFACE, highlightthickness=0, bd=0)
        self.items = [
            ("Jamones", "-"),
            ("Boxes", "-"),
            ("Etiquetas", "-"),
            ("Salida", "-"),
            ("Estado", "Pendiente"),
        ]
        self.status_ok = False
        self.bind("<Configure>", self._draw)

    def set_items(self, items: list[tuple[str, str]], status_ok: bool = False) -> None:
        self.items = items
        self.status_ok = status_ok
        self._draw()

    def _draw(self, _event=None) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        count = max(len(self.items), 1)
        gap = 10
        card_w = max((width - gap * (count - 1)) // count, 1)
        for index, (label, value) in enumerate(self.items):
            x1 = index * (card_w + gap)
            x2 = x1 + card_w
            fill = "#F8FBFF"
            outline = "#DCE3F0"
            if label.lower().startswith("estado"):
                fill = "#EEF9F1" if self.status_ok else "#FFF4E5"
                outline = "#B9E2C5" if self.status_ok else "#F0C987"
            _canvas_round_rect(self, x1 + 1, 1, x2 - 1, height - 1, 8, fill=fill, outline=outline, width=1)
            self.create_text(x1 + 14, 20, text=label.upper(), anchor="w", fill=MUTED, font=("Segoe UI", 8, "bold"))
            self.create_text(x1 + 14, 52, text=value, anchor="w", fill=TEXT, font=("Segoe UI", 13, "bold"), width=max(card_w - 28, 40))


class LabelTemplateEditor(tk.Toplevel):
    EDITABLE_TYPES = {"rect", "line", "text", "value", "field"}
    REQUIRED_IDS = {"titulo", "dia_salida", "fecha_salida", "fecha_entrada", "lote", "articulo", "piezas_rango", "unidades_box", "pie"}
    STRUCTURE_IDS = {"outer_border", "header_bar", "titulo", "salida_label", "linea_salida", "linea_fechas", "linea_lote", "linea_unidades", "linea_articulo", "linea_pie"}
    CUSTOM_LABEL_MIN_MM = 25.0
    CUSTOM_LABEL_MAX_MM = 220.0
    EDITOR_FONT_MAX = 360
    RIBBON_FONT_SIZES = ("8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "32", "36", "42", "48", "54", "62", "70", "82", "92", "112", "126", "150", "180", "220", "260", "300", "360")
    VARIABLE_CHOICES = (
        "box_numero", "dia_salida", "fecha_salida", "fecha_recepcion", "fecha_entrada", "lote",
        "articulo_codigo", "articulo_nombre", "articulo", "total_piezas_rango", "unidades",
        "dias_sal", "etiquetas", "pie",
    )
    TYPE_CHOICES = ("text", "value", "field", "line", "rect")
    TYPE_LABELS = {
        "field": "Campo con leyenda",
        "value": "Valor variable",
        "text": "Texto fijo",
        "line": "Linea",
        "rect": "Rectangulo",
    }
    TYPE_LABEL_CHOICES = ("Texto fijo", "Valor variable", "Campo con leyenda", "Linea", "Rectangulo")
    ALIGN_LABELS = {
        "left": "Izquierda",
        "center": "Centrado",
        "right": "Derecha",
    }
    ALIGN_LABEL_CHOICES = ("Izquierda", "Centrado", "Derecha")
    ELEMENT_LABELS = {
        "outer_border": "Borde exterior",
        "header_bar": "Cabecera negra",
        "titulo": "Titulo",
        "salida_label": "Rotulo fecha salida",
        "dia_salida": "Dia salida",
        "fecha_salida": "Fecha salida sal",
        "fecha_recepcion": "Fecha recepcion",
        "fecha_entrada": "Fecha entrada en sal",
        "lote": "Lote",
        "articulo": "Articulo",
        "piezas_rango": "Piezas en rango",
        "unidades_box": "Unidades box",
        "pie": "Pie de etiqueta",
    }
    VARIABLE_LABELS = {
        "box_numero": "Numero de box",
        "dia_salida": "Dia de salida",
        "fecha_salida": "Fecha salida sal",
        "fecha_recepcion": "Fecha recepcion",
        "fecha_entrada": "Fecha entrada en sal",
        "lote": "Lote",
        "articulo_codigo": "Codigo articulo",
        "articulo_nombre": "Nombre articulo",
        "articulo": "Articulo",
        "total_piezas_rango": "Piezas en rango",
        "unidades": "Unidades por box",
        "dias_sal": "Dias en sal",
        "etiquetas": "Etiquetas por box",
        "pie": "Pie calculado",
    }
    FIELD_PRESETS = (
        ("Lote", "lote", "LOTE"),
        ("Articulo", "articulo_nombre", "ARTICULO"),
        ("Fecha salida sal", "fecha_salida", "FECHA SALIDA SAL"),
        ("Fecha entrada en sal", "fecha_entrada", "FECHA DE ENTRADA EN SAL"),
        ("Fecha recepcion", "fecha_recepcion", "FECHA RECEPCION"),
        ("Piezas en rango", "total_piezas_rango", "PIEZAS EN RANGO"),
        ("Unidades box", "unidades", "UNIDADES BOX"),
        ("Dias en sal", "dias_sal", "DIAS EN SAL"),
    )
    FOOTER_PRESETS = (
        "BOX {box_numero}",
        "BOX {box_numero} | {dias_sal} DIAS EN SAL",
        "BOX {box_numero} | LOTE {lote} | {dias_sal} DIAS EN SAL",
    )
    QUICK_VARIABLES = (
        ("Box", "box_numero"),
        ("Lote", "lote"),
        ("Dias", "dias_sal"),
        ("Articulo", "articulo_nombre"),
    )

    def __init__(self, master, on_saved=None, sample_box_provider=None, printer_provider=None) -> None:
        super().__init__(master)
        self.withdraw()
        try:
            self.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        self.title("Editor de plantilla de etiqueta")
        self.geometry("1360x840")
        self.minsize(1180, 720)
        self.configure(bg=BG)
        set_window_icon(self)
        self.on_saved = on_saved
        self.sample_box_provider = sample_box_provider
        self.printer_provider = printer_provider
        self.template = normalize_template_to_safe_area(load_label_template())
        self.selected_index: int | None = None
        self.hover_index: int | None = None
        self.drag_start: tuple[int, int] | None = None
        self.drag_origin: dict | None = None
        self.drag_snapshot: dict | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.preview_scale = 1.0
        self.preview_origin = (0, 0)
        self.history: list[dict] = []
        self.future: list[dict] = []
        self.clipboard_element: dict | None = None
        self.resize_mode = False
        self.loading_form = False
        self.form_pending = False

        self.var_x = tk.StringVar()
        self.var_y = tk.StringVar()
        self.var_w = tk.StringVar()
        self.var_h = tk.StringVar()
        self.var_id = tk.StringVar()
        self.var_type = tk.StringVar()
        self.var_type_label = tk.StringVar()
        self.var_key = tk.StringVar()
        self.var_template = tk.StringVar()
        self.var_font = tk.StringVar()
        self.var_min_font = tk.StringVar()
        self.var_label = tk.StringVar()
        self.var_text = tk.StringVar()
        self.var_fill = tk.StringVar()
        self.var_outline = tk.StringVar()
        self.var_label_fill = tk.StringVar()
        self.var_line_width = tk.StringVar()
        self.var_value_offset = tk.StringVar()
        self.var_line_spacing = tk.StringVar()
        self.var_footer_preset = tk.StringVar(value=self.FOOTER_PRESETS[1])
        self.var_align = tk.StringVar(value=self.ALIGN_LABELS["left"])
        self.var_add_type_label = tk.StringVar(value=self.TYPE_LABELS["field"])
        self.var_visible = tk.BooleanVar(value=True)
        self.var_locked = tk.BooleanVar(value=False)
        self.var_bold = tk.BooleanVar(value=True)
        self.var_wrap = tk.BooleanVar(value=False)
        self.var_grid = tk.BooleanVar(value=True)
        self.var_guides = tk.BooleanVar(value=True)
        self.var_snap = tk.BooleanVar(value=False)
        self.var_safe_area = tk.BooleanVar(value=True)
        self.var_advanced_mode = tk.BooleanVar(value=False)
        self.var_zoom = tk.StringVar(value="Ajustar")
        self.var_safe_margin_mm = tk.StringVar(value=self._format_mm(self._safe_margin_mm()))
        self.var_ribbon_font_size = tk.StringVar(value="")
        self.size_preset_labels = tuple(item[0] for item in CITIZEN_LABEL_SIZE_PRESETS)
        current_width_mm, current_height_mm = self._label_size_mm()
        self.var_label_size = tk.StringVar(value=self._current_size_label())
        self.var_custom_width_mm = tk.StringVar(value=self._format_mm(current_width_mm))
        self.var_custom_height_mm = tk.StringVar(value=self._format_mm(current_height_mm))
        self.variable_label_choices = ("",) + tuple(self._variable_label(item) for item in self.VARIABLE_CHOICES)
        self.field_preset_labels = tuple(item[0] for item in self.FIELD_PRESETS)
        self.var_field_preset = tk.StringVar(value=self.field_preset_labels[0])
        self.status = tk.StringVar(value=f"Plantilla: {LABEL_TEMPLATE_PATH}")
        self.selection_info = tk.StringVar(value="Selecciona un elemento de la lista o de la vista previa.")
        self.used_fields_info = tk.StringVar(value="Variables usadas: -")
        self.template_state = tk.StringVar(value="Estado plantilla: pendiente")
        self.dirty_state = tk.StringVar(value="Cambios guardados")
        self.context_title = tk.StringVar(value="Sin elemento seleccionado")
        self.context_hint = tk.StringVar(value="Selecciona un bloque de la etiqueta para editarlo.")
        self._is_fullscreen = False
        self.lock_sensitive_widgets: list[tk.Misc] = []
        self.lock_exempt_widgets: list[tk.Misc] = []
        self.preview_pan_start: tuple[int, int] | None = None
        self.help_window: tk.Toplevel | None = None
        self.var_key.trace_add("write", lambda *_args: self._show_variable_preview())
        self.var_template.trace_add("write", lambda *_args: self._show_variable_preview())
        for variable in (
            self.var_id, self.var_type_label, self.var_key, self.var_template, self.var_x, self.var_y,
            self.var_w, self.var_h, self.var_font, self.var_min_font, self.var_label, self.var_text,
            self.var_fill, self.var_outline, self.var_label_fill, self.var_line_width,
            self.var_value_offset, self.var_line_spacing, self.var_align,
            self.var_visible, self.var_locked, self.var_bold, self.var_wrap,
        ):
            variable.trace_add("write", self._mark_form_pending)

        self._build_ui()
        self._populate_elements()
        self._select_first_editable()
        self.saved_snapshot = self._snapshot()
        self._bind_editor_shortcuts()
        self.after(100, self._draw_preview)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.request_close)
        self.after(20, self._show_editor_window)
        self.after(150, self._focus_editor)

    def _snapshot(self) -> dict:
        return json.loads(json.dumps(self.template))

    def _open_editor_maximized(self) -> None:
        try:
            self.state("zoomed")
            return
        except tk.TclError:
            pass
        try:
            width = self.winfo_screenwidth()
            height = self.winfo_screenheight()
            self.geometry(f"{width}x{height}+0+0")
        except Exception:
            pass

    def _show_editor_window(self) -> None:
        self._open_editor_maximized()
        self.deiconify()
        self.lift()
        try:
            self.attributes("-alpha", 1.0)
        except tk.TclError:
            pass

    def _base_width(self) -> int:
        return max(1, int(self.template.get("base_width", BASE_LABEL_WIDTH) or BASE_LABEL_WIDTH))

    def _base_height(self) -> int:
        return max(1, int(self.template.get("base_height", BASE_LABEL_HEIGHT) or BASE_LABEL_HEIGHT))

    def _label_size_mm(self) -> tuple[float, float]:
        try:
            width = float(self.template.get("label_width_mm", 110.0))
        except Exception:
            width = 110.0
        try:
            height = float(self.template.get("label_height_mm", 162.0))
        except Exception:
            height = 162.0
        return max(width, 1.0), max(height, 1.0)

    def _safe_margin_mm(self) -> float:
        return safe_margin_mm_from_template(self.template)

    def _format_mm(self, value: float) -> str:
        return f"{float(value):g}".replace(".", ",")

    def _current_size_label(self) -> str:
        width, height = self._label_size_mm()
        for label, preset_width, preset_height in CITIZEN_LABEL_SIZE_PRESETS:
            if abs(width - preset_width) < 0.1 and abs(height - preset_height) < 0.1:
                return label
        return f"{width:g} x {height:g} mm - personalizado"

    def _sync_size_controls(self) -> None:
        if not hasattr(self, "var_label_size"):
            return
        width, height = self._label_size_mm()
        self.var_label_size.set(self._current_size_label())
        if hasattr(self, "var_custom_width_mm"):
            self.var_custom_width_mm.set(self._format_mm(width))
        if hasattr(self, "var_custom_height_mm"):
            self.var_custom_height_mm.set(self._format_mm(height))
        if hasattr(self, "var_safe_margin_mm"):
            self.var_safe_margin_mm.set(self._format_mm(self._safe_margin_mm()))

    def _safe_box_for_dimensions(self, width_mm: float, height_mm: float, base_width: int, base_height: int, safe_margin_mm: float | None = None) -> tuple[int, int, int, int]:
        margin = self._safe_margin_mm() if safe_margin_mm is None else safe_margin_mm
        margin_x = int(base_width * margin / max(width_mm, 1))
        margin_y = int(base_height * margin / max(height_mm, 1))
        return margin_x, margin_y, base_width - margin_x, base_height - margin_y

    def _parse_custom_label_dimension(self, value: str, field_name: str) -> float:
        text = value.strip().replace(",", ".")
        try:
            number = float(text)
        except Exception as exc:
            raise ValueError(f"{field_name} debe ser un numero en mm.") from exc
        if number != number or number < self.CUSTOM_LABEL_MIN_MM or number > self.CUSTOM_LABEL_MAX_MM:
            raise ValueError(f"{field_name} debe estar entre {self.CUSTOM_LABEL_MIN_MM:g} y {self.CUSTOM_LABEL_MAX_MM:g} mm.")
        return number

    def _parse_safe_margin(self, value: str) -> float:
        text = value.strip().replace(",", ".")
        try:
            number = float(text)
        except Exception as exc:
            raise ValueError("El margen seguro debe ser un numero en mm.") from exc
        if number != number or number < SAFE_MARGIN_MIN_MM or number > SAFE_MARGIN_MAX_MM:
            raise ValueError(f"El margen seguro debe estar entre {SAFE_MARGIN_MIN_MM:g} y {SAFE_MARGIN_MAX_MM:g} mm.")
        return number

    def apply_safe_margin(self) -> str:
        try:
            new_margin = self._parse_safe_margin(self.var_safe_margin_mm.get())
        except ValueError as exc:
            messagebox.showinfo("Margen seguro no valido", str(exc), parent=self)
            self._sync_size_controls()
            return "break"
        old_margin = self._safe_margin_mm()
        if abs(new_margin - old_margin) < 0.01:
            self.status.set("La plantilla ya usa ese margen seguro.")
            self._sync_size_controls()
            return "break"
        if new_margin > old_margin and not messagebox.askyesno(
            "Cambiar margen seguro",
            f"Se aumentara el margen seguro de {old_margin:g} a {new_margin:g} mm.\n\n"
            "Los elementos visibles se recolocaran si quedan fuera del nuevo margen.\n\n"
            "¿Continuar?",
            parent=self,
        ):
            self._sync_size_controls()
            return "break"
        self._push_undo()
        self.template["safe_margin_mm"] = new_margin
        self.template = normalize_template_to_safe_area(self.template)
        self._sync_size_controls()
        self._populate_elements()
        if self.selected_index is not None:
            self._select_index(min(self.selected_index, len(self._elements()) - 1))
        self._draw_preview()
        self.status.set(f"Margen seguro aplicado: {new_margin:g} mm. Revisa la vista previa antes de guardar.")
        self._refresh_dirty_state()
        return "break"

    def _scale_element_for_label_size(self, element: dict, old_box: tuple[int, int, int, int], new_box: tuple[int, int, int, int], font_scale: float) -> None:
        old_x1, old_y1, old_x2, old_y2 = old_box
        new_x1, new_y1, new_x2, new_y2 = new_box
        sx = (new_x2 - new_x1) / max(old_x2 - old_x1, 1)
        sy = (new_y2 - new_y1) / max(old_y2 - old_y1, 1)

        def map_x(value) -> int:
            return int(round(new_x1 + (float(value) - old_x1) * sx))

        def map_y(value) -> int:
            return int(round(new_y1 + (float(value) - old_y1) * sy))

        kind = str(element.get("type", ""))
        if kind == "line":
            for key in ("x1", "x2"):
                if key in element:
                    element[key] = map_x(element.get(key, old_x1))
            for key in ("y1", "y2"):
                if key in element:
                    element[key] = map_y(element.get(key, old_y1))
        else:
            original_x = float(element.get("x", old_x1))
            original_y = float(element.get("y", old_y1))
            original_w = float(element.get("w", 1))
            original_h = float(element.get("h", 1))
            x1 = map_x(original_x)
            y1 = map_y(original_y)
            x2 = map_x(original_x + original_w)
            element["x"] = x1
            element["y"] = y1
            element["w"] = max(1, x2 - x1)
            if "h" in element:
                y2 = map_y(original_y + original_h)
                element["h"] = max(1, y2 - y1)
        for key in ("font_size", "min_size", "label_size", "value_size", "line_width", "value_offset"):
            if key in element:
                element[key] = max(1, int(round(float(element.get(key, 1)) * font_scale)))

    def apply_label_size_preset(self) -> str:
        selected = self.var_label_size.get().strip()
        preset = next((item for item in CITIZEN_LABEL_SIZE_PRESETS if item[0] == selected), None)
        if preset is None:
            messagebox.showinfo("Tamaño no valido", "Selecciona un tamaño de etiqueta de la lista.", parent=self)
            return "break"
        _label, width_mm, height_mm = preset
        return self._apply_label_size(width_mm, height_mm, "preset")

    def apply_custom_label_size(self) -> str:
        try:
            width_mm = self._parse_custom_label_dimension(self.var_custom_width_mm.get(), "Ancho")
            height_mm = self._parse_custom_label_dimension(self.var_custom_height_mm.get(), "Alto")
        except ValueError as exc:
            messagebox.showinfo("Tamaño personalizado no valido", str(exc), parent=self)
            self._sync_size_controls()
            return "break"
        return self._apply_label_size(width_mm, height_mm, "personalizado")

    def _apply_label_size(self, width_mm: float, height_mm: float, source: str) -> str:
        old_width = self._base_width()
        old_height = self._base_height()
        new_width = max(1, int(width_mm / 25.4 * DEFAULT_DPI))
        new_height = max(1, int(height_mm / 25.4 * DEFAULT_DPI))
        if old_width == new_width and old_height == new_height:
            self.status.set("La plantilla ya usa ese tamaño de etiqueta.")
            self._sync_size_controls()
            return "break"
        old_label_width_mm, old_label_height_mm = self._label_size_mm()
        old_box = self._safe_box_for_dimensions(old_label_width_mm, old_label_height_mm, old_width, old_height)
        new_box = self._safe_box_for_dimensions(width_mm, height_mm, new_width, new_height)
        sx = (new_box[2] - new_box[0]) / max(old_box[2] - old_box[0], 1)
        sy = (new_box[3] - new_box[1]) / max(old_box[3] - old_box[1], 1)
        font_scale = min(sx, sy)
        if not messagebox.askyesno(
            "Cambiar tamaño de etiqueta",
            f"Se cambiara la plantilla a {width_mm:g} x {height_mm:g} mm y se reescalaran los elementos.\n\n"
            f"El contenido se ajustara usando el margen seguro actual de {self._safe_margin_mm():g} mm.\n"
            "El editor creara una copia de seguridad antes del cambio.\n"
            "Importante: revisa que el driver de la Citizen tenga el mismo tamaño antes de imprimir.\n\n"
            "¿Continuar?",
            parent=self,
        ):
            self._sync_size_controls()
            return "break"
        backup_note = ""
        try:
            backup_dir = LABEL_TEMPLATE_PATH.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"plantilla_etiqueta_backup_antes_tamano_{datetime.now():%Y%m%d_%H%M%S}.json"
            backup_path.write_text(json.dumps(self.template, ensure_ascii=False, indent=2), encoding="utf-8")
            backup_note = f" Copia: {backup_path.name}."
        except Exception:
            backup_note = " No se pudo crear copia previa."
        self._push_undo()
        for element in self._elements():
            self._scale_element_for_label_size(element, old_box, new_box, font_scale)
        self.template["label_width_mm"] = width_mm
        self.template["label_height_mm"] = height_mm
        self.template["base_width"] = new_width
        self.template["base_height"] = new_height
        self.template = normalize_template_to_safe_area(self.template)
        self._sync_size_controls()
        self._populate_elements()
        if self.selected_index is not None:
            self._select_index(min(self.selected_index, len(self._elements()) - 1))
        self._draw_preview()
        self.status.set(f"Tamaño {source} aplicado: {width_mm:g} x {height_mm:g} mm. Diseño reescalado al area util. Revisa driver e imprime una prueba.{backup_note}")
        self._refresh_dirty_state()
        return "break"

    def _push_undo(self) -> None:
        self.history.append(self._snapshot())
        self.history = self.history[-60:]
        self.future.clear()

    def _restore_snapshot(self, snapshot: dict) -> None:
        self.template = json.loads(json.dumps(snapshot))
        self.selected_index = min(self.selected_index or 0, max(len(self._elements()) - 1, 0))
        self._populate_elements()
        self._sync_size_controls()
        if self.selected_index is not None:
            self.listbox.selection_set(self.selected_index)
            self.listbox.see(self.selected_index)
        self._load_selected_to_form()
        self._draw_preview()
        self._refresh_dirty_state()

    def _is_dirty(self) -> bool:
        return self._snapshot() != getattr(self, "saved_snapshot", None)

    def _refresh_dirty_state(self) -> None:
        if not hasattr(self, "dirty_state"):
            return
        if self.form_pending:
            self.dirty_state.set("Cambios escritos sin aplicar")
        elif self._is_dirty():
            self.dirty_state.set("Cambios sin guardar")
        else:
            self.dirty_state.set("Cambios guardados")

    def _mark_form_pending(self, *_args) -> None:
        if self.loading_form:
            return
        self.form_pending = True
        self._refresh_dirty_state()

    def _apply_form_event(self, _event=None) -> str:
        if self.form_pending:
            self.apply_changes()
        return "break"

    def _bind_apply_events(self, widget: tk.Misc) -> None:
        widget.bind("<FocusOut>", self._apply_form_event, add="+")
        widget.bind("<Return>", self._apply_form_event, add="+")
        widget.bind("<<ComboboxSelected>>", self._apply_form_event, add="+")

    def _toggle_simple_tools(self) -> None:
        advanced = bool(self.var_advanced_mode.get())
        if hasattr(self, "free_add_label"):
            if advanced:
                self.free_add_label.pack(anchor="w")
                self.free_add_combo.pack(fill="x")
                self.free_add_actions.pack(fill="x", pady=(6, 0))
            else:
                self.free_add_label.pack_forget()
                self.free_add_combo.pack_forget()
                self.free_add_actions.pack_forget()
        if hasattr(self, "quick_panel"):
            if advanced:
                self.quick_panel.grid()
            else:
                self.quick_panel.grid_remove()
        if hasattr(self, "footer_panel"):
            if advanced:
                self.footer_panel.grid()
            else:
                self.footer_panel.grid_remove()

    def request_close(self) -> bool:
        self.apply_changes(push_undo=False)
        if self._is_dirty():
            answer = messagebox.askyesnocancel("Cambios sin guardar", "Hay cambios en el editor de etiquetas.\n\n¿Quieres guardarlos antes de cerrar?", parent=self)
            if answer is None:
                return False
            if answer:
                self.save_changes()
                if self._is_dirty():
                    return False
        self.destroy()
        return True

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=14, style="App.TFrame")
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(2, weight=1)

        top = tk.Frame(root, bg="#F8FAFD", highlightthickness=1, highlightbackground="#D8E1EE", padx=16, pady=11)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        top.columnconfigure(1, weight=1)
        tk.Frame(top, bg=PRIMARY_BLUE, width=4, height=42).grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 12))
        tk.Label(top, text="Editor de etiqueta", bg="#F8FAFD", fg=TEXT, font=("Segoe UI", 16, "bold")).grid(row=0, column=1, sticky="w")
        tk.Label(top, text="Ajusta la plantilla, valida y prueba antes de guardar.", bg="#F8FAFD", fg=MUTED, font=("Segoe UI", 9)).grid(row=1, column=1, sticky="w", pady=(2, 0))
        top_actions = tk.Frame(top, bg="#F8FAFD")
        top_actions.grid(row=0, column=2, rowspan=2, sticky="e", padx=(18, 0))
        CanvasButton(top_actions, text="Guardar", command=self.save_changes, variant="primary", width=92, height=34, radius=8).pack(side="left", padx=(0, 6))
        CanvasButton(top_actions, text="Probar", command=self.print_test_label, variant="secondary", width=82, height=34, radius=8).pack(side="left", padx=(0, 6))
        CanvasButton(top_actions, text="Validar", command=self.validate_template_now, variant="secondary", width=84, height=34, radius=8).pack(side="left", padx=(0, 6))
        self.fullscreen_button = CanvasButton(top_actions, text="Pantalla", command=self.toggle_fullscreen, variant="ghost", width=104, height=34, radius=8)
        self.fullscreen_button.pack(side="left", padx=(0, 6))
        CanvasButton(top_actions, text="Ayuda", command=self.show_editor_help, variant="ghost", width=76, height=34, radius=8).pack(side="left")

        self._build_editor_ribbon(root)

        left_outer = tk.Frame(root, bg=SURFACE, highlightthickness=1, highlightbackground="#DCE3F0")
        left_outer.grid(row=2, column=0, sticky="ns", padx=(0, 14))
        left_outer.rowconfigure(0, weight=1)
        left_outer.columnconfigure(0, weight=1)
        left_canvas = tk.Canvas(left_outer, width=348, bg=SURFACE, highlightthickness=0, bd=0)
        self.left_canvas = left_canvas
        left_canvas.grid(row=0, column=0, sticky="ns")
        left_scroll = ModernScrollBar(left_outer, command=left_canvas.yview, width=12)
        left_scroll.grid(row=0, column=1, sticky="ns")
        left_canvas.configure(yscrollcommand=left_scroll.set)
        left = tk.Frame(left_canvas, bg=SURFACE, padx=12, pady=12)
        left_window = left_canvas.create_window((0, 0), window=left, anchor="nw")
        left.bind("<Configure>", lambda _e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        left_canvas.bind("<Configure>", lambda e: left_canvas.itemconfigure(left_window, width=e.width))
        left_canvas.bind("<Enter>", lambda _e: left_canvas.focus_set(), add="+")
        left.rowconfigure(1, weight=1)
        tk.Label(left, text="1. Selecciona un bloque", bg=SURFACE, fg=PRIMARY_BLUE, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.listbox = tk.Listbox(left, width=31, height=13, activestyle="dotbox", exportselection=False, relief="flat", highlightthickness=1, highlightbackground="#D7E0EE", bg="#FBFCFF", fg=TEXT, selectbackground=PRIMARY_BLUE, selectforeground="white")
        self.listbox.grid(row=1, column=0, sticky="ns")
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)

        add_buttons = ttk.Frame(left, style="Surface.TFrame")
        add_buttons.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(add_buttons, text="2. Añade solo si falta algo", style="Surface.TLabel").pack(anchor="w")
        ttk.Label(add_buttons, text="Usa esta zona para el flujo normal. Las acciones delicadas estan en las pestañas superiores.", style="Muted.TLabel", wraplength=320).pack(anchor="w", pady=(2, 6))
        field_combo = ttk.Combobox(add_buttons, textvariable=self.var_field_preset, values=self.field_preset_labels, state="readonly")
        field_combo.pack(fill="x", pady=(0, 5))
        CanvasButton(add_buttons, text="Añadir dato", command=self.add_preset_field, variant="secondary", width=118, height=30).pack(anchor="e", pady=(0, 8))
        self.free_add_label = ttk.Label(add_buttons, text="Añadir elemento libre", style="Muted.TLabel")
        self.free_add_label.pack(anchor="w")
        self.free_add_combo = ttk.Combobox(add_buttons, textvariable=self.var_add_type_label, values=self.TYPE_LABEL_CHOICES, state="readonly")
        self.free_add_combo.pack(fill="x")
        add_action_row = ttk.Frame(add_buttons, style="Surface.TFrame")
        self.free_add_actions = add_action_row
        add_action_row.pack(fill="x", pady=(6, 0))
        CanvasButton(add_action_row, text="Añadir", command=self.add_element, variant="secondary", width=78, height=30).pack(side="left")
        CanvasButton(add_action_row, text="Eliminar", command=self.delete_element, variant="danger", width=82, height=30).pack(side="left", padx=(6, 0))
        CanvasButton(add_action_row, text="Rest. elem.", command=self.restore_selected_element, variant="ghost", width=94, height=30).pack(side="left", padx=(6, 0))

        quick = ttk.Frame(left, style="Surface.TFrame")
        self.quick_panel = quick
        quick.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(quick, text="Variables rapidas para plantillas", style="Surface.TLabel").pack(anchor="w")
        quick_buttons = ttk.Frame(quick, style="Surface.TFrame")
        quick_buttons.pack(fill="x", pady=(5, 0))
        for label, key in self.QUICK_VARIABLES:
            CanvasButton(quick_buttons, text=label, command=lambda k=key: self.insert_variable(k), variant="ghost", width=54, height=28, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 4), pady=(0, 4))

        footer_box = ttk.Frame(left, style="Surface.TFrame")
        self.footer_panel = footer_box
        footer_box.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(footer_box, text="Pie de etiqueta", style="Surface.TLabel").pack(anchor="w")
        ttk.Combobox(footer_box, textvariable=self.var_footer_preset, values=self.FOOTER_PRESETS, width=38).pack(fill="x", pady=(5, 4))
        CanvasButton(footer_box, text="Aplicar al pie", command=self.apply_footer_preset, variant="secondary", width=118, height=30).pack(anchor="e")

        used_box = ttk.Frame(left, style="Surface.TFrame")
        used_box.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        ttk.Label(used_box, textvariable=self.template_state, style="Surface.TLabel", wraplength=336, justify="left").pack(fill="x", pady=(0, 5))
        ttk.Label(used_box, textvariable=self.used_fields_info, style="Muted.TLabel", wraplength=336, justify="left").pack(fill="x")

        context = tk.Frame(left, bg="#F8FBFF", highlightthickness=1, highlightbackground="#D7E0EE", padx=10, pady=10)
        context.grid(row=6, column=0, sticky="ew", pady=(12, 0))
        for col in range(2):
            context.columnconfigure(col, weight=1)
        tk.Label(context, text="3. Edita el bloque", bg="#F8FBFF", fg=PRIMARY_BLUE, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(context, textvariable=self.context_title, bg="#F8FBFF", fg=TEXT, font=("Segoe UI", 10, "bold"), wraplength=318, justify="left").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(7, 0))
        tk.Label(context, textvariable=self.context_hint, bg="#F8FBFF", fg=MUTED, font=("Segoe UI", 9), wraplength=318, justify="left").grid(row=2, column=0, columnspan=2, sticky="ew", pady=(2, 8))
        ttk.Label(context, text="Variable", style="Muted.TLabel").grid(row=3, column=0, sticky="w", pady=(5, 0))
        key_combo = ttk.Combobox(context, textvariable=self.var_key, values=self.variable_label_choices, width=15)
        key_combo.grid(row=3, column=1, sticky="ew", pady=(5, 0), padx=(8, 0))
        self.lock_sensitive_widgets.append(key_combo)
        self._bind_apply_events(key_combo)
        self._editor_entry(context, 4, "Leyenda", self.var_label)
        self._editor_entry(context, 5, "Texto", self.var_text)
        self._editor_entry(context, 6, "Plantilla", self.var_template)
        ttk.Label(context, text="Tamaño letra", style="Muted.TLabel").grid(row=7, column=0, sticky="w", pady=(5, 0))
        font_entry = ttk.Entry(context, textvariable=self.var_font, width=18)
        font_entry.grid(row=7, column=1, sticky="ew", pady=(5, 0), padx=(8, 0))
        self.lock_sensitive_widgets.append(font_entry)
        font_entry.bind("<KeyRelease>", self._mark_form_pending, add="+")
        self._bind_apply_events(font_entry)
        ttk.Label(context, text="Alineacion", style="Muted.TLabel").grid(row=8, column=0, sticky="w", pady=(5, 0))
        align_combo = ttk.Combobox(context, textvariable=self.var_align, values=self.ALIGN_LABEL_CHOICES, width=15, state="readonly")
        align_combo.grid(row=8, column=1, sticky="ew", pady=(5, 0), padx=(8, 0))
        self.lock_sensitive_widgets.append(align_combo)
        self._bind_apply_events(align_combo)
        context_checks = ttk.Frame(context, style="Surface.TFrame")
        context_checks.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        visible_check = ttk.Checkbutton(context_checks, text="Visible", variable=self.var_visible, command=self.apply_changes)
        visible_check.pack(side="left")
        self.lock_sensitive_widgets.append(visible_check)
        locked_check = ttk.Checkbutton(context_checks, text="Bloqueado", variable=self.var_locked, command=self.apply_changes)
        locked_check.pack(side="left", padx=(8, 0))
        self.lock_exempt_widgets.append(locked_check)
        bold_check = ttk.Checkbutton(context_checks, text="Negrita", variable=self.var_bold, command=self.apply_changes)
        bold_check.pack(side="left", padx=(8, 0))
        self.lock_sensitive_widgets.append(bold_check)
        context_apply = CanvasButton(context, text="Aplicar", command=self.apply_changes, variant="primary", width=88, height=32)
        context_apply.grid(row=10, column=0, columnspan=2, sticky="e", pady=(10, 0))
        self.lock_sensitive_widgets.append(context_apply)

        mode_box = ttk.Frame(left, style="Surface.TFrame")
        mode_box.grid(row=7, column=0, sticky="ew", pady=(10, 0))
        ttk.Checkbutton(mode_box, text="Mostrar parametros tecnicos", variable=self.var_advanced_mode, command=self._refresh_editor_mode).pack(anchor="w")

        editor = ttk.Frame(left, style="Surface.TFrame")
        self.advanced_editor = editor
        editor.grid(row=8, column=0, sticky="ew", pady=(8, 0))
        for col in range(2):
            editor.columnconfigure(col, weight=1)
        ttk.Label(editor, text="Elemento", style="Surface.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        self._editor_entry(editor, 1, "ID", self.var_id)
        ttk.Label(editor, text="Tipo", style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(5, 0))
        type_combo = ttk.Combobox(editor, textvariable=self.var_type_label, values=self.TYPE_LABEL_CHOICES, width=15, state="readonly")
        type_combo.grid(row=2, column=1, sticky="ew", pady=(5, 0), padx=(8, 0))
        self.lock_sensitive_widgets.append(type_combo)
        self._bind_apply_events(type_combo)
        ttk.Label(editor, text="Variable", style="Muted.TLabel").grid(row=3, column=0, sticky="w", pady=(5, 0))
        advanced_key_combo = ttk.Combobox(editor, textvariable=self.var_key, values=self.variable_label_choices, width=15)
        advanced_key_combo.grid(row=3, column=1, sticky="ew", pady=(5, 0), padx=(8, 0))
        self.lock_sensitive_widgets.append(advanced_key_combo)
        self._bind_apply_events(advanced_key_combo)
        self._editor_entry(editor, 4, "Plantilla", self.var_template)

        ttk.Label(editor, text="Posicion y caja", style="Surface.TLabel").grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._editor_entry(editor, 6, "X", self.var_x)
        self._editor_entry(editor, 7, "Y", self.var_y)
        self._editor_entry(editor, 8, "Ancho", self.var_w)
        self._editor_entry(editor, 9, "Alto", self.var_h)
        ttk.Label(editor, text="Texto y fuente", style="Surface.TLabel").grid(row=10, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._editor_entry(editor, 11, "Fuente", self.var_font)
        self._editor_entry(editor, 12, "Min fuente", self.var_min_font)
        self._editor_entry(editor, 13, "Leyenda", self.var_label)
        self._editor_entry(editor, 14, "Texto fijo", self.var_text)
        ttk.Label(editor, text="Alineacion", style="Muted.TLabel").grid(row=15, column=0, sticky="w", pady=(5, 0))
        advanced_align_combo = ttk.Combobox(editor, textvariable=self.var_align, values=self.ALIGN_LABEL_CHOICES, width=15, state="readonly")
        advanced_align_combo.grid(row=15, column=1, sticky="ew", pady=(5, 0), padx=(8, 0))
        self.lock_sensitive_widgets.append(advanced_align_combo)
        self._bind_apply_events(advanced_align_combo)
        ttk.Label(editor, text="Color/grafica", style="Surface.TLabel").grid(row=16, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._editor_entry(editor, 17, "Color texto", self.var_fill)
        self._editor_entry(editor, 18, "Borde/fondo", self.var_outline)
        self._editor_entry(editor, 19, "Color leyenda", self.var_label_fill)
        self._editor_entry(editor, 20, "Grosor linea", self.var_line_width)
        self._editor_entry(editor, 21, "Offset valor", self.var_value_offset)
        self._editor_entry(editor, 22, "Interlineado", self.var_line_spacing)
        checks = ttk.Frame(editor, style="Surface.TFrame")
        checks.grid(row=23, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        adv_visible_check = ttk.Checkbutton(checks, text="Visible", variable=self.var_visible, command=self.apply_changes)
        adv_visible_check.pack(side="left")
        self.lock_sensitive_widgets.append(adv_visible_check)
        adv_locked_check = ttk.Checkbutton(checks, text="Bloqueado", variable=self.var_locked, command=self.apply_changes)
        adv_locked_check.pack(side="left", padx=(8, 0))
        self.lock_exempt_widgets.append(adv_locked_check)
        adv_bold_check = ttk.Checkbutton(checks, text="Negrita", variable=self.var_bold, command=self.apply_changes)
        adv_bold_check.pack(side="left", padx=(8, 0))
        self.lock_sensitive_widgets.append(adv_bold_check)
        adv_wrap_check = ttk.Checkbutton(checks, text="Multilinea", variable=self.var_wrap, command=self.apply_changes)
        adv_wrap_check.pack(side="left", padx=(8, 0))
        self.lock_sensitive_widgets.append(adv_wrap_check)
        advanced_apply = CanvasButton(editor, text="Aplicar", command=self.apply_changes, variant="secondary", width=92, height=34)
        advanced_apply.grid(row=24, column=0, columnspan=2, sticky="e", pady=(10, 0))
        self.lock_sensitive_widgets.append(advanced_apply)
        self._bind_editor_scroll_area(left_outer)
        self._refresh_editor_mode()

        preview_frame = ttk.Frame(root, style="Surface.TFrame")
        preview_frame.grid(row=2, column=1, sticky="nsew")
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        self.preview_canvas = tk.Canvas(preview_frame, bg="#EEF3FA", highlightthickness=1, highlightbackground="#C8D3E3")
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        preview_y = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_canvas.yview)
        preview_y.grid(row=0, column=1, sticky="ns")
        preview_x = ttk.Scrollbar(preview_frame, orient="horizontal", command=self.preview_canvas.xview)
        preview_x.grid(row=1, column=0, sticky="ew")
        self.preview_canvas.configure(yscrollcommand=preview_y.set, xscrollcommand=preview_x.set)
        self.preview_canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.preview_canvas.bind("<Double-Button-1>", self._on_canvas_double_click)
        self.preview_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.preview_canvas.bind("<ButtonPress-2>", self._on_preview_pan_start)
        self.preview_canvas.bind("<B2-Motion>", self._on_preview_pan_move)
        self.preview_canvas.bind("<ButtonRelease-2>", self._on_preview_pan_end)
        self.preview_canvas.bind("<Shift-ButtonPress-1>", self._on_preview_pan_start)
        self.preview_canvas.bind("<Shift-B1-Motion>", self._on_preview_pan_move)
        self.preview_canvas.bind("<Shift-ButtonRelease-1>", self._on_preview_pan_end)
        self.preview_canvas.bind("<Motion>", self._on_canvas_motion)
        self.preview_canvas.bind("<Leave>", self._on_canvas_leave)
        self.preview_canvas.bind("<Configure>", lambda _e: self._draw_preview())

        footer = tk.Frame(root, bg=BG)
        footer.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        footer.columnconfigure(1, weight=1)
        tk.Label(footer, textvariable=self.dirty_state, bg=BG, fg=PRIMARY_BLUE, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(footer, textvariable=self.status, bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="e").grid(row=0, column=1, sticky="ew", padx=(14, 0))

    def _ribbon_group(self, parent: tk.Misc, title: str) -> tk.Frame:
        wrapper = tk.Frame(parent, bg="#F3F6FA")
        wrapper.pack(side="left", fill="y", padx=(0, 10))
        group = tk.Frame(wrapper, bg="#F3F6FA", padx=0, pady=2)
        group.pack(side="left", fill="y")
        tk.Label(group, text=title, bg="#F3F6FA", fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 7))
        body = tk.Frame(group, bg="#F3F6FA")
        body.pack(side="top", anchor="w")
        tk.Frame(wrapper, bg="#DDE6F1", width=1).pack(side="left", fill="y", padx=(10, 0), pady=(3, 1))
        return body

    def _ribbon_button(self, parent: tk.Misc, text: str, command, variant: str = "ghost", width: int = 78) -> CanvasButton:
        if variant == "ghost":
            variant = "ribbon"
        button = CanvasButton(parent, text=text, command=command, variant=variant, width=width, height=30, radius=8, font=("Segoe UI", 8, "bold"))
        button.pack(side="left", padx=(0, 5))
        return button

    def _select_ribbon_tab(self, key: str) -> str:
        for tab_key, page in self.ribbon_pages.items():
            if tab_key == key:
                page.grid()
                self.ribbon_tab_buttons[tab_key].set_variant("tab_active")
            else:
                page.grid_remove()
                self.ribbon_tab_buttons[tab_key].set_variant("tab")
        return "break"

    def _build_editor_ribbon(self, root: tk.Misc) -> None:
        ribbon = tk.Frame(root, bg="#F3F6FA", highlightthickness=1, highlightbackground="#D8E1EE", padx=12, pady=10)
        ribbon.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ribbon.columnconfigure(0, weight=1)

        tab_bar = tk.Frame(ribbon, bg="#F3F6FA")
        tab_bar.grid(row=0, column=0, sticky="w")
        self.ribbon_tab_buttons: dict[str, CanvasButton] = {}
        tab_specs = (
            ("file", "Archivo", 82),
            ("home", "Inicio", 74),
            ("insert", "Insertar", 84),
            ("design", "Diseño", 78),
            ("view", "Vista", 68),
        )
        for key, label, width in tab_specs:
            button = CanvasButton(tab_bar, text=label, command=lambda k=key: self._select_ribbon_tab(k), variant="tab", width=width, height=32, radius=9, font=("Segoe UI", 9, "bold"))
            button.pack(side="left", padx=(0, 6))
            self.ribbon_tab_buttons[key] = button

        pages = tk.Frame(ribbon, bg="#F3F6FA")
        pages.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        pages.columnconfigure(0, weight=1)
        self.ribbon_pages: dict[str, tk.Frame] = {}
        for key, _label, _width in tab_specs:
            page = tk.Frame(pages, bg="#F3F6FA")
            page.grid(row=0, column=0, sticky="ew")
            page.grid_remove()
            self.ribbon_pages[key] = page

        file_tab = self.ribbon_pages["file"]
        home_tab = self.ribbon_pages["home"]
        insert_tab = self.ribbon_pages["insert"]
        design_tab = self.ribbon_pages["design"]
        view_tab = self.ribbon_pages["view"]

        file_group = self._ribbon_group(file_tab, "Plantilla")
        self._ribbon_button(file_group, "Cargar", self.load_template_file, "secondary", 70)
        self._ribbon_button(file_group, "Exportar copia", self.save_template_as, "secondary", 108)
        self._ribbon_button(file_group, "Ult. backup", self.restore_latest_backup, "secondary", 92)
        self._ribbon_button(file_group, "Reparar", self.repair_template, "secondary", 76)
        self._ribbon_button(file_group, "Restaurar", self.reset_template, "danger", 84)

        edit_group = self._ribbon_group(home_tab, "Edicion")
        self._ribbon_button(edit_group, "Deshacer", self.undo, "ghost", 76)
        self._ribbon_button(edit_group, "Rehacer", self.redo, "ghost", 72)
        self._ribbon_button(edit_group, "Copiar", self.copy_element, "ghost", 66)
        self._ribbon_button(edit_group, "Pegar", self.paste_element, "ghost", 62)
        self._ribbon_button(edit_group, "Duplicar", self.duplicate_element, "ghost", 76)

        text_group = self._ribbon_group(home_tab, "Texto")
        ttk.Label(text_group, text="Tamaño", style="Muted.TLabel").pack(side="left", padx=(0, 4))
        font_combo = ttk.Combobox(text_group, textvariable=self.var_ribbon_font_size, values=self.RIBBON_FONT_SIZES, width=5)
        font_combo.pack(side="left", padx=(0, 5))
        font_combo.bind("<<ComboboxSelected>>", self.apply_ribbon_font_size, add="+")
        font_combo.bind("<Return>", self.apply_ribbon_font_size, add="+")
        font_combo.bind("<FocusOut>", self.apply_ribbon_font_size, add="+")
        self._ribbon_button(text_group, "A-", lambda: self.adjust_ribbon_font_size(-2), "ghost", 42)
        self._ribbon_button(text_group, "A+", lambda: self.adjust_ribbon_font_size(2), "ghost", 42)
        self._ribbon_button(text_group, "B", self.toggle_selected_bold, "ghost", 36)
        self._ribbon_button(text_group, "Izq", lambda: self.set_selected_text_align("left"), "ghost", 44)
        self._ribbon_button(text_group, "Cen", lambda: self.set_selected_text_align("center"), "ghost", 48)
        self._ribbon_button(text_group, "Der", lambda: self.set_selected_text_align("right"), "ghost", 44)
        ToolTip(font_combo, "Tamaño de letra del bloque de texto seleccionado.")

        element_group = self._ribbon_group(home_tab, "Elemento")
        self._ribbon_button(element_group, "Eliminar", self.delete_element, "danger", 76)
        self._ribbon_button(element_group, "Rest. elem.", self.restore_selected_element, "ghost", 86)
        self._ribbon_button(element_group, "Ocultar", lambda: self.toggle_selected_visible(False), "ghost", 70)
        self._ribbon_button(element_group, "Mostrar", lambda: self.toggle_selected_visible(True), "ghost", 70)

        insert_group = self._ribbon_group(insert_tab, "Elemento nuevo")
        ttk.Combobox(insert_group, textvariable=self.var_field_preset, values=self.field_preset_labels, width=21, state="readonly").pack(side="left", padx=(0, 5))
        self._ribbon_button(insert_group, "Añadir dato", self.add_preset_field, "primary", 88)
        ttk.Combobox(insert_group, textvariable=self.var_add_type_label, values=self.TYPE_LABEL_CHOICES, width=17, state="readonly").pack(side="left", padx=(0, 5))
        self._ribbon_button(insert_group, "Añadir", self.add_element, "secondary", 70)

        variables_group = self._ribbon_group(insert_tab, "Variables")
        for label, key in self.QUICK_VARIABLES:
            self._ribbon_button(variables_group, label, lambda k=key: self.insert_variable(k), "ghost", 58)

        footer_group = self._ribbon_group(insert_tab, "Pie")
        ttk.Combobox(footer_group, textvariable=self.var_footer_preset, values=self.FOOTER_PRESETS, width=34).pack(side="left", padx=(0, 5))
        self._ribbon_button(footer_group, "Aplicar", self.apply_footer_preset, "secondary", 70)

        layer_group = self._ribbon_group(design_tab, "Capas")
        self._ribbon_button(layer_group, "Arriba", self.bring_forward, "ghost", 62)
        self._ribbon_button(layer_group, "Abajo", self.send_backward, "ghost", 62)

        arrange_group = self._ribbon_group(design_tab, "Alinear")
        self._ribbon_button(arrange_group, "Izq", lambda: self.align_selected("left"), "ghost", 44)
        self._ribbon_button(arrange_group, "Centro", lambda: self.align_selected("center"), "ghost", 62)
        self._ribbon_button(arrange_group, "Der", lambda: self.align_selected("right"), "ghost", 44)
        self._ribbon_button(arrange_group, "Ancho", self.full_width_selected, "ghost", 62)

        size_group = self._ribbon_group(design_tab, "Tamaño preset")
        ttk.Combobox(size_group, textvariable=self.var_label_size, values=self.size_preset_labels, width=28, state="readonly").pack(side="left", padx=(0, 5))
        self._ribbon_button(size_group, "Aplicar", self.apply_label_size_preset, "secondary", 70)

        custom_size_group = self._ribbon_group(design_tab, "Personalizado")
        ttk.Label(custom_size_group, text="Ancho", style="Muted.TLabel").pack(side="left", padx=(0, 4))
        custom_width_entry = ttk.Entry(custom_size_group, textvariable=self.var_custom_width_mm, width=6)
        custom_width_entry.pack(side="left", padx=(0, 4))
        ttk.Label(custom_size_group, text="Alto", style="Muted.TLabel").pack(side="left", padx=(0, 4))
        custom_height_entry = ttk.Entry(custom_size_group, textvariable=self.var_custom_height_mm, width=6)
        custom_height_entry.pack(side="left", padx=(0, 5))
        self._ribbon_button(custom_size_group, "Aplicar", self.apply_custom_label_size, "primary", 70)
        ToolTip(custom_width_entry, "Ancho de etiqueta en mm. Valor permitido: 25 a 220.")
        ToolTip(custom_height_entry, "Alto de etiqueta en mm. Valor permitido: 25 a 220.")

        safe_margin_group = self._ribbon_group(design_tab, "Margen seguro")
        ttk.Label(safe_margin_group, text="mm", style="Muted.TLabel").pack(side="left", padx=(0, 4))
        safe_margin_entry = ttk.Entry(safe_margin_group, textvariable=self.var_safe_margin_mm, width=6)
        safe_margin_entry.pack(side="left", padx=(0, 5))
        self._ribbon_button(safe_margin_group, "Aplicar", self.apply_safe_margin, "secondary", 70)
        self._ribbon_button(safe_margin_group, "Ver", lambda: self.var_safe_area.set(True) or self._draw_preview(), "ghost", 42)
        ToolTip(safe_margin_entry, f"Margen seguro en mm. Valor permitido: {SAFE_MARGIN_MIN_MM:g} a {SAFE_MARGIN_MAX_MM:g}.")

        center_group = self._ribbon_group(design_tab, "Centrar")
        self._ribbon_button(center_group, "Centrar H", lambda: self.center_selected("horizontal"), "ghost", 82)
        self._ribbon_button(center_group, "Centrar V", lambda: self.center_selected("vertical"), "ghost", 80)

        structure_group = self._ribbon_group(design_tab, "Proteccion")
        self._ribbon_button(structure_group, "Bloq. estructura", self.lock_structure_elements, "secondary", 118)

        view_group = self._ribbon_group(view_tab, "Ayudas")
        ttk.Checkbutton(view_group, text="Rejilla", variable=self.var_grid, command=self._draw_preview).pack(side="left", padx=(0, 5))
        ttk.Checkbutton(view_group, text="Guias", variable=self.var_guides, command=self._draw_preview).pack(side="left", padx=(0, 5))
        ttk.Checkbutton(view_group, text="Margen seguro", variable=self.var_safe_area, command=self._draw_preview).pack(side="left", padx=(0, 5))
        ttk.Checkbutton(view_group, text="Snap", variable=self.var_snap).pack(side="left", padx=(0, 8))

        mode_group = self._ribbon_group(view_tab, "Modo")
        ttk.Checkbutton(mode_group, text="Parametros tecnicos", variable=self.var_advanced_mode, command=self._refresh_editor_mode).pack(side="left", padx=(0, 5))

        zoom_group = self._ribbon_group(view_tab, "Zoom")
        ttk.Label(zoom_group, text="Zoom", style="Muted.TLabel").pack(side="left", padx=(0, 4))
        ttk.Combobox(zoom_group, textvariable=self.var_zoom, values=("Ajustar", "50%", "75%", "100%", "150%"), width=8, state="readonly").pack(side="left")
        self.var_zoom.trace_add("write", lambda *_args: self._draw_preview())
        self._select_ribbon_tab("home")

    def show_editor_help(self) -> str:
        if self.help_window is not None and self.help_window.winfo_exists():
            self.help_window.lift()
            self.help_window.focus_force()
            return "break"
        self.help_window = tk.Toplevel(self)
        self.help_window.title("Ayuda del editor de etiquetas")
        self.help_window.geometry("820x720")
        self.help_window.minsize(680, 560)
        self.help_window.configure(bg=BG)
        set_window_icon(self.help_window)

        frame = ttk.Frame(self.help_window, padding=16, style="App.TFrame")
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Ayuda del editor de etiquetas", background=BG, foreground=TEXT, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Sigue estos pasos para cambiar el diseño sin tocar parametros tecnicos.", background=BG, foreground=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 12))

        body_frame = ttk.Frame(frame, style="App.TFrame")
        body_frame.pack(fill="both", expand=True)
        text = tk.Text(body_frame, wrap="word", bg="white", fg=TEXT, relief="flat", padx=18, pady=16, font=("Segoe UI", 10), height=22)
        text.pack(side="left", fill="both", expand=True)
        scroll = ModernScrollBar(body_frame, command=text.yview)
        scroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=scroll.set)

        help_text = """ANTES DE TOCAR NADA
1. Genera una vista previa en la pantalla principal si quieres editar con datos reales.
2. Abre el editor con Ctrl+Alt+D.
3. Mira el margen verde: todo lo importante debe quedar dentro.
4. Antes de guardar, usa Probar.
5. El editor se abre maximizado para que no se corte la cinta. Usa Pantalla o F11 si quieres pantalla completa real.

CAMBIAR UN TEXTO O UNA LEYENDA
1. Haz clic sobre el texto en la etiqueta, o selecciónalo en la lista Elementos.
2. Cambia Leyenda, Texto o Tamaño letra en el panel izquierdo.
3. Pulsa Enter o sal del campo. El cambio se ve en la etiqueta.
4. Si el diseño está bien, pulsa Guardar.

MOVER UN DATO
1. Haz clic sobre el bloque que quieres mover.
2. Arrástralo con el ratón dentro de la etiqueta.
3. También puedes usar las flechas del teclado. Con Shift se mueve más rápido.
4. Evita dejarlo fuera del margen verde.

CAMBIAR EL TAMAÑO DE UN BLOQUE
1. Selecciona el bloque.
2. Arrastra el cuadrado rojo de la esquina inferior derecha.
3. Si es un campo largo como ARTICULO, deja espacio suficiente para varias líneas.

AÑADIR UN DATO
1. En Añadir dato de la etiqueta, elige el dato que quieres añadir.
2. Pulsa Añadir dato.
3. Arrástralo a su posición.
4. Ajusta tamaño de letra y ancho si hace falta.
5. El rango de peso ya no se recomienda como bloque independiente: el rango viene dentro del nombre del artículo.

OCULTAR SIN BORRAR
1. Selecciona el elemento.
2. Desmarca Visible.
3. El elemento queda guardado en la plantilla, pero no se imprime.
4. Para recuperarlo, vuelve a marcar Visible.

ELIMINAR CON CUIDADO
1. Selecciona el elemento.
2. Pulsa Eliminar o la tecla Supr.
3. Si es un campo importante, el editor pedirá confirmación.
4. Si te equivocas, pulsa Deshacer.

CAMBIAR EL TAMAÑO DE ETIQUETA
1. Abre la pestaña Diseño.
2. Si el tamaño existe en la lista, usa Tamaño preset y pulsa Aplicar.
3. Si necesitas otra medida, escribe Ancho y Alto en Personalizado y pulsa Aplicar.
4. El editor crea una copia de seguridad antes de reescalar.
5. El reescalado mueve el diseño desde el margen seguro actual al nuevo margen seguro, para aprovechar el área útil.
6. Revisa visualmente la etiqueta: tamaños muy pequeños pueden necesitar simplificar textos.
7. Comprueba que el driver de la Citizen usa el mismo tamaño.
8. Imprime una prueba antes de guardar como diseño definitivo.

PROBAR ANTES DE IMPRIMIR
1. Selecciona la impresora en la pantalla principal.
2. En el editor, pulsa Probar.
3. Se envía una sola etiqueta.
4. Si sale bien, pulsa Guardar.

GUARDAR, EXPORTAR Y RECUPERAR
- Guardar aplica el diseño a la impresión real.
- Exportar copia guarda un JSON aparte, pero no cambia la plantilla activa.
- Ult. backup carga la última copia de seguridad para revisarla.
- Restaurar vuelve al diseño por defecto.
- Reparar intenta recuperar campos importantes, bloquear estructura y recolocar elementos fuera de etiqueta.

QUE SIGNIFICAN LOS ESTADOS
- Cambios guardados: la plantilla activa ya está al día.
- Cambios sin guardar: el diseño se ve cambiado, pero todavía no se aplica a impresión.
- Cambios escritos sin aplicar: has escrito algo en el panel y falta salir del campo, pulsar Enter o Aplicar cambios.
- Estado plantilla: OK: no se ven problemas importantes.
- Estado plantilla: revisar: hay algo que conviene corregir antes de guardar.
- Bloque protegido: los campos se desactivan para evitar cambios por error. Desmarca Bloqueado si necesitas editarlo.

REFERENCIA DE BOTONES, CAMPOS Y FUNCIONES

Cabecera superior
- Guardar: guarda la plantilla activa. A partir de ese momento la impresión real usa ese diseño.
- Probar: envía una sola etiqueta de prueba con el diseño que ves, aunque todavía no hayas guardado.
- Validar: revisa si faltan campos importantes, si hay elementos fuera de la etiqueta, textos demasiado pequeños o variables no reconocidas.
- Validar tambien avisa de posibles solapes, texto cortado, bajo contraste y campos importantes fuera del margen seguro.
- Pantalla: alterna pantalla completa real. F11 hace lo mismo y Esc sale de pantalla completa.
- Ayuda: abre esta guía. También se abre con F1.

Pestañas de herramientas
- Archivo: cargar, exportar, reparar o restaurar plantillas.
- Inicio: deshacer, rehacer, copiar, pegar, duplicar y dar formato rapido al texto seleccionado.
- Insertar: añadir datos frecuentes, elementos libres, variables rápidas y texto de pie.
- Diseño: ordenar capas, alinear, centrar, cambiar tamaño preset o personalizado y proteger estructura.
- Vista: activar rejilla, guías, margen seguro, snap, parámetros técnicos y zoom.

Archivo - Plantilla
- Cargar: abre una plantilla JSON externa para revisarla o usarla.
- Exportar copia: guarda una copia JSON aparte. No cambia la plantilla activa.
- Ult. backup: carga la última copia de seguridad disponible.
- Reparar: intenta recuperar campos importantes, mostrar elementos obligatorios, bloquear estructura y recolocar piezas fuera de la etiqueta.
- Restaurar: vuelve al diseño por defecto. Es una acción fuerte y pide confirmación.

Inicio - Edición
- Deshacer: revierte el último cambio.
- Rehacer: recupera un cambio que acabas de deshacer.
- Copiar: copia el elemento seleccionado.
- Pegar: crea una copia del elemento copiado.
- Duplicar: copia y pega el elemento seleccionado en un paso.

Inicio - Texto
- Tamaño: cambia la letra principal del bloque seleccionado.
- A- y A+: reducen o aumentan la letra en pasos pequeños.
- B: activa o desactiva negrita.
- Izq, Cen y Der: alinean el contenido dentro del bloque de texto, como en Word.

Inicio - Elemento
- Eliminar: borra el elemento seleccionado. Si es importante, pide confirmación.
- Rest. elem.: restaura el elemento seleccionado desde la plantilla base si existe.
- Ocultar: deja el elemento guardado, pero no lo imprime.
- Mostrar: vuelve a enseñar e imprimir un elemento oculto.

Insertar - Elemento nuevo
- Lista Añadir dato: contiene campos habituales, como lote, artículo, fechas, piezas o días en sal.
- Añadir dato: añade el campo elegido con una configuración sensata.
- Lista Añadir elemento libre: permite añadir texto fijo, variable, campo con leyenda, línea o recuadro.
- Añadir: crea el elemento libre elegido.

Insertar - Variables
- Botones rápidos: insertan una variable dentro del campo Plantilla del elemento seleccionado.
- Las variables se escriben entre llaves, por ejemplo {lote}. Al imprimir se sustituyen por el dato real.

Insertar - Pie
- Lista de pie: propone textos habituales para el pie de etiqueta.
- Aplicar: coloca ese texto en el elemento de pie.

Diseño - Capas y alineación
- Arriba: sube el elemento una capa para que se vea por encima de otros.
- Abajo: baja el elemento una capa.
- Izq, Centro y Der: alinean el texto dentro de su caja.
- Ancho: estira el elemento al ancho útil de la etiqueta.
- Centrar H: centra el elemento horizontalmente en la etiqueta.
- Centrar V: centra el elemento verticalmente en la etiqueta.

Diseño y Vista - Etiqueta, protección y vista
- Tamaño preset: selecciona tamaños comunes de etiquetas Citizen y aplica la medida elegida.
- Personalizado: permite escribir ancho y alto en mm entre 25 y 220.
- Aplicar: cambia el tamaño de etiqueta y reescala el diseño al nuevo margen seguro.
- Margen seguro: permite cambiar la zona interior recomendada para evitar cortes. Si lo aumentas, el editor recoloca lo que quede fuera.
- Ver: activa la visualizacion del margen seguro en la etiqueta.
- Bloq. estructura: bloquea elementos base para evitar moverlos por error.
- Rejilla: muestra puntos de referencia para colocar elementos.
- Guías: muestra líneas de ayuda al mover o seleccionar.
- Snap: hace que los movimientos se ajusten a la rejilla.
- Parámetros técnicos: muestra campos avanzados de posición, tamaño y color.
- Zoom: cambia el tamaño de visualización del lienzo. No cambia la etiqueta real.

Panel izquierdo
- Elementos: lista todos los bloques de la etiqueta. Haz clic en uno para editarlo.
- Estado plantilla: resume si el diseño está correcto o necesita revisión.
- Variables usadas: muestra qué datos reales utiliza la plantilla.
- Variable: dato real que se imprimirá, como lote, artículo, fecha, piezas o días.
- Leyenda: texto descriptivo que acompaña a un dato, por ejemplo ARTICULO.
- Texto: texto fijo escrito a mano, sin depender de los datos de la partida.
- Plantilla: texto mezclado con variables, por ejemplo BOX {box_num}/{box_total}.
- Tamaño letra: tamaño principal del texto seleccionado.
- Alineación: coloca el contenido a la izquierda, centrado o a la derecha dentro de su caja.
- Visible: si está marcado, el elemento se ve y se imprime.
- Bloqueado: si está marcado, evita mover o editar el elemento por accidente.
- Negrita: imprime el texto con más peso.
- Aplicar: fuerza la aplicación de lo escrito en los campos.

Parámetros técnicos
- ID: nombre interno del elemento. Sirve para reconocerlo y restaurarlo.
- Tipo: clase de elemento: texto, variable, campo con leyenda, línea o recuadro.
- X e Y: posición del elemento dentro de la etiqueta.
- Ancho y Alto: tamaño de la caja del elemento.
- Fuente: tamaño base de letra para textos y variables.
- Min fuente: tamaño mínimo permitido cuando el texto se ajusta automáticamente.
- Color texto: color del texto o de la línea.
- Borde/fondo: color de borde o fondo en elementos gráficos.
- Color leyenda: color de la leyenda en campos con dato.
- Grosor línea: grosor de líneas y bordes.
- Offset valor: distancia entre leyenda y valor en campos con dato.
- Interlineado: separación entre líneas cuando el texto ocupa varias líneas.
- Multilínea: permite partir el texto en varias líneas dentro de su caja.

Lienzo de etiqueta
- Clic: selecciona un bloque.
- Arrastrar: mueve el bloque seleccionado.
- Esquina roja: cambia el tamaño del bloque.
- Doble clic: abre una edición rápida cuando el elemento lo permite.
- Flechas del teclado: mueven 1 punto.
- Shift + flechas: mueve más rápido.
- Barras de scroll: aparecen para moverte cuando usas zoom alto.
- Botón central o Shift + arrastrar: desplaza el lienzo sin mover elementos.
"""
        text.insert("1.0", help_text)
        text.configure(state="disabled")
        CanvasButton(frame, text="Cerrar", command=self.help_window.destroy, variant="secondary", width=94, height=38).pack(anchor="e", pady=(12, 0))
        center_window(self.help_window)
        return "break"

    def _bind_editor_shortcuts(self) -> None:
        self.bind("<Control-z>", lambda _e: self.undo())
        self.bind("<Control-y>", lambda _e: self.redo())
        self.bind("<Control-s>", lambda _e: self.save_changes())
        self.bind("<Control-c>", lambda _e: self.copy_element())
        self.bind("<Control-v>", lambda _e: self.paste_element())
        self.bind("<Delete>", lambda _e: self.delete_element())
        self.bind("<F1>", lambda _e: self.show_editor_help())
        self.bind("<F11>", lambda _e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda _e: self.exit_fullscreen())
        self.bind("<Up>", lambda e: self.move_selected(0, -self._key_step(e)))
        self.bind("<Down>", lambda e: self.move_selected(0, self._key_step(e)))
        self.bind("<Left>", lambda e: self.move_selected(-self._key_step(e), 0))
        self.bind("<Right>", lambda e: self.move_selected(self._key_step(e), 0))

    def _fullscreen_active(self) -> bool:
        try:
            return bool(self.attributes("-fullscreen"))
        except tk.TclError:
            return self._is_fullscreen

    def _set_fullscreen(self, enabled: bool) -> None:
        self._is_fullscreen = bool(enabled)
        try:
            self.attributes("-fullscreen", self._is_fullscreen)
            self.update_idletasks()
        except tk.TclError:
            pass
        if not self._is_fullscreen:
            try:
                self.state("zoomed")
            except tk.TclError:
                self.state("normal")
        if hasattr(self, "fullscreen_button"):
            self.fullscreen_button.set_text("Salir pantalla" if self._is_fullscreen else "Pantalla")

    def toggle_fullscreen(self) -> str:
        self._set_fullscreen(not self._fullscreen_active())
        self.status.set("Pantalla completa activada. Pulsa Esc para salir." if self._is_fullscreen else "Pantalla completa desactivada.")
        return "break"

    def exit_fullscreen(self) -> str:
        if self._fullscreen_active():
            self._set_fullscreen(False)
            self.status.set("Pantalla completa desactivada.")
            return "break"
        return ""

    def _focus_editor(self) -> None:
        try:
            self.lift()
            self.focus_force()
            if hasattr(self, "preview_canvas"):
                self.preview_canvas.focus_set()
        except Exception:
            pass

    def _is_descendant(self, widget: tk.Misc, parent: tk.Misc) -> bool:
        current = widget
        while current is not None:
            if current is parent:
                return True
            try:
                current = current.master
            except Exception:
                return False
        return False

    def _wheel_units(self, event) -> int | None:
        if getattr(event, "num", None) == 4:
            return -3
        if getattr(event, "num", None) == 5:
            return 3
        raw_delta = getattr(event, "delta", 0)
        if raw_delta == 0:
            return None
        units = -1 * int(raw_delta / 120)
        return units if units else (-1 if raw_delta > 0 else 1)

    def _bind_editor_scroll_area(self, widget: tk.Misc) -> None:
        widget.bind("<MouseWheel>", self._on_editor_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_editor_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_editor_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_editor_scroll_area(child)

    def _on_editor_mousewheel(self, event) -> str | None:
        try:
            if event.widget.winfo_toplevel() is not self:
                return None
        except Exception:
            return None
        units = self._wheel_units(event)
        if units is None:
            return "break"
        if hasattr(self, "listbox") and self._is_descendant(event.widget, self.listbox):
            visible_rows = int(str(self.listbox.cget("height")))
            if self.listbox.size() > visible_rows:
                self.listbox.yview_scroll(units, "units")
                return "break"
        if hasattr(self, "left_canvas"):
            bbox = self.left_canvas.bbox("all")
            if bbox and (bbox[3] - bbox[1]) > self.left_canvas.winfo_height():
                self.left_canvas.yview_scroll(units, "units")
        return "break"

    def _type_label(self, kind: str) -> str:
        return self.TYPE_LABELS.get(kind, kind)

    def _type_value(self, label_or_kind: str) -> str:
        value = str(label_or_kind).strip()
        if value in self.TYPE_CHOICES:
            return value
        for kind, label in self.TYPE_LABELS.items():
            if value == label:
                return kind
        return value

    def _align_label(self, value: str) -> str:
        return self.ALIGN_LABELS.get(str(value).strip(), str(value).strip() or self.ALIGN_LABELS["left"])

    def _align_value(self, label_or_value: str) -> str:
        value = str(label_or_value).strip()
        if value in self.ALIGN_LABELS:
            return value
        for key, label in self.ALIGN_LABELS.items():
            if value == label:
                return key
        return "left"

    def _editor_entry(self, master, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(master, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=(5, 0))
        entry = ttk.Entry(master, textvariable=variable, width=18)
        entry.grid(row=row, column=1, sticky="ew", pady=(5, 0), padx=(8, 0))
        self.lock_sensitive_widgets.append(entry)
        entry.bind("<KeyRelease>", self._mark_form_pending, add="+")
        entry.bind("<FocusOut>", self._apply_form_event, add="+")
        entry.bind("<Return>", self._apply_form_event, add="+")

    def _set_widget_enabled(self, widget: tk.Misc, enabled: bool) -> None:
        try:
            if isinstance(widget, CanvasButton):
                widget.set_enabled(enabled)
                return
            if enabled:
                widget.state(["!disabled"])
            else:
                widget.state(["disabled"])
        except Exception:
            try:
                widget.configure(state="normal" if enabled else "disabled")
            except Exception:
                pass

    def _refresh_lock_state(self) -> None:
        element = self._selected_element()
        locked = bool(element and element.get("locked", False))
        for widget in self.lock_sensitive_widgets:
            self._set_widget_enabled(widget, not locked)
        for widget in self.lock_exempt_widgets:
            self._set_widget_enabled(widget, True)
        if locked:
            self.selection_info.set(self.selection_info.get() + " | desbloquea para cambiar" if "desbloquea" not in self.selection_info.get() else self.selection_info.get())

    def _refresh_editor_mode(self) -> str:
        if hasattr(self, "advanced_editor"):
            if self.var_advanced_mode.get():
                self.advanced_editor.grid()
            else:
                self.advanced_editor.grid_remove()
        self._toggle_simple_tools()
        self._refresh_lock_state()
        self.status.set("Modo avanzado activado." if self.var_advanced_mode.get() else "Modo sencillo: edita lo habitual desde el panel de elemento.")
        return "break"

    def _element_display_name(self, element: dict) -> str:
        element_id = str(element.get("id", "")).strip()
        if element_id in self.ELEMENT_LABELS:
            return self.ELEMENT_LABELS[element_id]
        label = str(element.get("label", "")).strip()
        text = str(element.get("text", "")).strip()
        if label:
            return label.title()
        if text:
            return text[:34]
        return element_id or "Elemento"

    def _element_label_by_id(self, element_id: str) -> str:
        clean = str(element_id).strip()
        return self.ELEMENT_LABELS.get(clean, clean or "Elemento")

    def _variable_label(self, key: str) -> str:
        return self.VARIABLE_LABELS.get(key, key)

    def _variable_value(self, label_or_key: str) -> str:
        value = str(label_or_key).strip()
        if value in self.VARIABLE_CHOICES:
            return value
        for key, label in self.VARIABLE_LABELS.items():
            if value == label:
                return key
        return value

    def _sample_box(self) -> BoxEtiqueta:
        if callable(self.sample_box_provider):
            try:
                box = self.sample_box_provider()
                if box is not None:
                    return box
            except Exception:
                pass
        return BoxEtiqueta(1, "220426", "607", "JAMON DE CEBO IBERICO", datetime(2026, 6, 27).date(), datetime(2026, 6, 17).date(), datetime(2026, 6, 26).date(), "VIERNES", 9, 24, 82, 10.5, 11.99, 10.5, 11.99, 2, (10.5, 11.2, 11.99))

    def _sample_values(self) -> dict[str, str]:
        return {
            "box_numero": "1",
            "dia_salida": "VIERNES",
            "fecha_salida": "26/06/2026",
            "fecha_recepcion": "27/05/2026",
            "fecha_entrada": "17/06/2026",
            "lote": "220426",
            "articulo_codigo": "607",
            "articulo_nombre": "JAMON DE CEBO IBERICO",
            "articulo": "JAMON DE CEBO IBERICO",
            "total_piezas_rango": "82",
            "unidades": "24",
            "dias_sal": "9",
            "rango_min": "10,5",
            "rango_max": "11,99",
            "rango_peso": "10,5 - 11,99 kg",
            "rango_real": "10,5 - 11,99 kg",
            "etiquetas": "2",
            "pie": "BOX 1 | 9 DIAS EN SAL | 2",
        }

    def _show_variable_preview(self) -> None:
        if not hasattr(self, "status"):
            return
        if getattr(self, "loading_form", False):
            return
        key = self._variable_value(self.var_key.get())
        template = self.var_template.get().strip()
        values = self._sample_values()
        if template:
            try:
                preview = template.format_map(values)
            except Exception:
                preview = "plantilla con variable no reconocida"
            self.status.set(f"Ejemplo plantilla: {preview}")
        elif key:
            self.status.set(f"Ejemplo variable {key}: {values.get(key, 'variable no reconocida')}")

    def _elements(self) -> list[dict]:
        elements = self.template.setdefault("elements", [])
        return elements if isinstance(elements, list) else []

    def _populate_elements(self) -> None:
        selected = self.selected_index
        self.listbox.delete(0, "end")
        for element in self._elements():
            flags = []
            if not element.get("visible", True):
                flags.append("oculto")
            if element.get("locked", False):
                flags.append("bloq")
            suffix = f" ({', '.join(flags)})" if flags else ""
            self.listbox.insert("end", f"{self._element_display_name(element)} - {self._type_label(str(element.get('type', '?')))}{suffix}")
        if selected is not None and 0 <= selected < len(self._elements()):
            self.listbox.selection_set(selected)
        self._refresh_used_fields()
        self._refresh_template_state()

    def _select_first_editable(self) -> None:
        for index, element in enumerate(self._elements()):
            if element.get("type") in self.EDITABLE_TYPES:
                self._select_index(index)
                return

    def _select_index(self, index: int | None) -> None:
        if index is None or not (0 <= index < len(self._elements())):
            return
        self.selected_index = index
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(index)
        self.listbox.see(index)
        self._load_selected_to_form()
        self._draw_preview()

    def _on_list_select(self, _event=None) -> None:
        selection = self.listbox.curselection()
        if selection:
            self._select_index(int(selection[0]))

    def _selected_element(self) -> dict | None:
        if self.selected_index is None:
            return None
        if 0 <= self.selected_index < len(self._elements()):
            return self._elements()[self.selected_index]
        return None

    def _load_selected_to_form(self) -> None:
        element = self._selected_element()
        if not element:
            return
        self.loading_form = True
        try:
            self.var_id.set(str(element.get("id", "")))
            self.var_type.set(str(element.get("type", "")))
            self.var_type_label.set(self._type_label(str(element.get("type", ""))))
            self.var_key.set(self._variable_label(str(element.get("key", ""))))
            self.var_template.set(str(element.get("template", "")))
            self.var_x.set(str(element.get("x", element.get("x1", ""))))
            self.var_y.set(str(element.get("y", element.get("y1", ""))))
            self.var_w.set(str(element.get("w", "")))
            self.var_h.set(str(element.get("h", "")))
            self.var_font.set(str(element.get("font_size", element.get("value_size", element.get("line_width", "")))))
            self.var_min_font.set(str(element.get("min_size", "")))
            self.var_label.set(str(element.get("label", "")))
            self.var_text.set(str(element.get("text", "")))
            self.var_fill.set(str(element.get("fill", "")))
            self.var_outline.set(str(element.get("outline", "")))
            self.var_label_fill.set(str(element.get("label_fill", "")))
            self.var_line_width.set(str(element.get("line_width", "")))
            self.var_value_offset.set(str(element.get("value_offset", "")))
            self.var_line_spacing.set(str(element.get("line_spacing", "")))
            self.var_align.set(self._align_label(str(element.get("align", "left"))))
            self.var_visible.set(bool(element.get("visible", True)))
            self.var_locked.set(bool(element.get("locked", False)))
            self.var_bold.set(bool(element.get("bold", True)))
            self.var_wrap.set(bool(element.get("wrap", False)))
            self._sync_ribbon_text_controls()
        finally:
            self.loading_form = False
            self.form_pending = False
        locked = "bloqueado" if element.get("locked", False) else "editable"
        visible = "visible" if element.get("visible", True) else "oculto"
        display_name = self._element_display_name(element)
        element_type = self._type_label(str(element.get("type", "")))
        self.selection_info.set(f"Seleccionado: {display_name} | {element_type} | {locked} | {visible}")
        self.context_title.set(f"{display_name} - {element_type}")
        if element.get("locked", False):
            self.context_hint.set("Este bloque esta protegido. Desbloquealo si necesitas moverlo o modificarlo.")
        elif element.get("type") == "field":
            key_text = self._variable_label(str(element.get("key", "")))
            self.context_hint.set(f"Campo con leyenda. Edita la leyenda, la variable ({key_text}) y el tamano del dato.")
        elif element.get("type") == "value":
            self.context_hint.set("Valor variable. Usa Variable o Plantilla para decidir que dato se imprime.")
        elif element.get("type") == "text":
            self.context_hint.set("Texto fijo. Cambia el texto visible, tamano y alineacion.")
        elif element.get("type") == "line":
            self.context_hint.set("Linea separadora. Muevela arrastrando o ajusta grosor en parametros tecnicos.")
        else:
            self.context_hint.set("Recuadro grafico. Arrastra para colocarlo y usa la esquina roja para cambiar tamano.")
        self._refresh_lock_state()
        self._refresh_dirty_state()

    def _selected_text_size_key(self, element: dict | None) -> str | None:
        if not element:
            return None
        kind = str(element.get("type", ""))
        if kind == "field":
            return "value_size"
        if kind in {"text", "value"}:
            return "font_size"
        return None

    def _sync_ribbon_text_controls(self) -> None:
        if not hasattr(self, "var_ribbon_font_size"):
            return
        element = self._selected_element()
        key = self._selected_text_size_key(element)
        self.var_ribbon_font_size.set(str(element.get(key, "")) if element and key else "")

    def apply_ribbon_font_size(self, _event=None) -> str:
        if self.loading_form:
            return "break"
        element = self._selected_element()
        key = self._selected_text_size_key(element)
        if not element or not key or element.get("locked", False):
            self.status.set("Selecciona un bloque de texto editable para cambiar la fuente.")
            self._sync_ribbon_text_controls()
            return "break"
        try:
            size = int(float(self.var_ribbon_font_size.get().strip().replace(",", ".")))
        except Exception:
            self.status.set("Tamaño de letra no valido.")
            self._sync_ribbon_text_controls()
            return "break"
        size = max(8, min(self.EDITOR_FONT_MAX, size))
        if int(element.get(key, size)) == size:
            return "break"
        self._push_undo()
        element[key] = size
        self.var_font.set(str(size))
        self._load_selected_to_form()
        self._draw_preview()
        self.status.set(f"Tamaño de letra aplicado: {size}.")
        self._refresh_dirty_state()
        return "break"

    def adjust_ribbon_font_size(self, delta: int) -> str:
        element = self._selected_element()
        key = self._selected_text_size_key(element)
        if not element or not key or element.get("locked", False):
            self.status.set("Selecciona un bloque de texto editable para ajustar la fuente.")
            return "break"
        current = int(element.get(key, 42) or 42)
        self.var_ribbon_font_size.set(str(max(8, min(self.EDITOR_FONT_MAX, current + delta))))
        return self.apply_ribbon_font_size()

    def set_selected_text_align(self, mode: str) -> str:
        element = self._selected_element()
        if not element or element.get("locked", False) or str(element.get("type", "")) not in {"text", "value", "field"}:
            self.status.set("Selecciona un bloque de texto editable para alinear.")
            return "break"
        if mode not in {"left", "center", "right"}:
            return "break"
        self._push_undo()
        element["align"] = mode
        self.var_align.set(self._align_label(mode))
        self._load_selected_to_form()
        self._draw_preview()
        self.status.set(f"Alineacion de texto: {self._align_label(mode).lower()}.")
        self._refresh_dirty_state()
        return "break"

    def toggle_selected_bold(self) -> str:
        element = self._selected_element()
        if not element or element.get("locked", False) or str(element.get("type", "")) not in {"text", "value", "field"}:
            self.status.set("Selecciona un bloque de texto editable para cambiar negrita.")
            return "break"
        self._push_undo()
        element["bold"] = not bool(element.get("bold", True))
        self._load_selected_to_form()
        self._draw_preview()
        self.status.set("Negrita activada." if element["bold"] else "Negrita desactivada.")
        self._refresh_dirty_state()
        return "break"

    def _read_int(self, value: str, fallback) -> int:
        try:
            return int(float(str(value).replace(",", ".")))
        except Exception:
            return int(fallback) if str(fallback).strip() else 0

    def _snap(self, value: int) -> int:
        return round(value / 10) * 10 if self.var_snap.get() else value

    def _new_element_id(self, prefix: str) -> str:
        existing = {str(item.get("id", "")) for item in self._elements()}
        counter = 1
        while f"{prefix}_{counter}" in existing:
            counter += 1
        return f"{prefix}_{counter}"

    def _make_new_element(self, kind: str) -> dict:
        kind = kind if kind in self.TYPE_CHOICES else "field"
        if kind == "line":
            return {"id": self._new_element_id("linea"), "type": "line", "x1": 120, "y1": 120, "x2": 700, "y2": 120, "fill": "black", "line_width": 2, "visible": True}
        if kind == "rect":
            return {"id": self._new_element_id("rectangulo"), "type": "rect", "x": 120, "y": 120, "w": 420, "h": 120, "outline": "black", "line_width": 2, "visible": True}
        if kind == "text":
            return {"id": self._new_element_id("texto"), "type": "text", "text": "TEXTO NUEVO", "x": 120, "y": 120, "w": 620, "h": 80, "font_size": 48, "min_size": 28, "bold": True, "fill": "black", "align": "left", "visible": True}
        if kind == "value":
            return {"id": self._new_element_id("variable"), "type": "value", "key": "lote", "x": 120, "y": 120, "w": 620, "h": 90, "font_size": 54, "min_size": 30, "bold": True, "fill": "black", "align": "left", "visible": True}
        return {"id": self._new_element_id("campo"), "type": "field", "label": "NUEVO CAMPO", "key": "lote", "x": 120, "y": 120, "w": 620, "label_size": 38, "value_size": 58, "min_size": 30, "bold": True, "label_fill": "#373737", "fill": "black", "value_offset": 52, "visible": True}

    def _safe_area_bbox_template(self) -> tuple[int, int, int, int]:
        width_mm, height_mm = self._label_size_mm()
        safe_margin_mm = self._safe_margin_mm()
        margin_x = int(self._base_width() * safe_margin_mm / max(width_mm, 1))
        margin_y = int(self._base_height() * safe_margin_mm / max(height_mm, 1))
        return margin_x, margin_y, self._base_width() - margin_x, self._base_height() - margin_y

    def _bbox_inside(self, inner: tuple[int, int, int, int], outer: tuple[int, int, int, int]) -> bool:
        return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]

    def _bboxes_overlap(self, first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> bool:
        x1 = max(first[0], second[0])
        y1 = max(first[1], second[1])
        x2 = min(first[2], second[2])
        y2 = min(first[3], second[3])
        return (x2 - x1) > 8 and (y2 - y1) > 8

    def _is_text_like(self, element: dict) -> bool:
        return str(element.get("type", "")) in {"text", "value", "field"}

    def _element_text_for_validation(self, element: dict) -> str:
        values = self._sample_values()
        template_text = str(element.get("template", "")).strip()
        if template_text:
            try:
                return template_text.format_map(values)
            except Exception:
                return template_text
        kind = str(element.get("type", ""))
        if kind == "text":
            return str(element.get("text", ""))
        if kind == "value":
            return str(values.get(str(element.get("key", "")), element.get("key", "")))
        if kind == "field":
            key = str(element.get("key", ""))
            return f"{element.get('label', '')} {values.get(key, key)}".strip()
        return ""

    def _text_may_clip(self, element: dict, bbox: tuple[int, int, int, int]) -> bool:
        text = self._element_text_for_validation(element)
        if not text:
            return False
        width = max(bbox[2] - bbox[0], 1)
        height = max(bbox[3] - bbox[1], 1)
        size = int(element.get("font_size", element.get("value_size", 30)) or 30)
        if str(element.get("type", "")) == "field":
            values = self._sample_values()
            label_text = str(element.get("label", ""))
            value_text = str(values.get(str(element.get("key", "")), element.get("key", "")))
            label_size = int(element.get("label_size", max(size // 2, 12)) or max(size // 2, 12))
            value_size = int(element.get("value_size", size) or size)
            label_w = len(label_text) * label_size * 0.54
            value_w = len(max(value_text.splitlines() or [value_text], key=len)) * value_size * 0.56
            value_h = value_size * 0.9
            if bool(element.get("wrap", False)) and value_w > width:
                lines = max(1, int(value_w / max(width, 1)) + 1)
                value_h = lines * value_size * float(element.get("line_spacing", 1.08) or 1.08)
                value_w = min(value_w, width)
            estimated_w = max(label_w, value_w)
            estimated_h = label_size * 0.95 + value_h
            return estimated_w > width * 1.08 or estimated_h > height * 1.12
        wrap = bool(element.get("wrap", False) or element.get("type") == "field")
        estimated_w = len(max(text.splitlines() or [text], key=len)) * size * 0.56
        estimated_h = size * 1.05
        if wrap and estimated_w > width:
            lines = max(1, int(estimated_w / max(width, 1)) + 1)
            estimated_h = lines * size * 1.18
            estimated_w = min(estimated_w, width)
        return estimated_w > width * 1.08 or estimated_h > height * 1.12

    def _color_luminance(self, color: str) -> float | None:
        value = str(color or "").strip().lower()
        names = {"black": "#000000", "white": "#ffffff", "red": "#ff0000", "blue": "#0000ff", "gray": "#808080", "grey": "#808080"}
        value = names.get(value, value)
        if not re.fullmatch(r"#[0-9a-f]{6}", value):
            return None
        r = int(value[1:3], 16) / 255
        g = int(value[3:5], 16) / 255
        b = int(value[5:7], 16) / 255
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _has_low_contrast(self, element: dict) -> bool:
        fg = self._color_luminance(str(element.get("fill", "black")))
        bg = self._color_luminance(str(element.get("background", element.get("background_fill", "white"))))
        if fg is None or bg is None:
            return False
        return abs(fg - bg) < 0.28

    def _validate_template(self) -> list[str]:
        issues: list[str] = []
        seen_ids: set[str] = set()
        visible_required: set[str] = set()
        safe_bbox = self._safe_area_bbox_template()
        visible_text_boxes: list[tuple[str, tuple[int, int, int, int]]] = []
        for index, element in enumerate(self._elements()):
            element_id = str(element.get("id", f"elemento_{index}"))
            element_name = self._element_display_name(element)
            if not element.get("visible", True):
                continue
            if element_id in seen_ids:
                issues.append(f"{element_name}: identificador duplicado ({element_id})")
            seen_ids.add(element_id)
            if element_id in self.REQUIRED_IDS and element.get("visible", True):
                visible_required.add(element_id)
            bbox = self._element_bbox(element)
            if bbox:
                x1, y1, x2, y2 = bbox
                if x2 <= x1 or y2 <= y1:
                    issues.append(f"{element_name}: tamano invalido.")
                if x1 < 0 or y1 < 0 or x2 > self._base_width() or y2 > self._base_height():
                    issues.append(f"{element_name}: queda fuera de la etiqueta.")
                elif not self._bbox_inside((x1, y1, x2, y2), safe_bbox) and element_id in self.REQUIRED_IDS:
                    issues.append(f"{element_name}: queda fuera del margen seguro de impresion.")
                if self._is_text_like(element):
                    text_bbox = (x1, y1, x2, y2)
                    for other_name, other_bbox in visible_text_boxes:
                        if self._bboxes_overlap(text_bbox, other_bbox):
                            issues.append(f"{element_name}: puede solaparse con {other_name}.")
                            break
                    visible_text_boxes.append((element_name, text_bbox))
                    if self._text_may_clip(element, text_bbox):
                        issues.append(f"{element_name}: el texto puede quedar cortado dentro de su caja.")
                    if self._has_low_contrast(element):
                        issues.append(f"{element_name}: el contraste de texto puede ser bajo.")
            font_size = element.get("font_size", element.get("value_size", None))
            if font_size is not None and int(font_size) < 12:
                issues.append(f"{element_name}: fuente demasiado pequena.")
            kind = str(element.get("type", ""))
            if kind not in self.EDITABLE_TYPES:
                issues.append(f"{element_name}: tipo no reconocido ({kind}).")
            key = str(element.get("key", "")).strip()
            if key and key not in self.VARIABLE_CHOICES:
                issues.append(f"{element_name}: variable no reconocida ({key}).")
            template_text = str(element.get("template", "")).strip()
            if template_text:
                try:
                    template_text.format_map(self._sample_values())
                except Exception as exc:
                    issues.append(f"{element_name}: plantilla combinada no valida ({exc}).")
        missing = [self._element_label_by_id(item) for item in sorted(self.REQUIRED_IDS - visible_required)]
        if missing:
            issues.append("Campos importantes ocultos: " + ", ".join(missing))
        return issues

    def _refresh_template_state(self) -> None:
        if not hasattr(self, "template_state"):
            return
        issues = self._validate_template()
        if not issues:
            self.template_state.set("Estado plantilla: OK")
            return
        preview = issues[0]
        if len(issues) > 1:
            preview += f" (+{len(issues) - 1})"
        self.template_state.set("Estado plantilla: revisar - " + preview)

    def apply_changes(self, push_undo: bool = True) -> str:
        element = self._selected_element()
        if not element:
            return "break"
        if element.get("locked", False) and self.var_locked.get():
            self.status.set(f"{self._element_display_name(element)} esta bloqueado. Desbloquealo para editarlo.")
            return "break"
        if push_undo:
            self._push_undo()
        old_type = str(element.get("type", ""))
        new_type = self._type_value(self.var_type_label.get().strip() or self.var_type.get().strip() or old_type)
        if new_type not in self.EDITABLE_TYPES:
            self.status.set("Tipo de elemento no valido.")
            return "break"
        self.var_type.set(new_type)
        element["id"] = self.var_id.get().strip() or str(element.get("id", "elemento"))
        element["type"] = new_type
        key_value = self._variable_value(self.var_key.get())
        template_value = self.var_template.get().strip()
        if key_value:
            element["key"] = key_value
        else:
            element.pop("key", None)
        if template_value:
            element["template"] = template_value
        else:
            element.pop("template", None)

        if new_type == "line":
            if old_type != "line":
                x = self._read_int(self.var_x.get(), element.get("x", 100))
                y = self._read_int(self.var_y.get(), element.get("y", 100))
                w = self._read_int(self.var_w.get(), element.get("w", 400))
                element["x1"], element["y1"], element["x2"], element["y2"] = x, y, x + max(w, 50), y
                for key in ("x", "y", "w", "h"):
                    element.pop(key, None)
            dx = self._read_int(self.var_x.get(), element.get("x1", 0)) - int(element.get("x1", 0))
            dy = self._read_int(self.var_y.get(), element.get("y1", 0)) - int(element.get("y1", 0))
            element["x1"] = self._snap(int(element.get("x1", 0)) + dx)
            element["x2"] = self._snap(int(element.get("x2", 0)) + dx)
            element["y1"] = self._snap(int(element.get("y1", 0)) + dy)
            element["y2"] = self._snap(int(element.get("y2", 0)) + dy)
            if self.var_line_width.get().strip() or self.var_font.get().strip():
                element["line_width"] = max(1, self._read_int(self.var_line_width.get() or self.var_font.get(), element.get("line_width", 1)))
        else:
            if old_type == "line":
                element["x"] = self._read_int(self.var_x.get(), element.get("x1", 100))
                element["y"] = self._read_int(self.var_y.get(), element.get("y1", 100))
                element["w"] = max(80, abs(int(element.get("x2", 500)) - int(element.get("x1", 100))))
                element["h"] = 90
                for key in ("x1", "x2", "y1", "y2"):
                    element.pop(key, None)
            element["x"] = self._snap(self._read_int(self.var_x.get(), element.get("x", 0)))
            element["y"] = self._snap(self._read_int(self.var_y.get(), element.get("y", 0)))
            if self.var_w.get().strip():
                element["w"] = max(10, self._read_int(self.var_w.get(), element.get("w", 100)))
            if self.var_h.get().strip():
                element["h"] = max(10, self._read_int(self.var_h.get(), element.get("h", 70)))
        if self.var_font.get().strip():
            key = "value_size" if element.get("type") == "field" else "font_size"
            if element.get("type") != "line":
                element[key] = max(8, self._read_int(self.var_font.get(), element.get(key, 42)))
        if self.var_min_font.get().strip() and element.get("type") in {"text", "value", "field"}:
            element["min_size"] = max(8, self._read_int(self.var_min_font.get(), element.get("min_size", 28)))
        if "label" in element:
            element["label"] = self.var_label.get()
        elif new_type == "field" and self.var_label.get().strip():
            element["label"] = self.var_label.get()
        if "text" in element or new_type == "text":
            element["text"] = self.var_text.get()
        if element.get("type") in {"text", "value", "field"}:
            element["align"] = self._align_value(self.var_align.get())
        if self.var_fill.get().strip():
            element["fill"] = self.var_fill.get().strip()
        elif new_type in {"text", "value", "field", "line"}:
            element.pop("fill", None)
        if self.var_outline.get().strip():
            if new_type == "rect" and self.var_fill.get().strip() and self.var_outline.get().strip().lower() in {"none", "sin", "-"}:
                element["fill"] = self.var_fill.get().strip()
                element.pop("outline", None)
            else:
                element["outline"] = self.var_outline.get().strip()
        elif new_type == "rect":
            element.setdefault("outline", "black")
        if self.var_label_fill.get().strip():
            element["label_fill"] = self.var_label_fill.get().strip()
        if self.var_value_offset.get().strip():
            element["value_offset"] = max(0, self._read_int(self.var_value_offset.get(), element.get("value_offset", 52)))
        if self.var_line_spacing.get().strip():
            try:
                element["line_spacing"] = max(0.8, min(float(self.var_line_spacing.get().replace(",", ".")), 2.0))
            except Exception:
                element["line_spacing"] = 1.08
        if self.var_line_width.get().strip() and new_type in {"line", "rect"}:
            element["line_width"] = max(1, self._read_int(self.var_line_width.get(), element.get("line_width", 1)))
        element["visible"] = bool(self.var_visible.get())
        element["locked"] = bool(self.var_locked.get())
        if element.get("type") in {"text", "value", "field"}:
            element["bold"] = bool(self.var_bold.get())
            element["wrap"] = bool(self.var_wrap.get())
        self._populate_elements()
        self._load_selected_to_form()
        self._draw_preview()
        self.form_pending = False
        self._refresh_lock_state()
        self._refresh_dirty_state()
        return "break"

    def save_changes(self) -> str:
        self.apply_changes(push_undo=False)
        self.template = normalize_template_to_safe_area(self.template)
        issues = self._validate_template()
        if issues:
            detail = "\n".join(f"- {issue}" for issue in issues[:10])
            if len(issues) > 10:
                detail += f"\n- ... y {len(issues) - 10} avisos mas"
            if not messagebox.askyesno("Validacion de plantilla", f"Se han detectado avisos:\n\n{detail}\n\n¿Guardar igualmente?", parent=self):
                self.status.set("Guardado cancelado por validacion.")
                return "break"
        path = save_label_template(self.template)
        self.saved_snapshot = self._snapshot()
        self.status.set(f"Plantilla guardada: {path}")
        self.form_pending = False
        self._refresh_dirty_state()
        if callable(self.on_saved):
            self.on_saved()
        return "break"

    def validate_template_now(self) -> str:
        self.apply_changes(push_undo=False)
        issues = self._validate_template()
        if not issues:
            messagebox.showinfo("Plantilla valida", "No se han detectado avisos en la plantilla.", parent=self)
            self.status.set("Plantilla validada sin avisos.")
            return "break"
        detail = "\n".join(f"- {issue}" for issue in issues[:12])
        if len(issues) > 12:
            detail += f"\n- ... y {len(issues) - 12} avisos mas"
        messagebox.showwarning("Avisos de plantilla", detail, parent=self)
        self.status.set(f"Plantilla validada con {len(issues)} aviso(s).")
        return "break"

    def save_template_as(self) -> str:
        self.apply_changes(push_undo=False)
        selected = filedialog.asksaveasfilename(parent=self, title="Exportar copia de plantilla", initialdir=str(LABEL_TEMPLATE_PATH.parent), defaultextension=".json", filetypes=[("Plantilla JSON", "*.json")], initialfile="plantilla_etiqueta_copia.json")
        if not selected:
            return "break"
        Path(selected).write_text(json.dumps(self.template, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status.set(f"Copia exportada: {selected}. La plantilla activa no cambia hasta pulsar Guardar.")
        self._refresh_dirty_state()
        return "break"

    def restore_latest_backup(self) -> str:
        backup_dir = LABEL_TEMPLATE_PATH.parent / "backups"
        backups = sorted(backup_dir.glob("plantilla_etiqueta_backup_*.json"), key=lambda item: item.stat().st_mtime, reverse=True) if backup_dir.exists() else []
        if not backups:
            messagebox.showinfo("Sin copias", "No hay copias de seguridad de plantilla disponibles.", parent=self)
            return "break"
        latest = backups[0]
        if not messagebox.askyesno("Restaurar ultimo backup", f"Se cargara la ultima copia:\n\n{latest.name}\n\nRevisala y pulsa Guardar para aplicarla a impresion. ¿Continuar?", parent=self):
            return "break"
        try:
            data = json.loads(latest.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "elements" not in data:
                raise ValueError("La copia no contiene una plantilla valida.")
        except Exception as exc:
            messagebox.showerror("No se pudo restaurar", str(exc), parent=self)
            return "break"
        self._push_undo()
        self.template = normalize_template_to_safe_area(data)
        self.selected_index = 0
        self._sync_size_controls()
        self._populate_elements()
        self._select_first_editable()
        self.status.set(f"Backup cargado: {latest.name}. Pulsa Guardar para aplicarlo.")
        self._refresh_dirty_state()
        return "break"

    def print_test_label(self) -> str:
        self.apply_changes(push_undo=False)
        printer = ""
        if callable(self.printer_provider):
            try:
                printer = str(self.printer_provider() or "").strip()
            except Exception:
                printer = ""
        if not printer:
            messagebox.showerror("Sin impresora", "Selecciona una impresora en la pantalla principal antes de imprimir la prueba.", parent=self)
            return "break"
        if not messagebox.askyesno("Imprimir prueba", f"Se enviara 1 etiqueta de prueba a:\n\n{printer}\n\nUsara el diseño actual del editor, aunque no este guardado. ¿Continuar?", parent=self):
            return "break"
        try:
            printed = print_labels_windows([replace(self._sample_box(), etiquetas=1)], printer, template=self.template)
        except Exception as exc:
            messagebox.showerror("No se pudo imprimir", str(exc), parent=self)
            return "break"
        self.status.set(f"Etiqueta de prueba enviada a impresion: {printed}")
        return "break"

    def load_template_file(self) -> str:
        selected = filedialog.askopenfilename(parent=self, title="Cargar plantilla", initialdir=str(LABEL_TEMPLATE_PATH.parent), filetypes=[("Plantilla JSON", "*.json")])
        if not selected:
            return "break"
        try:
            data = json.loads(Path(selected).read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "elements" not in data:
                raise ValueError("El archivo no contiene una plantilla valida.")
        except Exception as exc:
            messagebox.showerror("No se pudo cargar", str(exc), parent=self)
            return "break"
        self._push_undo()
        self.template = normalize_template_to_safe_area(data)
        self.selected_index = 0
        self._sync_size_controls()
        self._populate_elements()
        self._select_first_editable()
        self.status.set(f"Plantilla cargada: {selected}")
        return "break"

    def reset_template(self) -> str:
        if not messagebox.askyesno("Restaurar plantilla", "Se restaurara el diseno por defecto. ¿Continuar?", parent=self):
            return "break"
        self._push_undo()
        reset_label_template()
        self.template = normalize_template_to_safe_area(load_label_template())
        self._populate_elements()
        self._select_first_editable()
        self._draw_preview()
        self.saved_snapshot = self._snapshot()
        self.status.set("Plantilla restaurada a valores por defecto.")
        self.form_pending = False
        self._sync_size_controls()
        self._refresh_dirty_state()
        if callable(self.on_saved):
            self.on_saved()
        return "break"

    def undo(self) -> str:
        if not self.history:
            self.status.set("No hay cambios para deshacer.")
            return "break"
        self.future.append(self._snapshot())
        self._restore_snapshot(self.history.pop())
        self.status.set("Cambio deshecho.")
        self._refresh_dirty_state()
        return "break"

    def redo(self) -> str:
        if not self.future:
            self.status.set("No hay cambios para rehacer.")
            return "break"
        self.history.append(self._snapshot())
        self._restore_snapshot(self.future.pop())
        self.status.set("Cambio rehecho.")
        self._refresh_dirty_state()
        return "break"

    def duplicate_element(self) -> str:
        element = self._selected_element()
        if not element:
            return "break"
        self._push_undo()
        clone = json.loads(json.dumps(element))
        base_id = str(clone.get("id", "elemento")) + "_copia"
        existing = {str(item.get("id", "")) for item in self._elements()}
        new_id = base_id
        counter = 2
        while new_id in existing:
            new_id = f"{base_id}_{counter}"
            counter += 1
        clone["id"] = new_id
        clone["locked"] = False
        if clone.get("type") == "line":
            for key in ("x1", "x2", "y1", "y2"):
                clone[key] = int(clone.get(key, 0)) + 24
        else:
            clone["x"] = int(clone.get("x", 0)) + 24
            clone["y"] = int(clone.get("y", 0)) + 24
        insert_at = (self.selected_index or 0) + 1
        self._elements().insert(insert_at, clone)
        self._populate_elements()
        self._select_index(insert_at)
        self.status.set(f"Elemento duplicado: {new_id}")
        self._refresh_dirty_state()
        return "break"

    def copy_element(self) -> str:
        element = self._selected_element()
        if element:
            self.clipboard_element = json.loads(json.dumps(element))
            self.status.set(f"Elemento copiado: {element.get('id', '')}")
        return "break"

    def paste_element(self) -> str:
        if not self.clipboard_element:
            self.status.set("No hay ningun elemento copiado.")
            return "break"
        self._push_undo()
        clone = json.loads(json.dumps(self.clipboard_element))
        base_id = str(clone.get("id", "elemento")) + "_pegado"
        existing = {str(item.get("id", "")) for item in self._elements()}
        new_id = base_id
        counter = 2
        while new_id in existing:
            new_id = f"{base_id}_{counter}"
            counter += 1
        clone["id"] = new_id
        clone["locked"] = False
        self._move_element(clone, 32, 32)
        insert_at = (self.selected_index + 1) if self.selected_index is not None else len(self._elements())
        self._elements().insert(insert_at, clone)
        self._populate_elements()
        self._select_index(insert_at)
        self.status.set(f"Elemento pegado: {new_id}")
        self._refresh_dirty_state()
        return "break"

    def insert_variable(self, key: str) -> str:
        token = "{" + key + "}"
        current = self.var_template.get().strip()
        self.var_template.set(f"{current} {token}".strip() if current else token)
        self._show_variable_preview()
        return "break"

    def apply_footer_preset(self) -> str:
        footer_index = next((i for i, item in enumerate(self._elements()) if item.get("id") == "pie"), None)
        if footer_index is None:
            messagebox.showinfo("Pie no encontrado", "No existe un elemento con ID 'pie'.", parent=self)
            return "break"
        self._push_undo()
        footer = self._elements()[footer_index]
        footer["type"] = "value"
        footer["template"] = self.var_footer_preset.get().strip()
        footer.pop("key", None)
        footer.setdefault("font_size", 46)
        footer.setdefault("min_size", 30)
        footer.setdefault("fill", "black")
        footer.setdefault("align", "left")
        footer["visible"] = True
        self._select_index(footer_index)
        self.status.set(f"Pie actualizado: {footer['template']}")
        self._refresh_dirty_state()
        return "break"

    def align_selected(self, mode: str) -> str:
        element = self._selected_element()
        if not element or element.get("locked", False):
            return "break"
        bbox = self._element_bbox(element)
        if not bbox:
            return "break"
        self._push_undo()
        x1, _y1, x2, _y2 = bbox
        width = x2 - x1
        safe_x1, _safe_y1, safe_x2, _safe_y2 = self._safe_area_bbox_template()
        if element.get("type") == "line":
            if mode == "left":
                dx = safe_x1 - x1
            elif mode == "center":
                dx = safe_x1 + ((safe_x2 - safe_x1) - width) // 2 - x1
            else:
                dx = (safe_x2 - width) - x1
            self._move_element(element, dx, 0)
        else:
            if mode == "left":
                element["x"] = safe_x1
            elif mode == "center":
                element["x"] = safe_x1 + ((safe_x2 - safe_x1) - width) // 2
            else:
                element["x"] = safe_x2 - width
            if element.get("type") in {"text", "value", "field"}:
                element["align"] = mode if mode in {"left", "center", "right"} else element.get("align", "left")
        self._load_selected_to_form()
        self._draw_preview()
        self._refresh_dirty_state()
        return "break"

    def full_width_selected(self) -> str:
        element = self._selected_element()
        if not element or element.get("locked", False):
            return "break"
        self._push_undo()
        if element.get("type") == "line":
            safe_x1, _safe_y1, safe_x2, _safe_y2 = self._safe_area_bbox_template()
            element["x1"] = safe_x1
            element["x2"] = safe_x2
        else:
            safe_x1, _safe_y1, safe_x2, _safe_y2 = self._safe_area_bbox_template()
            element["x"] = safe_x1
            element["w"] = safe_x2 - safe_x1
        self._load_selected_to_form()
        self._draw_preview()
        self._refresh_dirty_state()
        return "break"

    def center_selected(self, axis: str) -> str:
        element = self._selected_element()
        if not element or element.get("locked", False):
            self.status.set("Selecciona un elemento editable para centrarlo.")
            return "break"
        bbox = self._element_bbox(element)
        if not bbox:
            return "break"
        x1, y1, x2, y2 = bbox
        self._push_undo()
        safe_x1, safe_y1, safe_x2, safe_y2 = self._safe_area_bbox_template()
        if axis == "horizontal":
            dx = safe_x1 + ((safe_x2 - safe_x1) - (x2 - x1)) // 2 - x1
            self._move_element(element, dx, 0)
            if element.get("type") in {"text", "value", "field"}:
                element["align"] = "center"
        else:
            dy = safe_y1 + ((safe_y2 - safe_y1) - (y2 - y1)) // 2 - y1
            self._move_element(element, 0, dy)
        self._load_selected_to_form()
        self._draw_preview()
        self.status.set("Elemento centrado " + ("horizontalmente." if axis == "horizontal" else "verticalmente."))
        self._refresh_dirty_state()
        return "break"

    def lock_structure_elements(self) -> str:
        self._push_undo()
        count = 0
        for element in self._elements():
            if str(element.get("id", "")) in self.STRUCTURE_IDS:
                if not element.get("locked", False):
                    count += 1
                element["locked"] = True
        self._load_selected_to_form()
        self._draw_preview()
        self.status.set(f"Estructura protegida: {count} elementos bloqueados.")
        self._refresh_dirty_state()
        return "break"

    def repair_template(self) -> str:
        current_issues = self._validate_template()
        if current_issues:
            detail = "\n".join(f"- {issue}" for issue in current_issues[:8])
            if len(current_issues) > 8:
                detail += f"\n- ... y {len(current_issues) - 8} avisos mas"
            message = f"Se intentaran reparar estos avisos:\n\n{detail}\n\n¿Continuar?"
        else:
            message = "No hay avisos graves, pero se revisaran campos obligatorios, bloqueo de estructura y limites de etiqueta.\n\n¿Continuar?"
        if not messagebox.askyesno("Reparar plantilla", message, parent=self):
            return "break"
        self._push_undo()
        defaults = {str(item.get("id", "")): item for item in DEFAULT_LABEL_TEMPLATE.get("elements", [])}
        existing_ids = {str(item.get("id", "")) for item in self._elements()}
        added = 0
        changed = 0
        repair_notes: list[str] = []
        for required_id in sorted(self.REQUIRED_IDS):
            if required_id not in existing_ids and required_id in defaults:
                self._elements().append(json.loads(json.dumps(defaults[required_id])))
                existing_ids.add(required_id)
                added += 1
                repair_notes.append(f"Añadido: {self._element_label_by_id(required_id)}")
        for element in self._elements():
            element_id = str(element.get("id", ""))
            element_name = self._element_display_name(element)
            if element_id in self.STRUCTURE_IDS and not element.get("locked", False):
                element["locked"] = True
                changed += 1
                repair_notes.append(f"Protegido: {element_name}")
            if element_id in self.REQUIRED_IDS and not element.get("visible", True):
                element["visible"] = True
                changed += 1
                repair_notes.append(f"Mostrado: {element_name}")
            key = str(element.get("key", "")).strip()
            if key and key not in self.VARIABLE_CHOICES:
                element.pop("key", None)
                changed += 1
                repair_notes.append(f"Variable no reconocida retirada: {element_name}")
            if str(element.get("type", "")) not in self.EDITABLE_TYPES:
                element["type"] = "field"
                element.setdefault("key", "lote")
                element.setdefault("label", "CAMPO")
                changed += 1
                repair_notes.append(f"Tipo corregido: {element_name}")
            if self._clamp_element_inside_label(element):
                changed += 1
                repair_notes.append(f"Recolocado dentro de etiqueta: {element_name}")
        self._populate_elements()
        if self.selected_index is None and self._elements():
            self.selected_index = 0
        if self.selected_index is not None:
            self._select_index(min(self.selected_index, len(self._elements()) - 1))
        self._draw_preview()
        self.status.set(f"Plantilla reparada: {added} campos añadidos, {changed} ajustes aplicados.")
        if repair_notes:
            detail = "\n".join(f"- {item}" for item in repair_notes[:12])
            if len(repair_notes) > 12:
                detail += f"\n- ... y {len(repair_notes) - 12} ajustes mas"
            messagebox.showinfo("Reparacion aplicada", detail, parent=self)
        else:
            messagebox.showinfo("Reparacion aplicada", "No ha sido necesario cambiar la plantilla.", parent=self)
        self._refresh_dirty_state()
        return "break"

    def _clamp_element_inside_label(self, element: dict) -> bool:
        sx1, sy1, sx2, sy2 = self._safe_area_bbox_template()
        changed = False
        kind = str(element.get("type", ""))
        if kind == "line":
            for key in ("x1", "x2"):
                original = int(element.get(key, 0))
                element[key] = max(sx1, min(sx2, original))
                changed = changed or element[key] != original
            for key in ("y1", "y2"):
                original = int(element.get(key, 0))
                element[key] = max(sy1, min(sy2, original))
                changed = changed or element[key] != original
            return changed
        if kind not in {"rect", "text", "value", "field"}:
            return False
        max_width = max(24, sx2 - sx1)
        max_height = max(24, sy2 - sy1)
        width = max(24, min(int(element.get("w", 100)), max_width))
        height = int(element.get("h", 180 if kind == "field" else 70))
        height = max(24, min(height, max_height))
        x = int(element.get("x", 0))
        y = int(element.get("y", 0))
        new_x = max(sx1, min(sx2 - width, x))
        new_y = max(sy1, min(sy2 - height, y))
        if width != int(element.get("w", 100)):
            element["w"] = width
            changed = True
        if kind in {"rect", "text", "value", "field"} and height != int(element.get("h", 180 if kind == "field" else 70)):
            element["h"] = height
            changed = True
        if new_x != x:
            element["x"] = new_x
            changed = True
        if new_y != y:
            element["y"] = new_y
            changed = True
        return changed

    def _template_variables(self) -> list[str]:
        variables: set[str] = set()
        known = set(self.VARIABLE_CHOICES)
        for element in self._elements():
            key = str(element.get("key", "")).strip()
            if key:
                variables.add(key)
            template = str(element.get("template", "")).strip()
            if template:
                variables.update(name for name in re.findall(r"{([A-Za-z0-9_]+)}", template) if name in known)
        return sorted(variables)

    def _refresh_used_fields(self) -> None:
        variables = self._template_variables()
        if not variables:
            self.used_fields_info.set("Variables usadas: -")
            return
        self.used_fields_info.set("Variables usadas: " + ", ".join(self._variable_label(item) for item in variables))

    def add_element(self) -> str:
        self._push_undo()
        element = self._make_new_element(self._type_value(self.var_add_type_label.get()))
        insert_at = (self.selected_index + 1) if self.selected_index is not None else len(self._elements())
        self._elements().insert(insert_at, element)
        self._populate_elements()
        self._select_index(insert_at)
        self.status.set(f"Elemento añadido: {self._element_display_name(element)}.")
        self._refresh_dirty_state()
        return "break"

    def add_preset_field(self) -> str:
        selected = self.var_field_preset.get().strip()
        preset = next((item for item in self.FIELD_PRESETS if item[0] == selected), self.FIELD_PRESETS[0])
        label, key, printed_label = preset
        self._push_undo()
        element = self._make_new_element("field")
        element["id"] = self._new_element_id(re.sub(r"[^a-z0-9_]+", "_", key.lower()).strip("_") or "campo")
        element["label"] = printed_label
        element["key"] = key
        element["x"] = 120
        element["y"] = min(1180, 180 + len(self._elements()) * 12)
        element["w"] = 720
        insert_at = (self.selected_index + 1) if self.selected_index is not None else len(self._elements())
        self._elements().insert(insert_at, element)
        self._populate_elements()
        self._select_index(insert_at)
        self.status.set(f"Dato añadido: {label}. Colocalo arrastrando sobre la etiqueta.")
        self._refresh_dirty_state()
        return "break"

    def delete_element(self) -> str:
        element = self._selected_element()
        if not element or self.selected_index is None:
            return "break"
        element_id = str(element.get("id", ""))
        element_name = self._element_display_name(element)
        if element.get("locked", False):
            self.status.set(f"{element_name} esta bloqueado. Desbloquealo para eliminarlo.")
            return "break"
        if element_id in self.REQUIRED_IDS:
            if not messagebox.askyesno("Eliminar campo importante", f"{element_name} es un campo importante para la etiqueta.\n\n¿Eliminarlo igualmente?", parent=self):
                return "break"
        else:
            if not messagebox.askyesno("Eliminar elemento", f"¿Eliminar {element_name}?", parent=self):
                return "break"
        self._push_undo()
        del self._elements()[self.selected_index]
        if self._elements():
            self.selected_index = min(self.selected_index, len(self._elements()) - 1)
        else:
            self.selected_index = None
        self._populate_elements()
        if self.selected_index is not None:
            self._select_index(self.selected_index)
        else:
            self._draw_preview()
        self.status.set(f"Elemento eliminado: {element_name}")
        self._refresh_dirty_state()
        return "break"

    def restore_selected_element(self) -> str:
        element = self._selected_element()
        if not element or self.selected_index is None:
            return "break"
        element_id = str(element.get("id", ""))
        element_name = self._element_display_name(element)
        defaults = {str(item.get("id", "")): item for item in DEFAULT_LABEL_TEMPLATE.get("elements", [])}
        if element_id not in defaults:
            messagebox.showinfo("Sin original", f"{element_name} no existe en la plantilla por defecto.", parent=self)
            return "break"
        if not messagebox.askyesno("Restaurar elemento", f"¿Restaurar {element_name} a su estado por defecto?", parent=self):
            return "break"
        self._push_undo()
        self._elements()[self.selected_index] = json.loads(json.dumps(defaults[element_id]))
        self._populate_elements()
        self._select_index(self.selected_index)
        self.status.set(f"Elemento restaurado: {element_name}")
        self._refresh_dirty_state()
        return "break"

    def bring_forward(self) -> str:
        if self.selected_index is None or self.selected_index >= len(self._elements()) - 1:
            return "break"
        self._push_undo()
        elements = self._elements()
        elements[self.selected_index], elements[self.selected_index + 1] = elements[self.selected_index + 1], elements[self.selected_index]
        self._select_index(self.selected_index + 1)
        self._refresh_dirty_state()
        return "break"

    def send_backward(self) -> str:
        if self.selected_index is None or self.selected_index <= 0:
            return "break"
        self._push_undo()
        elements = self._elements()
        elements[self.selected_index], elements[self.selected_index - 1] = elements[self.selected_index - 1], elements[self.selected_index]
        self._select_index(self.selected_index - 1)
        self._refresh_dirty_state()
        return "break"

    def toggle_selected_visible(self, visible: bool) -> str:
        element = self._selected_element()
        if element and not element.get("locked", False):
            self._push_undo()
            element["visible"] = visible
            self.var_visible.set(visible)
            self._populate_elements()
            self._draw_preview()
            self.status.set(f"{self._element_display_name(element)} mostrado." if visible else f"{self._element_display_name(element)} ocultado.")
            self._refresh_dirty_state()
        elif element:
            self.status.set(f"{self._element_display_name(element)} esta bloqueado. Desbloquealo para cambiar visibilidad.")
        return "break"

    def _key_step(self, event) -> int:
        return 10 if event.state & 0x0001 else 1

    def move_selected(self, dx: int, dy: int) -> str:
        element = self._selected_element()
        if not element:
            return "break"
        if element.get("locked", False):
            self.status.set(f"{self._element_display_name(element)} esta bloqueado. Desbloquealo para moverlo.")
            return "break"
        self._push_undo()
        self._move_element(element, dx, dy)
        self._load_selected_to_form()
        self._draw_preview()
        self._refresh_dirty_state()
        return "break"

    def _move_element(self, element: dict, dx: int, dy: int) -> None:
        if element.get("type") == "line":
            element["x1"] = int(element.get("x1", 0)) + dx
            element["x2"] = int(element.get("x2", 0)) + dx
            element["y1"] = int(element.get("y1", 0)) + dy
            element["y2"] = int(element.get("y2", 0)) + dy
            return
        element["x"] = int(element.get("x", 0)) + dx
        element["y"] = int(element.get("y", 0)) + dy

    def _draw_preview(self) -> None:
        if not hasattr(self, "preview_canvas"):
            return
        self.update_idletasks()
        zoom_text = self.var_zoom.get()
        if zoom_text == "Ajustar":
            image = render_label(self._sample_box(), dpi=120, template=self.template)
            max_w = max(self.preview_canvas.winfo_width() - 36, 360)
            max_h = max(self.preview_canvas.winfo_height() - 36, 520)
            image.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        else:
            factor = int(zoom_text.rstrip("%")) / 100
            image = render_label(self._sample_box(), dpi=max(int(300 * factor), 40), template=self.template)
        self.preview_scale = image.width / self._base_width()
        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview_canvas.delete("all")
        x = max((self.preview_canvas.winfo_width() - image.width) // 2, 18)
        y = max((self.preview_canvas.winfo_height() - image.height) // 2, 18)
        self.preview_origin = (x, y)
        self.preview_canvas.create_image(x, y, image=self.preview_photo, anchor="nw")
        self.preview_canvas.configure(scrollregion=(0, 0, max(self.preview_canvas.winfo_width(), x + image.width + 18), max(self.preview_canvas.winfo_height(), y + image.height + 18)))
        if self.var_safe_area.get():
            self._draw_safe_area(x, y)
        if self.var_grid.get():
            self._draw_grid(x, y)
        if self.var_guides.get():
            self._draw_guides(x, y)
        self._draw_hover_and_selection(x, y)

    def _draw_grid(self, ox: int, oy: int) -> None:
        step = 100 * self.preview_scale
        if step < 12:
            step = 50 * self.preview_scale
        x2 = ox + self._base_width() * self.preview_scale
        y2 = oy + self._base_height() * self.preview_scale
        pos = ox
        while pos <= x2:
            self.preview_canvas.create_line(pos, oy, pos, y2, fill="#D8E1EE", width=1)
            pos += step
        pos = oy
        while pos <= y2:
            self.preview_canvas.create_line(ox, pos, x2, pos, fill="#D8E1EE", width=1)
            pos += step

    def _draw_guides(self, ox: int, oy: int) -> None:
        element = self._selected_element()
        if not element:
            return
        bbox = self._element_bbox(element)
        if not bbox:
            return
        x1, y1, x2, y2 = bbox
        cx = ox + ((x1 + x2) / 2) * self.preview_scale
        cy = oy + ((y1 + y2) / 2) * self.preview_scale
        self.preview_canvas.create_line(cx, oy, cx, oy + self._base_height() * self.preview_scale, fill="#E31B1B", dash=(3, 4))
        self.preview_canvas.create_line(ox, cy, ox + self._base_width() * self.preview_scale, cy, fill="#E31B1B", dash=(3, 4))

    def _draw_safe_area(self, ox: int, oy: int) -> None:
        width_mm, height_mm = self._label_size_mm()
        safe_margin_mm = self._safe_margin_mm()
        margin_x = int(self._base_width() * safe_margin_mm / max(width_mm, 1))
        margin_y = int(self._base_height() * safe_margin_mm / max(height_mm, 1))
        x1 = ox + margin_x * self.preview_scale
        y1 = oy + margin_y * self.preview_scale
        x2 = ox + (self._base_width() - margin_x) * self.preview_scale
        y2 = oy + (self._base_height() - margin_y) * self.preview_scale
        self.preview_canvas.create_rectangle(x1, y1, x2, y2, outline="#0B7A5A", width=2, dash=(8, 5))
        self.preview_canvas.create_text(x1 + 8, y1 + 12, text=f"margen seguro {safe_margin_mm:g} mm", fill="#0B7A5A", anchor="w", font=("Segoe UI", 8, "bold"))

    def _draw_hover_and_selection(self, ox: int, oy: int) -> None:
        for index, color, width, dash in (
            (self.hover_index, "#0067D8", 1, (2, 3)),
            (self.selected_index, ACCENT_RED, 2, (5, 3)),
        ):
            if index is None or not (0 <= index < len(self._elements())):
                continue
            bbox = self._element_bbox(self._elements()[index])
            if not bbox:
                continue
            x1, y1, x2, y2 = bbox
            self.preview_canvas.create_rectangle(ox + x1 * self.preview_scale, oy + y1 * self.preview_scale, ox + x2 * self.preview_scale, oy + y2 * self.preview_scale, outline=color, width=width, dash=dash)
            if index == self.selected_index and not self._elements()[index].get("locked", False):
                handle = max(9, int(13 * self.preview_scale))
                hx = ox + x2 * self.preview_scale
                hy = oy + y2 * self.preview_scale
                self.preview_canvas.create_rectangle(hx - handle, hy - handle, hx + handle, hy + handle, fill=ACCENT_RED, outline="white", width=2)

    def _on_preview_pan_start(self, event) -> str:
        self.preview_canvas.scan_mark(event.x, event.y)
        self.preview_pan_start = (event.x, event.y)
        self.preview_canvas.configure(cursor="fleur")
        return "break"

    def _on_preview_pan_move(self, event) -> str:
        if self.preview_pan_start is not None:
            self.preview_canvas.scan_dragto(event.x, event.y, gain=1)
        return "break"

    def _on_preview_pan_end(self, _event) -> str:
        self.preview_pan_start = None
        self.preview_canvas.configure(cursor="")
        return "break"

    def _element_bbox(self, element: dict) -> tuple[int, int, int, int] | None:
        kind = element.get("type")
        if kind == "line":
            x1, y1, x2, y2 = int(element.get("x1", 0)), int(element.get("y1", 0)), int(element.get("x2", 0)), int(element.get("y2", 0))
            pad = max(10, int(element.get("line_width", 1)) * 2)
            return min(x1, x2), min(y1, y2) - pad, max(x1, x2), max(y1, y2) + pad
        if kind in {"rect", "text", "value"}:
            return int(element.get("x", 0)), int(element.get("y", 0)), int(element.get("x", 0)) + int(element.get("w", 100)), int(element.get("y", 0)) + int(element.get("h", 70))
        if kind == "field":
            return int(element.get("x", 0)), int(element.get("y", 0)), int(element.get("x", 0)) + int(element.get("w", 100)), int(element.get("y", 0)) + int(element.get("h", 180))
        return None

    def _hit_test(self, event_x: int, event_y: int) -> int | None:
        ox, oy = self.preview_origin
        x = (event_x - ox) / max(self.preview_scale, 0.01)
        y = (event_y - oy) / max(self.preview_scale, 0.01)
        for index in range(len(self._elements()) - 1, -1, -1):
            bbox = self._element_bbox(self._elements()[index])
            if bbox and bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]:
                return index
        return None

    def _is_resize_handle(self, event_x: int, event_y: int) -> bool:
        element = self._selected_element()
        if not element or element.get("locked", False):
            return False
        bbox = self._element_bbox(element)
        if not bbox:
            return False
        ox, oy = self.preview_origin
        x2 = ox + bbox[2] * self.preview_scale
        y2 = oy + bbox[3] * self.preview_scale
        margin = max(12, int(18 * self.preview_scale))
        return abs(event_x - x2) <= margin and abs(event_y - y2) <= margin

    def _on_canvas_motion(self, event) -> None:
        if self._is_resize_handle(event.x, event.y):
            self.preview_canvas.configure(cursor="size_nw_se")
            return
        hit = self._hit_test(event.x, event.y)
        if hit != self.hover_index:
            self.hover_index = hit
            self.preview_canvas.configure(cursor="hand2" if hit is not None else "")
            self._draw_preview()

    def _on_canvas_leave(self, _event) -> None:
        self.hover_index = None
        self.preview_canvas.configure(cursor="")
        self._draw_preview()

    def _on_canvas_press(self, event) -> None:
        self.preview_canvas.focus_set()
        if getattr(event, "state", 0) & 0x0001:
            self._on_preview_pan_start(event)
            return
        if self._is_resize_handle(event.x, event.y):
            self.resize_mode = True
            self.drag_start = (event.x, event.y)
            self.drag_origin = dict(self._selected_element() or {})
            self.drag_snapshot = self._snapshot()
            return
        hit = self._hit_test(event.x, event.y)
        if hit is not None:
            self._select_index(hit)
        element = self._selected_element()
        if element:
            self.resize_mode = False
            self.drag_start = (event.x, event.y)
            self.drag_origin = dict(element)
            self.drag_snapshot = self._snapshot()

    def _on_canvas_double_click(self, event) -> str:
        hit = self._hit_test(event.x, event.y)
        if hit is not None:
            self._select_index(hit)
        element = self._selected_element()
        if not element:
            return "break"
        if element.get("locked", False):
            self.status.set(f"{self._element_display_name(element)} esta bloqueado. Desbloquealo para editarlo con doble clic.")
            return "break"
        kind = str(element.get("type", ""))
        self._push_undo()
        if kind == "text":
            value = simpledialog.askstring("Editar texto", "Texto que se imprimira:", initialvalue=str(element.get("text", "")), parent=self)
            if value is None:
                return "break"
            element["text"] = value
        elif kind == "field":
            label_value = simpledialog.askstring("Editar leyenda", "Leyenda del campo:", initialvalue=str(element.get("label", "")), parent=self)
            if label_value is None:
                return "break"
            element["label"] = label_value
        elif kind == "value":
            template_value = simpledialog.askstring("Editar valor", "Variable o plantilla entre llaves, por ejemplo {lote}:", initialvalue=str(element.get("template", "{" + str(element.get("key", "lote")) + "}")), parent=self)
            if template_value is None:
                return "break"
            if template_value.startswith("{") and template_value.endswith("}") and template_value.count("{") == 1:
                element["key"] = template_value.strip("{} ")
                element.pop("template", None)
            else:
                element["template"] = template_value
        else:
            self.status.set("Doble clic disponible para textos y campos de datos.")
            return "break"
        self._load_selected_to_form()
        self._populate_elements()
        self._draw_preview()
        self.status.set("Elemento editado con doble clic.")
        return "break"

    def _on_canvas_drag(self, event) -> None:
        if self.preview_pan_start is not None:
            return
        element = self._selected_element()
        if not element or not self.drag_start or not self.drag_origin:
            return
        if element.get("locked", False):
            self.status.set(f"{self._element_display_name(element)} esta bloqueado. Desbloquealo para moverlo.")
            return
        dx = int((event.x - self.drag_start[0]) / max(self.preview_scale, 0.01))
        dy = int((event.y - self.drag_start[1]) / max(self.preview_scale, 0.01))
        if self.var_snap.get():
            dx = self._snap(dx)
            dy = self._snap(dy)
        if self.resize_mode:
            if element.get("type") == "line":
                element["x2"] = max(0, min(self._base_width(), int(self.drag_origin.get("x2", 0)) + dx))
                element["y2"] = max(0, min(self._base_height(), int(self.drag_origin.get("y2", 0)) + dy))
            else:
                origin_x = int(self.drag_origin.get("x", 0))
                origin_y = int(self.drag_origin.get("y", 0))
                element["w"] = max(24, min(self._base_width() - origin_x, int(self.drag_origin.get("w", 100)) + dx))
                if element.get("type") in {"rect", "text", "value", "field"}:
                    element["h"] = max(24, min(self._base_height() - origin_y, int(self.drag_origin.get("h", 150)) + dy))
            self.status.set("Redimensionando elemento seleccionado.")
        elif element.get("type") == "line":
            element["x1"] = int(self.drag_origin.get("x1", 0)) + dx
            element["x2"] = int(self.drag_origin.get("x2", 0)) + dx
            element["y1"] = int(self.drag_origin.get("y1", 0)) + dy
            element["y2"] = int(self.drag_origin.get("y2", 0)) + dy
        else:
            element["x"] = int(self.drag_origin.get("x", 0)) + dx
            element["y"] = int(self.drag_origin.get("y", 0)) + dy
        self._load_selected_to_form()
        self._draw_preview()

    def _on_canvas_release(self, _event) -> None:
        if self.drag_snapshot is not None:
            self.history.append(self.drag_snapshot)
            self.history = self.history[-60:]
            self.future.clear()
        self.resize_mode = False
        self.drag_start = None
        self.drag_origin = None
        self.drag_snapshot = None
        self._refresh_template_state()
        self._refresh_dirty_state()


class EtiquetadoBoxApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.withdraw()
        try:
            self.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        self.title("Etiquetado box salazon")
        self.geometry("1120x720")
        self.minsize(760, 600)
        self.configure(bg=BG)
        set_window_icon(self)
        configure_style(self)
        saved_state = self._load_user_state()

        self.logo_images: list[ImageTk.PhotoImage] = []
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.resultado: ResultadoGeneracion | None = None
        self.selected_file = tk.StringVar(value="")
        self.last_partida_dir = saved_state.get("ultima_carpeta_partida", "")
        self.fecha_entrada = tk.StringVar(value=datetime.today().strftime("%d/%m/%Y"))
        self.dias_sal = tk.StringVar(value="0")
        self.rango_peso = tk.StringVar(value="")
        self.rango_info_value = tk.StringVar(value="Carga una partida para ver los rangos configurados.")
        self.range_options: dict[str, RangoSalazon] = {}
        self.range_combo: ttk.Combobox | None = None
        self._range_syncing = False
        self._applying_range = False
        self.unidades_box = tk.StringVar(value="")
        self.etiquetas_box = tk.StringVar(value=saved_state.get("etiquetas_box", "1"))
        self.printer = tk.StringVar(value="")
        self.status = tk.StringVar(value="Selecciona una partida .txt para comenzar.")
        self.summary = tk.StringVar(value="Sin datos cargados")
        self.validation_value = tk.StringVar(value="Pendiente de validar parametros")
        self.partida_info_value = tk.StringVar(value="Sin partida cargada")
        self.validation_partida = tk.StringVar(value="[ ] Partida: pendiente")
        self.validation_fechas = tk.StringVar(value="[ ] Fechas: pendiente")
        self.validation_rango = tk.StringVar(value="[ ] Rango y boxes: pendiente")
        self.validation_impresora = tk.StringVar(value="[ ] Impresora: pendiente")
        self.preview_box_value = tk.StringVar(value="Vista previa: sin etiqueta")
        self.preview_box_index = 0
        self.preview_zoom = 1.0
        self.summary_bar: CanvasSummaryBar | None = None
        self.flow_bar: CanvasFlowBar | None = None
        self.layout_mode = ""
        self.validation_cache: dict[tuple[str, float, int], tuple[list[str], list[str], str]] = {}
        self.save_after_id: str | None = None
        self.detail_lines: list[str] = []
        self.details_window: tk.Toplevel | None = None
        self.details_text: tk.Text | None = None
        self.calendar_window: tk.Toplevel | None = None
        self.calendar_month: datetime | None = None
        self.template_editor: LabelTemplateEditor | None = None
        self._build_ui()
        self._load_printers()
        self._bind_shortcuts()
        self._bind_validation_traces()
        self._refresh_validation_state()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(20, self._show_main_window)

    def _show_main_window(self) -> None:
        try:
            self.state("zoomed")
        except Exception:
            center_window(self)
        self.deiconify()
        self.lift()
        try:
            self.attributes("-alpha", 1.0)
        except tk.TclError:
            pass

    def _load_user_state(self) -> dict[str, str]:
        try:
            if not STATE_PATH.exists():
                return {}
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            result: dict[str, str] = {}
            for key in ("unidades_box", "etiquetas_box", "ultima_carpeta_partida"):
                value = str(data.get(key, "")).strip()
                if value:
                    result[key] = value
            return result
        except Exception:
            return {}

    def _save_user_state(self) -> None:
        self.save_after_id = None
        data = {
            "etiquetas_box": self.etiquetas_box.get().strip() or "1",
            "ultima_carpeta_partida": self.last_partida_dir,
        }
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            self._append_detail(f"AVISO: no se pudieron guardar preferencias de usuario: {exc}")

    def _on_close(self) -> None:
        if self.save_after_id is not None:
            try:
                self.after_cancel(self.save_after_id)
            except Exception:
                pass
            self.save_after_id = None
        self._save_user_state()
        self.destroy()

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-o>", lambda _e: self.select_file())
        self.bind("<Control-r>", lambda _e: self.generate_preview())
        self.bind("<Control-p>", lambda _e: self.print_labels())
        self.bind("<Control-s>", lambda _e: self.save_preview())
        self.bind("<Control-d>", lambda _e: self.show_details())
        self.bind("<Control-Alt-d>", lambda _e: self.open_template_editor())
        self.bind("<Control-Alt-D>", lambda _e: self.open_template_editor())

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
        self._append_detail("INFO: editor grafico de etiquetas abierto por acceso administrador.")
        if self.template_editor is not None and self.template_editor.winfo_exists():
            self.template_editor.lift()
            self.template_editor.focus_force()
            return "break"
        self.template_editor = LabelTemplateEditor(self, on_saved=self._refresh_template_after_save, sample_box_provider=self._editor_sample_box, printer_provider=lambda: self.printer.get().strip())
        self.template_editor.protocol("WM_DELETE_WINDOW", self._close_template_editor)
        return "break"

    def _close_template_editor(self) -> None:
        if self.template_editor is not None:
            if hasattr(self.template_editor, "request_close") and not self.template_editor.request_close():
                return
            if self.template_editor is not None and self.template_editor.winfo_exists():
                self.template_editor.destroy()
        self.template_editor = None

    def _editor_sample_box(self) -> BoxEtiqueta | None:
        if self.resultado is None or not self.resultado.boxes:
            return None
        index = max(0, min(self.preview_box_index, len(self.resultado.boxes) - 1))
        return self.resultado.boxes[index]

    def _refresh_template_after_save(self) -> None:
        self.status.set("Plantilla de etiqueta guardada. La vista previa se ha actualizado.")
        if self.resultado is not None:
            self._show_current_preview()

    def _bind_validation_traces(self) -> None:
        self.selected_file.trace_add("write", lambda *_args: self._on_file_changed())
        for variable in (self.fecha_entrada, self.dias_sal, self.rango_peso, self.etiquetas_box):
            variable.trace_add("write", lambda *_args: self._on_input_changed())
        self.unidades_box.trace_add("write", lambda *_args: self._on_units_box_changed())

    def _on_units_box_changed(self) -> None:
        if not self._applying_range:
            self._persist_units_preference()
        self._on_input_changed()

    def _persist_units_preference(self) -> None:
        selected = self._selected_salazon_range()
        if selected is None:
            return
        raw_units = self.unidades_box.get().strip()
        if not raw_units:
            return
        try:
            units = int(raw_units)
            if units <= 0:
                return
        except Exception:
            return
        if selected.unidades_box == units:
            return
        try:
            save_salazon_range_units(SALAZON_CONFIG_PATH, selected, units)
            self.range_options[self.rango_peso.get().strip()] = replace(selected, unidades_box=units)
            self.rango_info_value.set(f"Preferencia guardada: {units} unidades/box para {selected.range_label}. Dias sugeridos: {selected.dias_sal}.")
        except Exception as exc:
            self._append_detail(f"AVISO: no se pudo guardar unidades/box en config_salazon.csv: {exc}")
    def _on_file_changed(self) -> None:
        self._refresh_range_options()
        self._on_input_changed()

    def _on_input_changed(self) -> None:
        if self.resultado is not None:
            self.resultado = None
            self.preview_box_index = 0
            self.preview_box_value.set("Vista previa: pendiente de generar")
            self.summary.set("Sin datos cargados")
            try:
                self.preview_label.configure(image="", text="Genera la vista previa para ver la primera etiqueta.")
            except Exception:
                pass
            if hasattr(self, "tree"):
                for item in self.tree.get_children():
                    self.tree.delete(item)
        self._schedule_user_state_save()
        self._refresh_validation_state()

    def _refresh_validation_state(self) -> None:
        errors, warnings, live_summary, status_ok = self._validate_inputs_live()
        if errors:
            self.validation_value.set("Pendiente: " + " | ".join(errors[:3]))
        elif warnings:
            self.validation_value.set("Aviso: " + " | ".join(warnings[:3]))
        else:
            self.validation_value.set("Parametros validos. Puedes generar la vista previa.")
        if self.summary_bar is not None:
            self.summary_bar.set_items(live_summary, status_ok=status_ok)
        self._update_validation_panel(errors, warnings)
        for button_name in ("generate_button", "quick_generate_button"):
            button = getattr(self, button_name, None)
            if button is not None:
                button.set_enabled(not errors)
        self._set_preview_actions_state(self.resultado is not None)
        if self.flow_bar is not None:
            has_file = bool(self.selected_file.get().strip())
            params_ok = not errors
            has_preview = self.resultado is not None
            if has_preview:
                self.flow_bar.set_state(3, 2)
            elif params_ok:
                self.flow_bar.set_state(2, 1)
            elif has_file:
                self.flow_bar.set_state(1, 0)
            else:
                self.flow_bar.set_state(0, -1)

    def _set_preview_actions_state(self, enabled: bool) -> None:
        for name in ("save_button", "print_button", "quick_print_button", "prev_button", "next_button", "zoom_button"):
            button = getattr(self, name, None)
            if button is not None:
                button.set_enabled(enabled)

    def _update_validation_panel(self, errors: list[str], warnings: list[str]) -> None:
        def status_for(prefixes: tuple[str, ...], ok_text: str, pending_text: str) -> str:
            relevant_errors = [item for item in errors if any(prefix in item for prefix in prefixes)]
            relevant_warnings = [item for item in warnings if any(prefix in item for prefix in prefixes)]
            if relevant_errors:
                return "[X] " + relevant_errors[0]
            if relevant_warnings:
                return "[!] " + relevant_warnings[0]
            return "[OK] " + ok_text if not errors else "[ ] " + pending_text

        self.validation_partida.set(status_for(("partida", "lote", "articulo", "lineas", "leer", ".txt"), "Partida valida", "Partida pendiente"))
        self.validation_fechas.set(status_for(("fecha", "salida", "dias", "laborable"), "Fechas validas", "Fechas pendientes"))
        self.validation_rango.set(status_for(("peso", "rango", "unidades", "etiquetas"), "Rango y boxes validos", "Rango pendiente"))
        if not self.printer.get().strip():
            self.validation_impresora.set("[!] Impresora no seleccionada")
        else:
            self.validation_impresora.set("[OK] Impresora seleccionada")

    def _schedule_user_state_save(self) -> None:
        if self.save_after_id is not None:
            try:
                self.after_cancel(self.save_after_id)
            except Exception:
                pass
        self.save_after_id = self.after(700, self._save_user_state)

    def _set_range_combo_values(self, labels: list[str], enabled: bool) -> None:
        if self.range_combo is not None:
            self.range_combo.configure(values=labels, state="readonly" if enabled else "disabled")

    def _range_label_for(self, item: RangoSalazon) -> str:
        return item.display_label

    def _selected_salazon_range(self) -> RangoSalazon | None:
        return self.range_options.get(self.rango_peso.get().strip())

    def _single_article_from_pieces(self, pieces) -> str:
        article_codes = sorted({pieza.articulo_clave or pieza.articulo_codigo for pieza in pieces})
        if len(article_codes) != 1:
            return ""
        return article_codes[0]

    def _refresh_range_options(self) -> None:
        if self._range_syncing:
            return
        self._range_syncing = True
        try:
            self.range_options = {}
            path_text = self.selected_file.get().strip()
            if not path_text:
                self.rango_peso.set("")
                self.rango_info_value.set("Carga una partida para ver los rangos configurados.")
                self._set_range_combo_values([], False)
                return
            path = Path(path_text)
            if not path.exists():
                self.rango_peso.set("")
                self.rango_info_value.set("Partida no encontrada.")
                self._set_range_combo_values([], False)
                return
            try:
                legend = load_article_legend(ARTICULOS_PATH)
                pieces = parse_partida_file(path, legend)
                article_code = self._single_article_from_pieces(pieces)
                if not article_code:
                    self.rango_peso.set("")
                    self.rango_info_value.set("La partida contiene varios articulos; separa la partida antes de elegir rango.")
                    self._set_range_combo_values([], False)
                    return
                ranges = salazon_ranges_for_article(article_code, load_salazon_ranges(SALAZON_CONFIG_PATH))
            except Exception as exc:
                self.rango_peso.set("")
                self.rango_info_value.set(f"No se pudieron cargar rangos: {str(exc).splitlines()[0]}")
                self._set_range_combo_values([], False)
                return
            if not ranges:
                self.rango_peso.set("")
                self.rango_info_value.set("No hay rangos configurados para el articulo de la partida.")
                self._set_range_combo_values([], False)
                return
            weights = [pieza.peso for pieza in pieces]
            min_real = min(weights)
            max_real = max(weights)
            labels: list[str] = []
            coverage: dict[str, int] = {}
            for item in ranges:
                filtered_count = sum(1 for pieza in pieces if item.rango_min <= pieza.peso <= item.rango_max)
                if filtered_count <= 0:
                    continue
                units_label = f" | {item.unidades_box} uds/box" if item.unidades_box else ""
                label = f"{item.range_label} | {item.dias_sal} dias{units_label} | {filtered_count} piezas | {item.articulo_nombre}"
                if label in self.range_options:
                    label = f"{label} | codigo {item.articulo_codigo}"
                self.range_options[label] = item
                coverage[label] = filtered_count
                labels.append(label)
            if not labels:
                self.rango_peso.set("")
                self.rango_info_value.set(
                    f"Hay rangos configurados para el articulo, pero ninguno contiene piezas de esta partida. Peso real: {format_decimal(min_real)} - {format_decimal(max_real)} kg."
                )
                self._set_range_combo_values([], False)
                return
            self._set_range_combo_values(labels, True)
            current = self.rango_peso.get().strip()
            selected = current if current in self.range_options else ""
            if not selected:
                fitting = [label for label, item in self.range_options.items() if item.rango_min <= min_real and max_real <= item.rango_max]
                if len(fitting) == 1:
                    selected = fitting[0]
                elif len(labels) == 1:
                    selected = labels[0]
            self.rango_peso.set(selected)
            if selected:
                self._apply_selected_range(update_status=False)
                selected_range = self.range_options[selected]
                self.rango_info_value.set(
                    f"{coverage.get(selected, 0)} piezas en {selected_range.range_label}. Dias sugeridos: {selected_range.dias_sal}. Unidades/box sugeridas: {selected_range.unidades_box or 'sin preferencia'}."
                )
            else:
                self.rango_info_value.set(
                    f"{len(labels)} rangos con piezas disponibles. Peso real partida: {format_decimal(min_real)} - {format_decimal(max_real)} kg."
                )
        finally:
            self._range_syncing = False
    def _apply_selected_range(self, update_status: bool = True) -> None:
        selected = self._selected_salazon_range()
        if selected is None:
            return
        self._applying_range = True
        try:
            self.dias_sal.set(str(selected.dias_sal))
            if selected.unidades_box:
                self.unidades_box.set(str(selected.unidades_box))
        finally:
            self._applying_range = False
        units_text = selected.unidades_box if selected.unidades_box else "sin preferencia"
        self.rango_info_value.set(
            f"Rango {selected.range_label}. Dias sugeridos: {selected.dias_sal}. Unidades/box sugeridas: {units_text}."
        )
        if update_status:
            self.status.set("Rango aplicado. Los dias en sal quedan precargados y puedes ajustarlos si hace falta.")

    def _on_range_selected(self, _event=None) -> None:
        self._apply_selected_range(update_status=True)
        self._on_input_changed()

    def _validate_inputs_live(self) -> tuple[list[str], list[str], list[tuple[str, str]], bool]:
        errors: list[str] = []
        warnings: list[str] = []
        exit_text = "-"
        status_text = "Pendiente"
        status_ok = False
        path = Path(self.selected_file.get().strip()) if self.selected_file.get().strip() else None
        selected_range = self._selected_salazon_range()

        if path is None:
            self.partida_info_value.set("Sin partida cargada")
            return ["falta partida"], warnings, [("Jamones", "-"), ("Boxes", "-"), ("Etiquetas", "-"), ("Salida", exit_text), ("Estado", status_text)], False
        if not path.exists():
            self.partida_info_value.set("Partida no encontrada.")
            return ["partida no encontrada"], warnings, [("Jamones", "-"), ("Boxes", "-"), ("Etiquetas", "-"), ("Salida", exit_text), ("Estado", status_text)], False

        file_errors, file_warnings, partida_info = self._validate_partida_path(path)
        errors.extend(file_errors)
        warnings.extend(file_warnings)
        self.partida_info_value.set(partida_info)

        try:
            entry_date = parse_date(self.fecha_entrada.get())
        except Exception:
            entry_date = None
            errors.append("fecha entrada invalida")
        try:
            days = int(self.dias_sal.get().strip())
            if days < 0:
                errors.append("dias en sal negativo")
        except Exception:
            days = 0
            errors.append("dias en sal invalido")
        if selected_range is None:
            errors.append("selecciona rango de peso")
        else:
            try:
                legend = load_article_legend(ARTICULOS_PATH)
                pieces = parse_partida_file(path, legend)
                filtered_count = sum(1 for pieza in pieces if selected_range.rango_min <= pieza.peso <= selected_range.rango_max)
                if filtered_count == 0:
                    errors.append("rango sin piezas en la partida")
                else:
                    self.rango_info_value.set(
                        f"{filtered_count} piezas en {selected_range.range_label}. Dias sugeridos: {selected_range.dias_sal}."
                    )
            except Exception:
                pass
        try:
            units = int(self.unidades_box.get().strip())
            if units <= 0:
                errors.append("unidades/box debe ser mayor que cero")
        except Exception:
            units = 0
            errors.append("unidades/box invalido")
        try:
            labels = int(self.etiquetas_box.get().strip())
            if labels <= 0:
                errors.append("etiquetas/box debe ser mayor que cero")
        except Exception:
            labels = 0
            errors.append("etiquetas/box invalido")

        if entry_date is not None and selected_range is not None and "dias en sal invalido" not in errors:
            try:
                exit_date = calculate_exit_date(entry_date, days)
                exit_text = exit_date.strftime("%d/%m/%Y")
                ok, reason = validate_workday(exit_date)
                status_ok = ok and not errors
                status_text = "Laborable" if ok else f"Revisar salida: {reason}"
                if not ok:
                    warnings.append(f"salida no laborable ({reason})")
            except Exception as exc:
                errors.append(str(exc))
        elif selected_range is None:
            status_text = "Pendiente rango"

        jamones = str(self.resultado.total_filtradas) if self.resultado is not None else "-"
        boxes = str(len(self.resultado.boxes)) if self.resultado is not None else "-"
        etiquetas = str(self.resultado.total_etiquetas) if self.resultado is not None else "-"
        return errors, warnings, [("Jamones", jamones), ("Boxes", boxes), ("Etiquetas", etiquetas), ("Salida", exit_text), ("Estado", status_text)], status_ok
    def _validate_partida_path(self, path: Path) -> tuple[list[str], list[str], str]:
        try:
            stat = path.stat()
            cache_key = (str(path.resolve()), stat.st_mtime, stat.st_size)
            cached = self.validation_cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception:
            cache_key = None
        errors: list[str] = []
        warnings: list[str] = []
        info = "Partida seleccionada, pendiente de validar."
        if path.suffix.lower() != ".txt":
            errors.append("la partida debe ser .txt")
        try:
            text = path.read_text(encoding="utf-8-sig")
        except Exception:
            return ["no se puede leer la partida"], warnings, info
        total_lines = sum(1 for line in text.splitlines() if line.strip())
        if total_lines == 0:
            return ["partida vacia"], warnings, "Partida vacia."
        lote_digits = "".join(ch for ch in path.stem if ch.isdigit())
        if len(lote_digits) < 6:
            warnings.append("lote con menos de 6 digitos")
        try:
            legend = load_article_legend(ARTICULOS_PATH)
            pieces = parse_partida_file(path, legend)
        except Exception as exc:
            return [str(exc).splitlines()[0]], warnings, info
        invalid_lines = max(total_lines - len(pieces), 0)
        if invalid_lines:
            errors.append(f"{invalid_lines} lineas de partida no validas")
        unknown_articles = sorted({pieza.articulo_codigo for pieza in pieces if pieza.articulo_nombre.startswith("ARTICULO ")})
        if unknown_articles:
            errors.append("articulo sin leyenda")
        article_labels = sorted({f"{pieza.articulo_clave} - {pieza.articulo_nombre}" for pieza in pieces})
        if len(article_labels) > 1:
            warnings.append("partida con varios articulos")
        reception_dates = sorted({pieza.fecha_recepcion for pieza in pieces})
        if len(reception_dates) > 1:
            warnings.append("partida con varias recepciones")
        weights = [pieza.peso for pieza in pieces]
        article_text = article_labels[0] if len(article_labels) == 1 else f"{len(article_labels)} articulos"
        info = (
            f"Lote {normalize_lote_from_filename(path.name)} | {len(pieces)} piezas validas de {total_lines} lineas | "
            f"{article_text} | Recepcion {reception_dates[0]:%d/%m/%Y} | "
            f"Peso real {format_decimal(min(weights))} - {format_decimal(max(weights))} kg"
        )
        result = (errors, warnings, info)
        if cache_key is not None:
            self.validation_cache.clear()
            self.validation_cache[cache_key] = result
        return result

    def _load_logo(self, path: Path, max_width: int, max_height: int) -> ImageTk.PhotoImage | None:
        if not path.exists():
            return None
        try:
            image = Image.open(path).convert("RGBA")
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            self.logo_images.append(photo)
            return photo
        except Exception:
            return None

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scroll = ModernScrollBar(self, command=self.canvas.yview)
        self.scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.container = ttk.Frame(self.canvas, padding=14, style="App.TFrame")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.container, anchor="nw")
        self.container.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.canvas.bind("<Button-4>", self._on_mousewheel, add="+")
        self.canvas.bind("<Button-5>", self._on_mousewheel, add="+")
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_mousewheel, add="+")
        self.container.columnconfigure(0, weight=1)
        self.header = tk.Frame(self.container, bg=SURFACE, padx=14, pady=12, highlightthickness=1, highlightbackground="#C8D3E3", highlightcolor="#C8D3E3", bd=0)
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self.header.columnconfigure(1, weight=1)

        title_box = ttk.Frame(self.header, style="Header.TFrame")
        title_box.grid(row=0, column=1, sticky="w", padx=(18, 18))
        ttk.Label(title_box, text="Etiquetado box salazon", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text="Genera etiquetas para identificar visualmente los boxes de jamones en sal.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))
        quick_actions = ttk.Frame(title_box, style="Header.TFrame")
        quick_actions.pack(anchor="w", pady=(8, 0))
        self.quick_generate_button = CanvasButton(quick_actions, text="Generar vista previa", command=self.generate_preview, variant="primary", width=166, height=36)
        self.quick_generate_button.pack(side="left")
        self.quick_print_button = CanvasButton(quick_actions, text="Imprimir", command=self.print_labels, variant="dark", width=96, height=36, enabled=False)
        self.quick_print_button.pack(side="left", padx=(8, 0))

        rodriguez_logo = self._load_logo(RODRIGUEZ_LOGO, 150, 58)
        if rodriguez_logo:
            tk.Label(self.header, image=rodriguez_logo, bg=SURFACE, borderwidth=0).grid(row=0, column=0, sticky="w")

        finura_logo = self._load_logo(FINURA_LOGO, 120, 48)
        if finura_logo:
            tk.Label(self.header, image=finura_logo, bg=SURFACE, borderwidth=0).grid(row=0, column=2, sticky="e")

        self.main = tk.Frame(self.container, bg=SURFACE, padx=18, pady=18, highlightthickness=1, highlightbackground="#C8D3E3", highlightcolor="#C8D3E3", bd=0)
        self.main.grid(row=1, column=0, sticky="nsew")
        self.main.columnconfigure(0, weight=1)
        self.main.columnconfigure(1, weight=1)
        self.main.bind("<Configure>", self._on_main_configure, add="+")
        tk.Frame(self.main, bg=ACCENT_RED, height=4).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        self.flow_bar = CanvasFlowBar(self.main, ("Partida", "Parametros", "Vista previa", "Imprimir"))
        self.flow_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self.summary_bar = CanvasSummaryBar(self.main)
        self.summary_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        self._build_input_panel()
        self._build_preview_panel()
        self._build_boxes_table()
        self._build_status_panel()

    def _build_input_panel(self) -> None:
        self.form_panel = CanvasPanel(self.main, "Datos de la partida", min_height=438)
        self.form_panel.grid(row=3, column=0, sticky="nsew", padx=(0, 8), pady=(0, 12))
        form = self.form_panel.body
        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=0)
        form.columnconfigure(3, weight=0)

        ttk.Label(form, text="Partida .txt", style="Surface.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.selected_file).grid(row=0, column=1, sticky="ew", padx=(10, 8))
        self.select_button = CanvasButton(form, text="Seleccionar", command=self.select_file, variant="primary", width=122, height=40)
        self.select_button.grid(row=0, column=2, sticky="e")
        ToolTip(self.select_button, "Ctrl+O - Selecciona el fichero de partida.")
        self.clear_button = CanvasButton(form, text="Limpiar", command=self.clear_file, variant="ghost", width=88, height=40)
        self.clear_button.grid(row=0, column=3, sticky="e", padx=(6, 0))
        ToolTip(self.clear_button, "Quita la partida seleccionada.")

        info = tk.Label(form, textvariable=self.partida_info_value, bg="#F3F7FF", fg=TEXT, anchor="w", justify="left", padx=12, pady=10, font=("Segoe UI", 10), highlightthickness=1, highlightbackground="#C8D6EA")
        info.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 2))

        self._add_date_row(form, 2)
        self._add_range_row(form, 3)
        self._add_stepper_row(form, 5, "Dias en sal", self.dias_sal, "dias", mode="int", step=1, minimum=0)
        self._add_stepper_row(form, 6, "Unidades/box", self.unidades_box, "CSV", mode="int", step=1, minimum=1)
        self._add_stepper_row(form, 7, "Etiquetas/box", self.etiquetas_box, "copias", mode="int", step=1, minimum=1)

        self.printer_panel = CanvasPanel(self.main, "Impresora Windows", min_height=124)
        self.printer_panel.grid(row=4, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
        printer_frame = self.printer_panel.body
        printer_frame.columnconfigure(0, weight=1)
        self.printer_combo = ttk.Combobox(printer_frame, textvariable=self.printer, state="readonly")
        self.printer_combo.grid(row=0, column=0, sticky="ew")
        refresh = CanvasButton(printer_frame, text="Actualizar", command=self._load_printers, variant="secondary", width=118, height=38)
        refresh.grid(row=0, column=1, sticky="e", padx=(8, 0))
        ttk.Label(printer_frame, text="Configura en el driver Citizen el mismo tamano elegido o personalizado en la plantilla de etiqueta.", style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.actions_frame = ttk.Frame(self.main, style="Surface.TFrame")
        self.actions_frame.grid(row=5, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
        self.generate_button = CanvasButton(self.actions_frame, text="Generar vista previa", command=self.generate_preview, variant="primary", width=176, height=42)
        self.generate_button.pack(side="left")
        self.save_button = CanvasButton(self.actions_frame, text="Guardar PNG", command=self.save_preview, variant="secondary", width=126, height=42, enabled=False)
        self.save_button.pack(side="left", padx=(8, 0))
        self.details_button = CanvasButton(self.actions_frame, text="Ver detalles", command=self.show_details, variant="secondary", width=126, height=42)
        self.details_button.pack(side="left", padx=(8, 0))
        self.print_button = CanvasButton(self.actions_frame, text="Imprimir etiquetas", command=self.print_labels, variant="dark", width=166, height=42, enabled=False)
        self.print_button.pack(side="right")

    def _add_date_row(self, parent: tk.Misc, row: int) -> None:
        ttk.Label(parent, text="Fecha entrada", style="Surface.TLabel").grid(row=row, column=0, sticky="w", pady=(8, 0))
        frame = ttk.Frame(parent, style="Surface.TFrame")
        frame.grid(row=row, column=1, sticky="ew", padx=(10, 8), pady=(8, 0))
        frame.columnconfigure(0, weight=1)
        ttk.Entry(frame, textvariable=self.fecha_entrada).grid(row=0, column=0, sticky="ew")
        cal_button = CanvasButton(frame, text="Calendario", command=self.show_calendar, variant="secondary", width=126, height=36)
        cal_button.grid(row=0, column=1, padx=(8, 0))
        ttk.Label(parent, text="dd/mm/aaaa", style="Muted.TLabel").grid(row=row, column=2, sticky="w", pady=(8, 0))

    def _add_range_row(self, parent: tk.Misc, row: int) -> None:
        ttk.Label(parent, text="Rango peso", style="Surface.TLabel").grid(row=row, column=0, sticky="w", pady=(10, 0))
        range_frame = tk.Frame(parent, bg="#F8FBFF", highlightthickness=1, highlightbackground="#C8D6EA", padx=8, pady=8)
        range_frame.grid(row=row, column=1, columnspan=3, sticky="ew", padx=(10, 0), pady=(10, 0))
        range_frame.columnconfigure(0, weight=1)
        self.range_combo = ttk.Combobox(range_frame, textvariable=self.rango_peso, state="disabled")
        self.range_combo.grid(row=0, column=0, sticky="ew")
        self.range_combo.bind("<<ComboboxSelected>>", self._on_range_selected)
        ToolTip(self.range_combo, "Se carga desde config/config_salazon.csv segun el articulo de la partida.")
        tk.Label(range_frame, textvariable=self.rango_info_value, bg="#F8FBFF", fg=MUTED, anchor="w", justify="left", wraplength=760, font=("Segoe UI", 9)).grid(row=1, column=0, sticky="ew", pady=(6, 0))
    def _add_plain_row(self, parent: tk.Misc, row: int, label: str, variable: tk.StringVar, hint: str) -> None:
        ttk.Label(parent, text=label, style="Surface.TLabel").grid(row=row, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=(10, 8), pady=(8, 0))
        ttk.Label(parent, text=hint, style="Muted.TLabel").grid(row=row, column=2, sticky="w", pady=(8, 0))

    def _add_stepper_row(self, parent: tk.Misc, row: int, label: str, variable: tk.StringVar, hint: str, mode: str, step: float, minimum: float | None) -> None:
        ttk.Label(parent, text=label, style="Surface.TLabel").grid(row=row, column=0, sticky="w", pady=(8, 0))
        frame = ttk.Frame(parent, style="Surface.TFrame")
        frame.grid(row=row, column=1, sticky="ew", padx=(10, 8), pady=(8, 0))
        frame.columnconfigure(1, weight=1)
        minus = CanvasButton(frame, text="-", width=36, height=34, radius=8, variant="ghost", command=lambda: self._adjust_value(variable, mode, -step, minimum), font=("Segoe UI", 13, "bold"))
        minus.grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=variable).grid(row=0, column=1, sticky="ew", padx=6)
        plus = CanvasButton(frame, text="+", width=36, height=34, radius=8, variant="ghost", command=lambda: self._adjust_value(variable, mode, step, minimum), font=("Segoe UI", 13, "bold"))
        plus.grid(row=0, column=2, sticky="e")
        ttk.Label(parent, text=hint, style="Muted.TLabel").grid(row=row, column=2, sticky="w", pady=(8, 0))

    def _adjust_value(self, variable: tk.StringVar, mode: str, delta: float, minimum: float | None) -> None:
        raw = variable.get().strip().replace(",", ".")
        try:
            current = float(raw) if raw else 0.0
        except ValueError:
            current = 0.0
        value = current + delta
        if minimum is not None:
            value = max(value, minimum)
        if mode == "int":
            variable.set(str(int(round(value))))
            return
        text = f"{value:.1f}".rstrip("0").rstrip(".").replace(".", ",")
        variable.set(text)

    def show_calendar(self) -> None:
        if self.calendar_window is not None and self.calendar_window.winfo_exists():
            self.calendar_window.lift()
            return
        try:
            selected = parse_date(self.fecha_entrada.get())
            self.calendar_month = datetime(selected.year, selected.month, 1)
        except Exception:
            today = datetime.today()
            self.calendar_month = datetime(today.year, today.month, 1)
        self.calendar_window = tk.Toplevel(self)
        self.calendar_window.title("Seleccionar fecha de entrada")
        self.calendar_window.geometry("360x340")
        self.calendar_window.configure(bg=BG)
        self.calendar_window.transient(self)
        self.calendar_window.protocol("WM_DELETE_WINDOW", self._close_calendar)
        set_window_icon(self.calendar_window)
        self._draw_calendar()
        center_window(self.calendar_window)

    def _close_calendar(self) -> None:
        if self.calendar_window is not None and self.calendar_window.winfo_exists():
            self.calendar_window.destroy()
        self.calendar_window = None

    def _draw_calendar(self) -> None:
        if self.calendar_window is None or self.calendar_month is None:
            return
        for child in self.calendar_window.winfo_children():
            child.destroy()
        frame = ttk.Frame(self.calendar_window, padding=14, style="App.TFrame")
        frame.pack(fill="both", expand=True)
        header = ttk.Frame(frame, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 10))
        header.columnconfigure(1, weight=1)
        CanvasButton(header, text="<", width=38, height=34, variant="ghost", command=lambda: self._change_calendar_month(-1), font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        title = f"{month_names[self.calendar_month.month - 1]} {self.calendar_month.year}"
        ttk.Label(header, text=title, background=BG, foreground=TEXT, font=("Segoe UI", 13, "bold")).grid(row=0, column=1)
        CanvasButton(header, text=">", width=38, height=34, variant="ghost", command=lambda: self._change_calendar_month(1), font=("Segoe UI", 12, "bold")).grid(row=0, column=2, sticky="e")
        for col, name in enumerate(("L", "M", "X", "J", "V", "S", "D")):
            ttk.Label(frame, text=name, background=BG, foreground=MUTED, font=("Segoe UI", 10, "bold"), anchor="center").grid(row=1, column=col, sticky="ew", padx=2, pady=2)
            frame.columnconfigure(col, weight=1)
        month = calendar.monthcalendar(self.calendar_month.year, self.calendar_month.month)
        holidays = holidays_for_year(self.calendar_month.year)
        for r, week in enumerate(month, start=2):
            for c, day in enumerate(week):
                if day == 0:
                    ttk.Label(frame, text="", background=BG).grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
                    continue
                text = str(day)
                command = lambda d=day: self._select_calendar_day(d)
                variant = "ghost" if c >= 5 else "secondary"
                tooltip = "Seleccionar fecha de entrada."
                try:
                    current_day = datetime(self.calendar_month.year, self.calendar_month.month, day).date()
                    selected_entry = parse_date(self.fecha_entrada.get())
                    selected_exit = calculate_exit_date(selected_entry, int(self.dias_sal.get().strip()))
                    if current_day in holidays:
                        variant = "danger"
                        tooltip = f"Festivo: {holidays[current_day]}"
                    if current_day == selected_exit:
                        variant = "dark"
                        ok, reason = validate_workday(current_day)
                        tooltip = "Salida calculada." if ok else f"Salida no laborable: {reason}"
                    if current_day == selected_entry:
                        variant = "primary"
                        tooltip = "Fecha de entrada seleccionada."
                except Exception:
                    pass
                day_button = CanvasButton(frame, text=text, command=command, variant=variant, width=42, height=34, font=("Segoe UI", 10, "bold"))
                day_button.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
                ToolTip(day_button, tooltip)
        ttk.Label(frame, text="Azul: entrada | Oscuro: salida calculada | Rojo: festivo | Claro: fin de semana", background=BG, foreground=MUTED, font=("Segoe UI", 9)).grid(row=8, column=0, columnspan=7, sticky="w", pady=(8, 0))

    def _change_calendar_month(self, offset: int) -> None:
        if self.calendar_month is None:
            return
        year = self.calendar_month.year
        month = self.calendar_month.month + offset
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        self.calendar_month = datetime(year, month, 1)
        self._draw_calendar()

    def _select_calendar_day(self, day: int) -> None:
        if self.calendar_month is None:
            return
        selected = datetime(self.calendar_month.year, self.calendar_month.month, day)
        try:
            days = int(self.dias_sal.get().strip())
            exit_date = calculate_exit_date(selected.date(), days)
            ok, reason = validate_workday(exit_date)
            if not ok:
                messagebox.showwarning(
                    "Salida no laborable",
                    f"Con esa entrada, la salida seria {exit_date:%d/%m/%Y} y no es laborable: {reason}.",
                    parent=self.calendar_window,
                )
                return
        except Exception:
            pass
        self.fecha_entrada.set(selected.strftime("%d/%m/%Y"))
        self._close_calendar()

    def _build_preview_panel(self) -> None:
        self.preview_panel = CanvasPanel(self.main, "Vista previa etiqueta", min_height=468, auto_height=False)
        self.preview_panel.grid(row=3, column=1, rowspan=3, sticky="nsew", padx=(8, 0), pady=(0, 12))
        preview = self.preview_panel.body
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(0, weight=1)
        self.preview_label = tk.Label(preview, text="Genera la vista previa para ver la primera etiqueta.", bg="white", fg=MUTED, highlightthickness=1, highlightbackground="#D7E0EE", bd=0, padx=20, pady=20)
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        nav = ttk.Frame(preview, style="Surface.TFrame")
        nav.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        nav.columnconfigure(1, weight=1)
        self.prev_button = CanvasButton(nav, text="<", command=self.preview_previous, variant="ghost", width=42, height=34, font=("Segoe UI", 12, "bold"), enabled=False)
        self.prev_button.grid(row=0, column=0, sticky="w")
        ttk.Label(nav, textvariable=self.preview_box_value, style="Result.TLabel", anchor="center").grid(row=0, column=1, sticky="ew")
        self.zoom_button = CanvasButton(nav, text="Ver grande", command=self.show_large_label, variant="secondary", width=112, height=34, font=("Segoe UI", 10, "bold"), enabled=False)
        self.zoom_button.grid(row=0, column=2, sticky="e", padx=(8, 6))
        self.next_button = CanvasButton(nav, text=">", command=self.preview_next, variant="ghost", width=42, height=34, font=("Segoe UI", 12, "bold"), enabled=False)
        self.next_button.grid(row=0, column=3, sticky="e")
        ttk.Label(preview, textvariable=self.summary, style="Result.TLabel", wraplength=480).grid(row=2, column=0, sticky="ew", pady=(10, 0))

    def _build_boxes_table(self) -> None:
        self.table_panel = CanvasPanel(self.main, "Boxes generados", min_height=226)
        self.table_panel.grid(row=6, column=0, columnspan=2, sticky="nsew")
        table_frame = self.table_panel.body
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("box", "unidades", "rango", "rango_real", "etiquetas")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=5)
        headings = {
            "box": "Box",
            "unidades": "Unidades",
            "rango": "Rango elegido",
            "rango_real": "Rango real box",
            "etiquetas": "Etiquetas",
        }
        widths = {"box": 80, "unidades": 100, "rango": 180, "rango_real": 180, "etiquetas": 100}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ModernScrollBar(table_frame, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_box_selected)

    def _build_status_panel(self) -> None:
        self.status_panel = CanvasPanel(self.main, "Validacion y estado", min_height=132)
        self.status_panel.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        status_frame = self.status_panel.body
        status_frame.columnconfigure(0, weight=1)
        ttk.Label(status_frame, textvariable=self.status, style="Surface.TLabel", wraplength=980).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(status_frame, textvariable=self.validation_value, style="Muted.TLabel", wraplength=980).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 6))
        ttk.Label(status_frame, textvariable=self.validation_partida, style="Surface.TLabel").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Label(status_frame, textvariable=self.validation_fechas, style="Surface.TLabel").grid(row=2, column=1, sticky="w", pady=2, padx=(14, 0))
        ttk.Label(status_frame, textvariable=self.validation_rango, style="Surface.TLabel").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Label(status_frame, textvariable=self.validation_impresora, style="Surface.TLabel").grid(row=3, column=1, sticky="w", pady=2, padx=(14, 0))

    def _on_main_configure(self, event) -> None:
        if event.widget is self.main:
            self._apply_responsive_layout(event.width)

    def _apply_responsive_layout(self, width: int) -> None:
        if not all(hasattr(self, name) for name in ("form_panel", "printer_panel", "actions_frame", "preview_panel", "table_panel", "status_panel")):
            return
        if width < 1040:
            if self.layout_mode == "stacked":
                return
            self.layout_mode = "stacked"
            self.main.columnconfigure(0, weight=1)
            self.main.columnconfigure(1, weight=0)
            self.form_panel.grid_configure(row=3, column=0, columnspan=2, sticky="nsew", padx=0, pady=(0, 12))
            self.printer_panel.grid_configure(row=4, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 12))
            self.actions_frame.grid_configure(row=5, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 12))
            self.preview_panel.grid_configure(row=6, column=0, columnspan=2, rowspan=1, sticky="nsew", padx=0, pady=(0, 12))
            self.table_panel.grid_configure(row=7, column=0, columnspan=2, sticky="nsew")
            self.status_panel.grid_configure(row=8, column=0, columnspan=2, sticky="ew", pady=(12, 0))
            return
        if self.layout_mode == "wide":
            return
        self.layout_mode = "wide"
        self.main.columnconfigure(0, weight=1)
        self.main.columnconfigure(1, weight=1)
        self.form_panel.grid_configure(row=3, column=0, columnspan=1, sticky="nsew", padx=(0, 8), pady=(0, 12))
        self.printer_panel.grid_configure(row=4, column=0, columnspan=1, sticky="ew", padx=(0, 8), pady=(0, 12))
        self.actions_frame.grid_configure(row=5, column=0, columnspan=1, sticky="ew", padx=(0, 8), pady=(0, 12))
        self.preview_panel.grid_configure(row=3, column=1, columnspan=1, rowspan=3, sticky="nsew", padx=(8, 0), pady=(0, 12))
        self.table_panel.grid_configure(row=6, column=0, columnspan=2, sticky="nsew")
        self.status_panel.grid_configure(row=7, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def _on_content_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event) -> str | None:
        try:
            if event.widget.winfo_toplevel() is not self:
                return None
        except Exception:
            return None
        bbox = self.canvas.bbox("all")
        if not bbox:
            return None
        content_height = bbox[3] - bbox[1]
        if content_height <= self.canvas.winfo_height():
            return None
        if getattr(event, "num", None) == 4:
            delta = -3
        elif getattr(event, "num", None) == 5:
            delta = 3
        else:
            raw_delta = getattr(event, "delta", 0)
            if raw_delta == 0:
                return None
            delta = -1 * int(raw_delta / 120)
            if delta == 0:
                delta = -1 if raw_delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")
        return "break"

    def _load_printers(self) -> None:
        printers = list_windows_printers()
        self.printer_combo.configure(values=printers)
        default = default_windows_printer()
        citizen = next((name for name in printers if "citizen" in name.lower() and ("703" in name or "cl-s" in name.lower())), "")
        selected = citizen or default or (printers[0] if printers else "")
        self.printer.set(selected)
        if printers:
            self._append_detail(f"Impresoras detectadas: {', '.join(printers)}")
        else:
            self._append_detail("No se detectan impresoras Windows o pywin32 no esta disponible.")
        self._refresh_validation_state()

    def select_file(self) -> None:
        initial_dir = self.last_partida_dir if self.last_partida_dir and Path(self.last_partida_dir).exists() else None
        dialog_options = {
            "title": "Seleccionar partida .txt",
            "filetypes": [("Partidas TXT", "*.txt"), ("Todos los archivos", "*.*")],
        }
        if initial_dir:
            dialog_options["initialdir"] = initial_dir
        selected = filedialog.askopenfilename(**dialog_options)
        if selected:
            self.last_partida_dir = str(Path(selected).resolve().parent)
            self.selected_file.set(selected)
            self.status.set("Partida seleccionada. Genera la vista previa para validar datos.")
            self._save_user_state()
            self._refresh_range_options()
            self._refresh_validation_state()

    def clear_file(self) -> None:
        self.resultado = None
        self.validation_cache.clear()
        self.selected_file.set("")
        self.fecha_entrada.set("")
        self.rango_peso.set("")
        self.dias_sal.set("")
        self.unidades_box.set("")
        self.etiquetas_box.set("")
        self.rango_info_value.set("Carga una partida para ver los rangos configurados.")
        self.range_options = {}
        self._set_range_combo_values([], False)
        self.preview_box_index = 0
        self.preview_photo = None
        self.preview_box_value.set("Vista previa: sin etiqueta")
        self.partida_info_value.set("Sin partida cargada")
        self.summary.set("Sin datos cargados")
        self.preview_label.configure(image="", text="Genera la vista previa para ver la primera etiqueta.")
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.status.set("Datos limpiados. Selecciona una partida .txt para comenzar.")
        self._refresh_validation_state()

    def _non_workday_exit_warning(self, entry_date, days: int) -> str:
        exit_date = calculate_exit_date(entry_date, days)
        ok, reason = validate_workday(exit_date)
        if ok:
            return ""
        return f"La fecha de salida calculada es {exit_date:%d/%m/%Y} y cae en dia no laborable: {reason}."
    def _read_inputs(self) -> tuple[Path, object, int, float, float, int, int, str]:
        path = Path(self.selected_file.get().strip())
        if not path.exists():
            raise ValueError("Selecciona un fichero de partida valido.")
        file_errors, file_warnings, _partida_info = self._validate_partida_path(path)
        if file_errors:
            raise ValueError("Revisa la partida:\n" + "\n".join(file_errors))
        for warning in file_warnings:
            self._append_detail(f"AVISO PARTIDA: {warning}")
        entry_date = parse_date(self.fecha_entrada.get())
        days = int(self.dias_sal.get().strip())
        selected_range = self._selected_salazon_range()
        if selected_range is None:
            raise ValueError("Selecciona un rango de peso configurado para el articulo.")
        min_weight = selected_range.rango_min
        max_weight = selected_range.rango_max
        units = int(self.unidades_box.get().strip())
        labels = int(self.etiquetas_box.get().strip())
        return path, entry_date, days, min_weight, max_weight, units, labels, selected_range.articulo_nombre

    def generate_preview(self) -> None:
        try:
            path, entry_date, days, min_weight, max_weight, units, labels, article_name = self._read_inputs()
            non_workday_warning = self._non_workday_exit_warning(entry_date, days)
            if non_workday_warning and not messagebox.askyesno("Salida no laborable", non_workday_warning + "\n\nPuedes seguir generando la vista previa para revisar la etiqueta. ¿Continuar?", parent=self):
                self.status.set("Salida no laborable pendiente de revisar. Ajusta fecha o dias en sal si no quieres continuar.")
                return
            legend = load_article_legend(ARTICULOS_PATH)
            resultado = build_boxes(path, entry_date, days, min_weight, max_weight, units, labels, legend=legend, article_name_override=article_name)
        except Exception as exc:
            self.resultado = None
            self.status.set("Revisa los datos antes de continuar.")
            self._append_detail("ERROR GENERANDO VISTA PREVIA:\n" + traceback.format_exc())
            messagebox.showerror("No se pudo generar", str(exc))
            return

        self.resultado = resultado
        self._save_user_state()
        self.preview_box_index = 0
        self._fill_table(resultado.boxes)
        self._show_current_preview()
        self.summary.set(
            f"Lote {resultado.lote} | {resultado.total_filtradas} jamones | "
            f"{len(resultado.boxes)} boxes | {resultado.total_etiquetas} etiquetas | "
            f"salida {resultado.fecha_salida:%d/%m/%Y}"
        )
        self.status.set("Vista previa generada correctamente. Revisa los boxes antes de imprimir.")
        self._refresh_validation_state()
        self._append_detail("RESUMEN GENERACION")
        self._append_detail(f"Partida: {path}")
        self._append_detail(f"Leyenda articulos: {ARTICULOS_PATH}")
        self._append_detail(f"Configuracion salazon: {SALAZON_CONFIG_PATH}")
        self._append_detail(f"Lineas leidas: {resultado.total_lineas}")
        self._append_detail(f"Piezas validas: {resultado.total_validas}")
        self._append_detail(f"Piezas en rango: {resultado.total_filtradas}")
        self._append_detail(f"Articulo: {resultado.articulo_nombre}")
        self._append_detail(f"Boxes: {len(resultado.boxes)}")
        self._append_detail(f"Etiquetas: {resultado.total_etiquetas}")
        for aviso in resultado.avisos:
            self._append_detail(f"AVISO: {aviso}")

    def _fill_table(self, boxes: tuple[BoxEtiqueta, ...]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree.tag_configure("resto", background="#FFF4E5")
        try:
            target_units = int(self.unidades_box.get().strip())
        except Exception:
            target_units = 0
        for index, box in enumerate(boxes):
            tags = ("resto",) if index == len(boxes) - 1 and target_units and box.unidades < target_units else ()
            self.tree.insert(
                "",
                "end",
                iid=str(box.box_numero),
                values=(
                    box.box_numero,
                    box.unidades,
                    f"{format_decimal(box.rango_min)} - {format_decimal(box.rango_max)} kg",
                    f"{format_decimal(box.rango_real_min)} - {format_decimal(box.rango_real_max)} kg",
                    box.etiquetas,
                ),
                tags=tags,
            )
        if boxes:
            self.tree.selection_set(str(boxes[0].box_numero))

    def _show_label(self, box: BoxEtiqueta) -> None:
        image = render_label(box, dpi=110, template=self.template)
        image.thumbnail((330, 390), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview_label.configure(image=self.preview_photo, text="", bg="white")

    def _on_box_selected(self, _event=None) -> None:
        if self.resultado is None:
            return
        selection = self.tree.selection()
        if not selection:
            return
        number = int(selection[0])
        for index, box in enumerate(self.resultado.boxes):
            if box.box_numero == number:
                self.preview_box_index = index
                self._show_label(box)
                self.preview_box_value.set(f"Vista previa: Box {index + 1} de {len(self.resultado.boxes)}")
                break

    def _show_current_preview(self) -> None:
        if self.resultado is None or not self.resultado.boxes:
            self.preview_box_value.set("Vista previa: sin etiqueta")
            return
        self.preview_box_index = max(0, min(self.preview_box_index, len(self.resultado.boxes) - 1))
        box = self.resultado.boxes[self.preview_box_index]
        self._show_label(box)
        self.preview_box_value.set(f"Vista previa: Box {self.preview_box_index + 1} de {len(self.resultado.boxes)}")
        try:
            self.tree.selection_set(str(box.box_numero))
            self.tree.see(str(box.box_numero))
        except Exception:
            pass

    def preview_previous(self) -> None:
        if self.resultado is None or not self.resultado.boxes:
            return
        self.preview_box_index = (self.preview_box_index - 1) % len(self.resultado.boxes)
        self._show_current_preview()

    def preview_next(self) -> None:
        if self.resultado is None or not self.resultado.boxes:
            return
        self.preview_box_index = (self.preview_box_index + 1) % len(self.resultado.boxes)
        self._show_current_preview()

    def show_large_label(self) -> None:
        if self.resultado is None or not self.resultado.boxes:
            messagebox.showinfo("Sin etiqueta", "Genera primero la vista previa.")
            return
        box = self.resultado.boxes[self.preview_box_index]
        window = tk.Toplevel(self)
        window.title(f"Etiqueta box {box.box_numero}")
        window.geometry("620x840")
        window.configure(bg=BG)
        set_window_icon(window)
        frame = ttk.Frame(window, padding=14, style="App.TFrame")
        frame.pack(fill="both", expand=True)
        image = render_label(box, dpi=150, template=self.template)
        image.thumbnail((560, 760), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        window._preview_photo = photo
        label = tk.Label(frame, image=photo, bg="white", highlightthickness=1, highlightbackground="#D7E0EE")
        label.pack(fill="both", expand=True)
        CanvasButton(frame, text="Cerrar", command=window.destroy, variant="secondary", width=94, height=38).pack(anchor="e", pady=(10, 0))
        center_window(window)

    def save_preview(self) -> None:
        if self.resultado is None:
            messagebox.showinfo("Sin etiquetas", "Genera primero la vista previa.")
            return
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        selected = filedialog.asksaveasfilename(
            title="Guardar etiquetas como PNG",
            defaultextension=".png",
            initialdir=str(EXPORTS_DIR),
            initialfile=f"etiquetas_{self.resultado.lote}.png",
            filetypes=[("Imagen PNG", "*.png")],
        )
        if not selected:
            return
        try:
            save_label_contact_sheet(expand_labels(self.resultado.boxes), Path(selected), dpi=120, template=self.template)
            self.status.set(f"PNG guardado: {selected}")
        except Exception as exc:
            messagebox.showerror("No se pudo guardar", str(exc))

    def print_labels(self) -> None:
        if self.resultado is None:
            messagebox.showinfo("Sin etiquetas", "Genera primero la vista previa.")
            return
        total = self.resultado.total_etiquetas
        printer = self.printer.get().strip()
        if not printer:
            messagebox.showerror("Sin impresora", "Selecciona la Citizen CL-S703 instalada en Windows.")
            return
        ok, reason = validate_workday(self.resultado.fecha_salida)
        if not ok and not messagebox.askyesno("Salida no laborable", f"La fecha de salida {self.resultado.fecha_salida:%d/%m/%Y} cae en dia no laborable: {reason}.\n\n¿Quieres imprimir igualmente?", parent=self):
            self.status.set("Impresion cancelada: salida no laborable pendiente de revisar.")
            return
        if not messagebox.askyesno("Confirmar impresion", f"Se enviaran {total} etiquetas a:\n\n{printer}\n\nContinuar?"):
            return
        try:
            printed = print_labels_windows(self.resultado.boxes, printer, template=self.template)
        except Exception as exc:
            self._append_detail("ERROR IMPRIMIENDO:\n" + traceback.format_exc())
            messagebox.showerror("No se pudo imprimir", str(exc))
            return
        self.status.set(f"Etiquetas enviadas a impresion: {printed}")
        self._append_detail(f"Impresion enviada a {printer}: {printed} etiquetas")

    def show_details(self) -> None:
        if self.details_window is not None and self.details_window.winfo_exists():
            self.details_window.lift()
            return
        self.details_window = tk.Toplevel(self)
        self.details_window.title("Detalles tecnicos")
        self.details_window.geometry("780x460")
        self.details_window.configure(bg=BG)
        set_window_icon(self.details_window)
        frame = ttk.Frame(self.details_window, padding=14, style="App.TFrame")
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Auditoria y detalles tecnicos", background=BG, foreground=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill="both", expand=True)
        self.details_text = tk.Text(text_frame, height=16, wrap="word", state="normal", bg="white", fg=TEXT, insertbackground=PRIMARY_BLUE, relief="flat", padx=10, pady=10, font=("Consolas", 9))
        self.details_text.pack(side="left", fill="both", expand=True)
        scroll = ModernScrollBar(text_frame, command=self.details_text.yview)
        scroll.pack(side="right", fill="y")
        self.details_text.configure(yscrollcommand=scroll.set)
        for line in self.detail_lines:
            self.details_text.insert(tk.END, line + "\n")
        self.details_text.configure(state="disabled")
        CanvasButton(frame, text="Cerrar", command=self.details_window.destroy, variant="secondary", width=94, height=38).pack(anchor="e", pady=(10, 0))

    def _append_detail(self, text: str) -> None:
        self.detail_lines.append(text)
        if self.details_text is not None and self.details_text.winfo_exists():
            self.details_text.configure(state="normal")
            self.details_text.insert(tk.END, text + "\n")
            self.details_text.see(tk.END)
            self.details_text.configure(state="disabled")


def main() -> None:
    print("Modulo de editor compartido. Ejecuta app_etiquetado_pesos.py.")


if __name__ == "__main__":
    main()

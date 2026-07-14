from __future__ import annotations

from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
ASSETS_DIR = APP_DIR / "assets" if (APP_DIR / "assets").exists() else RESOURCE_DIR / "assets"
RODRIGUEZ_LOGO = ASSETS_DIR / "RODRIGUEZ.png"
FINURA_LOGO = ASSETS_DIR / "FINURA.png"
APP_ICON = ASSETS_DIR / "ICONO_SUITE_RRHH.ico"

PRIMARY_BLUE = "#003B8E"
ACCENT_RED = "#E31B1B"
GOLD = "#8F8155"
BG = "#F6F8FC"
SURFACE = "#FFFFFF"
TEXT = "#172033"
MUTED = "#5D667A"
BORDER = "#DCE3F0"
SUCCESS = "#167A3A"
WARNING = "#9B5A00"

FONT_FAMILY = "Segoe UI"


class ToolTip:
    def __init__(self, widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<FocusIn>", self._show, add="+")
        widget.bind("<FocusOut>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        if self.window or not self.text:
            return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.window,
            text=self.text,
            bg=TEXT,
            fg="white",
            padx=8,
            pady=5,
            font=(FONT_FAMILY, 9),
            justify="left",
        )
        label.pack()

    def _hide(self, _event=None) -> None:
        if self.window:
            self.window.destroy()
            self.window = None


def configure_style(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("App.TFrame", background=BG)
    style.configure("Surface.TFrame", background=SURFACE)
    style.configure("Header.TFrame", background=SURFACE)
    style.configure("Title.TLabel", background=SURFACE, foreground=TEXT, font=(FONT_FAMILY, 22, "bold"))
    style.configure("Subtitle.TLabel", background=SURFACE, foreground=MUTED, font=(FONT_FAMILY, 11))
    style.configure("Section.TLabelframe", background=SURFACE, bordercolor=BORDER, relief="solid")
    style.configure("Section.TLabelframe.Label", background=SURFACE, foreground=PRIMARY_BLUE, font=(FONT_FAMILY, 11, "bold"))
    style.configure("Surface.TLabel", background=SURFACE, foreground=TEXT, font=(FONT_FAMILY, 11))
    style.configure("Muted.TLabel", background=SURFACE, foreground=MUTED, font=(FONT_FAMILY, 10))
    style.configure("Result.TLabel", background=SURFACE, foreground=PRIMARY_BLUE, font=(FONT_FAMILY, 11, "bold"))
    style.configure("Success.TLabel", background=SURFACE, foreground=SUCCESS, font=(FONT_FAMILY, 11, "bold"))
    style.configure("Warning.TLabel", background=SURFACE, foreground=WARNING, font=(FONT_FAMILY, 11, "bold"))

    style.configure("Primary.TButton", font=(FONT_FAMILY, 11, "bold"), padding=(16, 9), foreground="white", background=PRIMARY_BLUE, borderwidth=0)
    style.map("Primary.TButton", background=[("active", "#0050B8"), ("pressed", "#002E70"), ("disabled", "#9EACC2")])
    style.configure("Blue.TButton", font=(FONT_FAMILY, 11, "bold"), padding=(14, 8), foreground="white", background=PRIMARY_BLUE, borderwidth=0)
    style.map("Blue.TButton", background=[("active", "#0050B8"), ("pressed", "#002E70"), ("disabled", "#9EACC2")])
    style.configure("Secondary.TButton", font=(FONT_FAMILY, 11), padding=(14, 8), foreground=PRIMARY_BLUE, background="#EEF4FF", borderwidth=1)
    style.map("Secondary.TButton", background=[("active", "#DCEBFF"), ("disabled", "#F3F5F9")])
    style.configure("Danger.TButton", font=(FONT_FAMILY, 11), padding=(14, 8), foreground="white", background=ACCENT_RED, borderwidth=0)
    style.map("Danger.TButton", background=[("active", "#C91616"), ("disabled", "#D9A0A0")])

    style.configure("TEntry", fieldbackground="white", bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, padding=6)
    style.configure("TCombobox", fieldbackground="white", bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, padding=5)
    style.configure("Treeview", font=(FONT_FAMILY, 10), rowheight=30, background="white", fieldbackground="white", foreground=TEXT)
    style.configure("Treeview.Heading", font=(FONT_FAMILY, 10, "bold"), background=PRIMARY_BLUE, foreground="white")
    style.map("Treeview.Heading", background=[("active", "#0050B8")])
    style.configure("Horizontal.TProgressbar", background=PRIMARY_BLUE, troughcolor="#E8EEF8", bordercolor="#E8EEF8", lightcolor=PRIMARY_BLUE, darkcolor=PRIMARY_BLUE)
    return style


def set_window_icon(window: tk.Toplevel | tk.Tk) -> None:
    try:
        if APP_ICON.exists():
            window.iconbitmap(str(APP_ICON))
        photos = []
        for size in (256, 128, 64, 48, 32, 24, 16):
            path = ASSETS_DIR / f"ICONO_SUITE_RRHH_{size}.png"
            if path.exists():
                photos.append(tk.PhotoImage(file=str(path)))
        if photos:
            window._icon_photos = photos
            window.iconphoto(True, *photos)
    except Exception:
        pass


def center_window(window: tk.Toplevel | tk.Tk) -> None:
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = max((window.winfo_screenwidth() - width) // 2, 0)
    y = max((window.winfo_screenheight() - height) // 2, 0)
    window.geometry(f"{width}x{height}+{x}+{y}")

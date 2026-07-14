from __future__ import annotations

import csv
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
CONFIG_DIR = APP_DIR / "config" if (APP_DIR / "config").exists() else RESOURCE_DIR / "config"
ARTICULOS_PATH = CONFIG_DIR / "articulos.txt"
SALAZON_CONFIG_PATH = CONFIG_DIR / "config_salazon.csv"
FESTIVOS_PATH = CONFIG_DIR / "festivos.json"
LABEL_TEMPLATE_PATH = CONFIG_DIR / "plantilla_etiqueta_pesos.json"

LABEL_WIDTH_MM = 111
LABEL_HEIGHT_MM = 162
DEFAULT_DPI = 300
PRINT_SAFE_MARGIN_MM = 3.0
SAFE_MARGIN_MIN_MM = 0.0
SAFE_MARGIN_MAX_MM = 12.0
BASE_LABEL_WIDTH = int(LABEL_WIDTH_MM / 25.4 * DEFAULT_DPI)
BASE_LABEL_HEIGHT = int(LABEL_HEIGHT_MM / 25.4 * DEFAULT_DPI)

CITIZEN_LABEL_SIZE_PRESETS = (
    ("110 x 162 mm - actual salazon", 110.0, 162.0),
    ("100 x 150 mm - envio grande", 100.0, 150.0),
    ("102 x 152 mm - 4 x 6 pulgadas", 102.0, 152.0),
    ("105 x 148 mm - A6", 105.0, 148.0),
    ("100 x 100 mm - cuadrada", 100.0, 100.0),
    ("80 x 50 mm - producto", 80.0, 50.0),
    ("70 x 50 mm - producto", 70.0, 50.0),
    ("60 x 40 mm - producto pequeno", 60.0, 40.0),
    ("50 x 30 mm - trazabilidad", 50.0, 30.0),
    ("40 x 30 mm - pequena", 40.0, 30.0),
)

WEEKDAY_ES = {
    0: "LUNES",
    1: "MARTES",
    2: "MIERCOLES",
    3: "JUEVES",
    4: "VIERNES",
    5: "SABADO",
    6: "DOMINGO",
}


@dataclass(frozen=True)
class Pieza:
    lote: str
    fecha_recepcion: date
    articulo_codigo: str
    articulo_clave: str
    articulo_nombre: str
    peso: float
    linea: int
    raw: str


@dataclass(frozen=True)
class BoxEtiqueta:
    box_numero: int
    lote: str
    articulo_codigo: str
    articulo_nombre: str
    fecha_recepcion: date
    fecha_entrada: date
    fecha_salida: date
    dia_salida: str
    dias_sal: int
    unidades: int
    total_piezas_rango: int
    rango_min: float
    rango_max: float
    rango_real_min: float
    rango_real_max: float
    etiquetas: int
    pesos: tuple[float, ...]
    albaran: str = ""
    partida: str = ""
    rango_pesos: str = ""


@dataclass(frozen=True)
class RangoSalazon:
    articulo_codigo: str
    articulo_nombre: str
    rango_min: float
    rango_max: float
    dias_sal: int
    unidades_box: int | None = None
    rango_texto: str = ""

    @property
    def range_label(self) -> str:
        if self.rango_texto:
            return self.rango_texto
        return f"{format_decimal(self.rango_min)} - {format_decimal(self.rango_max)} kg"


@dataclass(frozen=True)
class ResultadoGeneracion:
    lote: str
    total_lineas: int
    total_validas: int
    total_filtradas: int
    articulo_nombre: str
    fecha_recepcion: date
    fecha_salida: date
    boxes: tuple[BoxEtiqueta, ...]
    avisos: tuple[str, ...]

    @property
    def total_etiquetas(self) -> int:
        return sum(box.etiquetas for box in self.boxes)


def parse_decimal(text: str) -> float:
    clean = str(text).strip().replace(",", ".")
    if not clean:
        raise ValueError("valor vacio")
    return float(clean)


def format_decimal(value: float) -> str:
    text = f"{value:.2f}".replace(".", ",")
    return text.rstrip("0").rstrip(",")


def parse_date(text: str) -> date:
    value = str(text).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError("Introduce la fecha en formato dd/mm/aaaa.")


def normalize_lote_from_filename(filename: str) -> str:
    digits = "".join(re.findall(r"\d", Path(filename).stem))
    return digits[:6] if len(digits) >= 6 else (digits or Path(filename).stem[:6])


def normalize_article_code(value: str) -> str:
    clean = re.sub(r"\D", "", str(value or ""))
    return clean.lstrip("0") or clean


def load_article_legend(path: Path = ARTICULOS_PATH) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"No existe la lista de articulos: {path}")
    result: dict[str, str] = {}
    pattern = re.compile(r"^\s*(\d+)\s*[-;]\s*(.+?)\s*$")
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = pattern.match(line)
        if not match:
            raise ValueError(f"Linea {line_no} no valida en lista de articulos: {line}")
        code, name = match.groups()
        result[code.strip()] = name.strip()
    if not result:
        raise ValueError("La lista de articulos esta vacia.")
    return result


def _csv_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").strip().lower())


def _first_csv_value(row: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key, "")
        if str(value).strip():
            return str(value).strip()
    return ""


def _extract_weight_range_values(name: str) -> tuple[float, float, str]:
    text = str(name or "").strip()
    matches = list(re.finditer(r"(\d+(?:[,.]\d+)?)\s*-\s*(\d+(?:[,.]\d+)?)", text))
    if matches:
        match = matches[-1]
        min_weight = parse_decimal(match.group(1))
        max_weight = parse_decimal(match.group(2))
        if min_weight > max_weight:
            min_weight, max_weight = max_weight, min_weight
        return min_weight, max_weight, f"{format_decimal(min_weight)} - {format_decimal(max_weight)} kg"
    less_match = re.search(r"(?:^|\s)<\s*(\d+(?:[,.]\d+)?)\s*(?:kg|kgs|kilos)?\s*$", text, re.IGNORECASE)
    if less_match:
        max_weight = parse_decimal(less_match.group(1))
        return 0.0, max_weight, f"< {format_decimal(max_weight)} kg"
    greater_match = re.search(r"(?:^|\s)(?:\+|>)\s*(\d+(?:[,.]\d+)?)\s*(?:kg|kgs|kilos)?\s*$", text, re.IGNORECASE)
    if greater_match:
        min_weight = parse_decimal(greater_match.group(1))
        return min_weight, 999.0, f"> {format_decimal(min_weight)} kg"
    raise ValueError(f"No se encontro rango de peso en el nombre de articulo: {name}")


def article_name_without_weight_range(name: str) -> str:
    text = str(name or "").strip()
    matches = list(re.finditer(r"(?:\d+(?:[,.]\d+)?\s*-\s*\d+(?:[,.]\d+)?|[<+>]\s*\d+(?:[,.]\d+)?)", text))
    if not matches:
        return text
    match = matches[-1]
    prefix = text[: match.start()].rstrip()
    suffix = text[match.end() :].strip()
    suffix = re.sub(r"^(?:kg|kgs|kilos)\b\.?", "", suffix, flags=re.IGNORECASE).strip()
    clean = f"{prefix} {suffix}".strip()
    clean = re.sub(r"\s{2,}", " ", clean).strip(" -;")
    return clean or text


def load_salazon_ranges(path: Path = SALAZON_CONFIG_PATH) -> tuple[RangoSalazon, ...]:
    if not path.exists():
        return ()
    ranges: list[RangoSalazon] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(2048)
        handle.seek(0)
        has_header = bool(re.search(r"codigo|articulo|dias|sal", sample.splitlines()[0] if sample else "", re.IGNORECASE))
        reader = csv.DictReader(handle, delimiter=";") if has_header else csv.reader(handle, delimiter=";")
        for row_no, row in enumerate(reader, start=2 if has_header else 1):
            try:
                if has_header:
                    clean_row = {_csv_key(str(key or "")): str(value or "").strip() for key, value in row.items()}
                    code = _first_csv_value(clean_row, ("codigofac", "codigo", "numero", "articulo", "numeroarticulo", "codigoarticulo"))
                    name = _first_csv_value(clean_row, ("nombredelproducto", "nombreproducto", "nombre", "nombrearticulo", "descripcion"))
                    days_text = _first_csv_value(clean_row, ("diassal", "dias", "diassalazon", "diasensal"))
                    units_text = _first_csv_value(clean_row, ("unidadesbox", "unidadesporbox", "unidades", "udsbox", "uds"))
                else:
                    if len(row) < 2:
                        continue
                    code = str(row[0]).strip()
                    name = str(row[1]).strip()
                    days_text = str(row[2]).strip() if len(row) >= 3 else "0"
                    units_text = str(row[3]).strip() if len(row) >= 4 else ""
                if not code or not name:
                    continue
                min_weight, max_weight, range_label = _extract_weight_range_values(name)
                units_value = None
                if units_text:
                    units_value = max(1, int(float(units_text.replace(",", "."))))
                ranges.append(
                    RangoSalazon(
                        articulo_codigo=normalize_article_code(code),
                        articulo_nombre=name,
                        rango_min=min_weight,
                        rango_max=max_weight,
                        dias_sal=int(float((days_text or "0").replace(",", "."))),
                        unidades_box=units_value,
                        rango_texto=range_label,
                    )
                )
            except Exception as exc:
                raise ValueError(f"Linea {row_no} no valida en config_salazon.csv: {exc}") from exc
    return tuple(ranges)


def _article_code_priority_key(code: str) -> tuple[int, int, str]:
    digits = re.sub(r"\D", "", str(code or ""))
    numeric_code = int(digits or "0")
    return (-len(digits), numeric_code, str(code or ""))


def article_options(path: Path = SALAZON_CONFIG_PATH) -> list[tuple[str, str, str]]:
    ranges = load_salazon_ranges(path)
    if ranges:
        return [
            (item.articulo_codigo, item.articulo_nombre, f"{item.articulo_codigo} - {item.articulo_nombre}")
            for item in sorted(
                ranges,
                key=lambda item: (
                    _article_code_priority_key(item.articulo_codigo),
                    item.rango_min,
                    item.rango_max,
                    item.articulo_nombre,
                ),
            )
        ]
    legend = load_article_legend(ARTICULOS_PATH)
    return [(code, name, f"{code} - {name}") for code, name in sorted(legend.items(), key=lambda item: _article_code_priority_key(item[0]))]


def unique_article_options(path: Path = SALAZON_CONFIG_PATH) -> list[tuple[str, str, str]]:
    ranges = load_salazon_ranges(path)
    if ranges:
        result: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in sorted(
            ranges,
            key=lambda item: (
                _article_code_priority_key(item.articulo_codigo),
                article_name_without_weight_range(item.articulo_nombre),
                item.rango_min,
                item.rango_max,
            ),
        ):
            name = article_name_without_weight_range(item.articulo_nombre)
            key = (item.articulo_codigo, name.lower())
            if key in seen:
                continue
            seen.add(key)
            result.append((item.articulo_codigo, name, f"{item.articulo_codigo} - {name}"))
        return result
    return article_options(path)


def salazon_ranges_for_article(article_code: str, ranges: Iterable[RangoSalazon] | None = None) -> tuple[RangoSalazon, ...]:
    ranges = tuple(ranges) if ranges is not None else load_salazon_ranges()
    code = normalize_article_code(article_code)
    matches = [item for item in ranges if normalize_article_code(item.articulo_codigo) == code]
    return tuple(sorted(matches, key=lambda item: (item.rango_min, item.rango_max, item.dias_sal, item.articulo_nombre)))


def save_salazon_range_units(path: Path, target: RangoSalazon, units_per_box: int) -> None:
    raise RuntimeError("La aplicacion de pesos no modifica config_salazon.csv desde el editor.")


def extract_weight_range(text: str) -> str:
    try:
        return _extract_weight_range_values(text)[2]
    except Exception:
        return ""


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _center_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font, fill="black") -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = box[0] + ((box[2] - box[0]) - width) // 2
    y = box[1] + ((box[3] - box[1]) - height) // 2
    draw.text((x, y), text, font=font, fill=fill)


DEFAULT_LABEL_TEMPLATE = {
    "version": 1,
    "base_width": BASE_LABEL_WIDTH,
    "base_height": BASE_LABEL_HEIGHT,
    "label_width_mm": LABEL_WIDTH_MM,
    "label_height_mm": LABEL_HEIGHT_MM,
    "safe_margin_mm": PRINT_SAFE_MARGIN_MM,
    "background": "white",
    "elements": [
        {"id": "outer_border", "type": "rect", "x": 12, "y": 12, "w": BASE_LABEL_WIDTH - 24, "h": BASE_LABEL_HEIGHT - 24, "outline": "black", "line_width": 5, "visible": True, "locked": True},
        {"id": "header_bar", "type": "rect", "x": 12, "y": 12, "w": BASE_LABEL_WIDTH - 24, "h": 132, "fill": "black", "outline": "black", "line_width": 1, "visible": True, "locked": True},
        {"id": "titulo", "type": "text", "text": "ETIQUETA PESOS", "x": 26, "y": 24, "w": BASE_LABEL_WIDTH - 52, "h": 108, "font_size": 66, "min_size": 46, "bold": True, "fill": "white", "align": "center", "visible": True},
        {"id": "articulo", "type": "field", "label": "ARTICULO", "key": "articulo_nombre", "x": 36, "y": 200, "w": BASE_LABEL_WIDTH - 72, "h": 410, "label_size": 48, "value_size": 88, "min_size": 44, "bold": True, "label_fill": "#373737", "fill": "#0C0C0C", "visible": True, "wrap": True, "line_spacing": 1.08},
        {"id": "linea_articulo", "type": "line", "x1": 36, "y1": 650, "x2": BASE_LABEL_WIDTH - 36, "y2": 650, "fill": "#878787", "line_width": 2, "visible": True},
        {"id": "albaran", "type": "field", "label": "ALBARAN", "key": "albaran", "x": 36, "y": 706, "w": BASE_LABEL_WIDTH - 72, "h": 184, "label_size": 48, "value_size": 116, "min_size": 70, "bold": True, "label_fill": "#373737", "fill": "#0C0C0C", "visible": True},
        {"id": "linea_albaran", "type": "line", "x1": 36, "y1": 940, "x2": BASE_LABEL_WIDTH - 36, "y2": 940, "fill": "#878787", "line_width": 2, "visible": True},
        {"id": "partida", "type": "field", "label": "PARTIDA", "key": "partida", "x": 36, "y": 996, "w": BASE_LABEL_WIDTH - 72, "h": 184, "label_size": 48, "value_size": 116, "min_size": 70, "bold": True, "label_fill": "#373737", "fill": "#0C0C0C", "visible": True},
        {"id": "linea_partida", "type": "line", "x1": 36, "y1": 1248, "x2": BASE_LABEL_WIDTH - 36, "y2": 1248, "fill": "#878787", "line_width": 2, "visible": True},
        {"id": "rango_label", "type": "text", "text": "RANGO DE PESOS", "x": 36, "y": 1310, "w": BASE_LABEL_WIDTH - 72, "h": 64, "font_size": 44, "min_size": 34, "bold": True, "fill": "#373737", "align": "center", "visible": True},
        {"id": "rango_pesos", "type": "value", "key": "rango_pesos", "x": 36, "y": 1390, "w": BASE_LABEL_WIDTH - 72, "h": 220, "font_size": 170, "min_size": 82, "bold": True, "fill": "black", "align": "center", "visible": True},
        {"id": "pie", "type": "value", "template": "{articulo_codigo} | ALB {albaran} | PART {partida}", "x": 36, "y": BASE_LABEL_HEIGHT - 118, "w": BASE_LABEL_WIDTH - 72, "h": 70, "font_size": 40, "min_size": 26, "bold": True, "fill": "black", "align": "center", "visible": True},
    ],
}


def safe_margin_mm_from_template(template: dict | None = None) -> float:
    template = template or {}
    try:
        margin = float(template.get("safe_margin_mm", PRINT_SAFE_MARGIN_MM))
    except Exception:
        margin = PRINT_SAFE_MARGIN_MM
    return max(SAFE_MARGIN_MIN_MM, min(SAFE_MARGIN_MAX_MM, margin))


def _safe_margin_for_template(template: dict) -> tuple[int, int, int, int]:
    label_width_mm = float(template.get("label_width_mm", LABEL_WIDTH_MM) or LABEL_WIDTH_MM)
    label_height_mm = float(template.get("label_height_mm", LABEL_HEIGHT_MM) or LABEL_HEIGHT_MM)
    base_width = int(template.get("base_width", BASE_LABEL_WIDTH) or BASE_LABEL_WIDTH)
    base_height = int(template.get("base_height", BASE_LABEL_HEIGHT) or BASE_LABEL_HEIGHT)
    safe_margin_mm = safe_margin_mm_from_template(template)
    margin_x = int(base_width * safe_margin_mm / max(label_width_mm, 1))
    margin_y = int(base_height * safe_margin_mm / max(label_height_mm, 1))
    return margin_x, margin_y, base_width - margin_x, base_height - margin_y


def _clamp_element_to_box(element: dict, safe_box: tuple[int, int, int, int]) -> None:
    sx1, sy1, sx2, sy2 = safe_box
    kind = str(element.get("type", ""))
    if kind == "line":
        for key in ("x1", "x2"):
            element[key] = min(max(int(element.get(key, sx1)), sx1), sx2)
        for key in ("y1", "y2"):
            element[key] = min(max(int(element.get(key, sy1)), sy1), sy2)
        return
    if kind not in {"rect", "text", "value", "field"}:
        return
    x = int(element.get("x", sx1))
    y = int(element.get("y", sy1))
    width = int(element.get("w", max(1, sx2 - sx1)))
    height = int(element.get("h", 180 if kind == "field" else 70))
    max_width = max(1, sx2 - sx1)
    max_height = max(1, sy2 - sy1)
    width = min(max(width, 1), max_width)
    height = min(max(height, 1), max_height)
    element["x"] = min(max(x, sx1), sx2 - width)
    element["y"] = min(max(y, sy1), sy2 - height)
    element["w"] = width
    element["h"] = height


def normalize_template_to_safe_area(template: dict) -> dict:
    normalized = json.loads(json.dumps(template))
    normalized.setdefault("label_width_mm", LABEL_WIDTH_MM)
    normalized.setdefault("label_height_mm", LABEL_HEIGHT_MM)
    normalized.setdefault("safe_margin_mm", PRINT_SAFE_MARGIN_MM)
    safe_box = _safe_margin_for_template(normalized)
    for element in normalized.get("elements", []):
        if isinstance(element, dict) and element.get("visible", True):
            _clamp_element_to_box(element, safe_box)
    return normalized


def _editable_config_dir() -> Path:
    path = APP_DIR / "config"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _template_path() -> Path:
    editable = APP_DIR / "config" / "plantilla_etiqueta_pesos.json"
    if editable.exists():
        return editable
    bundled = RESOURCE_DIR / "config" / "plantilla_etiqueta_pesos.json"
    if bundled.exists():
        return bundled
    return editable


def load_label_template() -> dict:
    path = _template_path()
    if not path.exists():
        template = normalize_template_to_safe_area(DEFAULT_LABEL_TEMPLATE)
        save_label_template(template)
        return template
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "elements" not in data:
            raise ValueError("Plantilla sin elementos.")
        return normalize_template_to_safe_area(data)
    except Exception:
        return normalize_template_to_safe_area(DEFAULT_LABEL_TEMPLATE)


def save_label_template(template: dict) -> Path:
    path = _editable_config_dir() / "plantilla_etiqueta_pesos.json"
    if path.exists():
        backup_dir = path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, backup_dir / f"plantilla_etiqueta_backup_{stamp}.json")
    path.write_text(json.dumps(normalize_template_to_safe_area(template), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def reset_label_template() -> Path:
    return save_label_template(normalize_template_to_safe_area(DEFAULT_LABEL_TEMPLATE))


def _label_values(box: BoxEtiqueta) -> dict[str, str]:
    rango = getattr(box, "rango_pesos", "") or f"{format_decimal(box.rango_min)} - {format_decimal(box.rango_max)} kg"
    albaran = str(getattr(box, "albaran", "") or "").strip()
    partida = str(getattr(box, "partida", "") or box.lote).strip()
    return {
        "box_numero": str(box.box_numero),
        "titulo": "ETIQUETA PESOS",
        "dia_salida": box.dia_salida,
        "fecha_salida": box.fecha_salida.strftime("%d/%m/%Y"),
        "fecha_recepcion": box.fecha_recepcion.strftime("%d/%m/%Y"),
        "fecha_entrada": box.fecha_entrada.strftime("%d/%m/%Y"),
        "lote": partida,
        "albaran": albaran,
        "numero_albaran": albaran,
        "partida": partida,
        "numero_partida": partida,
        "articulo_codigo": box.articulo_codigo,
        "articulo_nombre": box.articulo_nombre,
        "articulo": box.articulo_nombre,
        "total_piezas_rango": str(box.total_piezas_rango),
        "unidades": str(box.unidades),
        "dias_sal": str(box.dias_sal),
        "rango_min": format_decimal(box.rango_min),
        "rango_max": format_decimal(box.rango_max),
        "rango_peso": rango,
        "rango_pesos": rango,
        "rango_real": rango,
        "etiquetas": str(box.etiquetas),
        "pie": f"{box.articulo_codigo} | ALB {albaran} | PART {partida}",
    }


def render_label(box: BoxEtiqueta, dpi: int = DEFAULT_DPI, template: dict | None = None) -> Image.Image:
    width = int(LABEL_WIDTH_MM / 25.4 * dpi)
    height = int(LABEL_HEIGHT_MM / 25.4 * dpi)
    template = template or load_label_template()
    image = Image.new("RGB", (width, height), template.get("background", "white"))
    draw = ImageDraw.Draw(image)
    base_width = int(template.get("base_width", BASE_LABEL_WIDTH) or BASE_LABEL_WIDTH)
    scale = width / base_width

    def s(value) -> int:
        return int(float(value) * scale)

    def fit_font(text: str, max_width: int, start: int, minimum: int, bold: bool = True):
        step = max(s(2), 1)
        for size in range(s(start), s(minimum) - 1, -step):
            font = _font(max(size, 1), bold)
            bbox = draw.textbbox((0, 0), text, font=font)
            if bbox[2] - bbox[0] <= max_width:
                return font
        return _font(s(minimum), bold)

    def wrap_lines(text: str, font, max_width: int) -> list[str]:
        lines: list[str] = []
        for raw_line in str(text).splitlines() or [""]:
            words = raw_line.split()
            if not words:
                lines.append("")
                continue
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                bbox = draw.textbbox((0, 0), candidate, font=font)
                if bbox[2] - bbox[0] <= max_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines

    def fit_multiline_font(text: str, max_width: int, max_height: int, start: int, minimum: int, bold: bool = True, spacing: float = 1.08):
        step = max(s(2), 1)
        for size in range(s(start), s(minimum) - 1, -step):
            font = _font(max(size, 1), bold)
            lines = wrap_lines(text, font, max_width)
            line_h = max(draw.textbbox((0, 0), "Ag", font=font)[3], 1)
            if line_h * spacing * len(lines) <= max_height:
                return font, lines
        font = _font(s(minimum), bold)
        return font, wrap_lines(text, font, max_width)

    def draw_aligned_text(area: tuple[int, int, int, int], text: str, font, fill, align: str) -> None:
        if align == "center":
            _center_text(draw, area, text, font, fill=fill)
            return
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = area[0] if align == "left" else area[2] - text_w
        draw.text((x, area[1]), text, font=font, fill=fill)

    def draw_text_block(area: tuple[int, int, int, int], text: str, font, fill, align: str, spacing: float = 1.08) -> None:
        lines = wrap_lines(text, font, max(area[2] - area[0], 1))
        line_h = max(draw.textbbox((0, 0), "Ag", font=font)[3], 1)
        y = area[1]
        for line in lines:
            if y > area[3]:
                break
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            if align == "center":
                x = area[0] + ((area[2] - area[0]) - line_w) // 2
            elif align == "right":
                x = area[2] - line_w
            else:
                x = area[0]
            draw.text((x, y), line, font=font, fill=fill)
            y += int(line_h * spacing)

    values = _label_values(box)

    def resolve_text(element: dict, default: str = "") -> str:
        template_text = str(element.get("template", "")).strip()
        if template_text:
            try:
                return template_text.format_map(values)
            except Exception:
                return template_text
        key = str(element.get("key", "")).strip()
        if key:
            return values.get(key, "")
        return default

    for element in template.get("elements", []):
        if not element.get("visible", True):
            continue
        kind = element.get("type", "")
        if kind == "rect":
            x1, y1 = s(element.get("x", 0)), s(element.get("y", 0))
            x2 = x1 + s(element.get("w", 0))
            y2 = y1 + s(element.get("h", 0))
            draw.rectangle((x1, y1, x2, y2), fill=element.get("fill"), outline=element.get("outline"), width=max(s(element.get("line_width", 1)), 1))
        elif kind == "line":
            draw.line((s(element.get("x1", 0)), s(element.get("y1", 0)), s(element.get("x2", 0)), s(element.get("y2", 0))), fill=element.get("fill", "black"), width=max(s(element.get("line_width", 1)), 1))
        elif kind in {"text", "value"}:
            text = str(element.get("text", "") if kind == "text" and not element.get("template") else resolve_text(element, str(element.get("text", ""))))
            area = (s(element.get("x", 0)), s(element.get("y", 0)), s(element.get("x", 0)) + s(element.get("w", 0)), s(element.get("y", 0)) + s(element.get("h", 70)))
            if element.get("wrap", False):
                font, _lines = fit_multiline_font(text, max(area[2] - area[0], 1), max(area[3] - area[1], 1), int(element.get("font_size", 42)), int(element.get("min_size", 28)), bool(element.get("bold", True)), float(element.get("line_spacing", 1.08)))
                draw_text_block(area, text, font, element.get("fill", "black"), str(element.get("align", "left")), float(element.get("line_spacing", 1.08)))
            else:
                font = fit_font(text, max(area[2] - area[0], 1), int(element.get("font_size", 42)), int(element.get("min_size", 28)), bool(element.get("bold", True)))
                draw_aligned_text(area, text, font, element.get("fill", "black"), str(element.get("align", "left")))
        elif kind == "field":
            x, y, max_width = s(element.get("x", 0)), s(element.get("y", 0)), s(element.get("w", 100))
            label = str(element.get("label", ""))
            value = str(resolve_text(element))
            label_font = _font(s(element.get("label_size", 41)), bool(element.get("bold", True)))
            draw.text((x, y), label, font=label_font, fill=element.get("label_fill", "#373737"))
            value_y = y + s(element.get("value_offset", 52))
            value_area = (x, value_y, x + max_width, y + s(element.get("h", 180)))
            if element.get("wrap", False):
                value_font, _lines = fit_multiline_font(value, max_width, max(value_area[3] - value_area[1], 1), int(element.get("value_size", 68)), int(element.get("min_size", 42)), bool(element.get("bold", True)), float(element.get("line_spacing", 1.08)))
                draw_text_block(value_area, value, value_font, element.get("fill", "#0C0C0C"), str(element.get("align", "left")), float(element.get("line_spacing", 1.08)))
            else:
                value_font = fit_font(value, max_width, int(element.get("value_size", 68)), int(element.get("min_size", 42)), bool(element.get("bold", True)))
                draw.text((x, value_y), value, font=value_font, fill=element.get("fill", "#0C0C0C"))
    return image.convert("L").convert("RGB")


def expand_labels(boxes: Iterable[BoxEtiqueta]) -> list[BoxEtiqueta]:
    expanded: list[BoxEtiqueta] = []
    for box in boxes:
        expanded.extend([box] * max(int(box.etiquetas), 1))
    return expanded


def save_label_contact_sheet(boxes: Iterable[BoxEtiqueta], output_path: Path, dpi: int = 120, template: dict | None = None) -> None:
    rendered = [render_label(box, dpi=dpi, template=template) for box in boxes]
    if not rendered:
        raise ValueError("No hay etiquetas que guardar.")
    cols = 2
    gap = 24
    rows = (len(rendered) + cols - 1) // cols
    cell_w = rendered[0].width
    cell_h = rendered[0].height
    sheet = Image.new("RGB", (cols * cell_w + (cols + 1) * gap, rows * cell_h + (rows + 1) * gap), "white")
    for index, image in enumerate(rendered):
        row, col = divmod(index, cols)
        x = gap + col * (cell_w + gap)
        y = gap + row * (cell_h + gap)
        sheet.paste(image, (x, y))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def calculate_centered_print_rect(
    physical_width: int,
    physical_height: int,
    printable_width: int,
    printable_height: int,
    offset_x: int,
    offset_y: int,
    dpi_x: int,
    dpi_y: int,
    image_width: int,
    image_height: int,
    safe_margin_mm: float = PRINT_SAFE_MARGIN_MM,
) -> tuple[int, int, int, int]:
    physical_width = max(int(physical_width or printable_width), 1)
    physical_height = max(int(physical_height or printable_height), 1)
    printable_width = max(int(printable_width or physical_width), 1)
    printable_height = max(int(printable_height or physical_height), 1)
    dpi_x = max(int(dpi_x or DEFAULT_DPI), 1)
    dpi_y = max(int(dpi_y or DEFAULT_DPI), 1)
    safe_x = min(int(safe_margin_mm / 25.4 * dpi_x), max((physical_width - 1) // 2, 0))
    safe_y = min(int(safe_margin_mm / 25.4 * dpi_y), max((physical_height - 1) // 2, 0))
    image_ratio = max(image_width, 1) / max(image_height, 1)
    target_area_w = max(1, physical_width - (safe_x * 2))
    target_area_h = max(1, physical_height - (safe_y * 2))
    if target_area_w / target_area_h > image_ratio:
        target_h = target_area_h
        target_w = int(target_h * image_ratio)
    else:
        target_w = target_area_w
        target_h = int(target_w / image_ratio)
    left_physical = safe_x + (target_area_w - target_w) // 2
    top_physical = safe_y + (target_area_h - target_h) // 2
    left = left_physical - int(offset_x or 0)
    top = top_physical - int(offset_y or 0)
    return left, top, left + target_w, top + target_h


def list_windows_printers() -> list[str]:
    try:
        import win32print

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return sorted({item[2] for item in win32print.EnumPrinters(flags)})
    except Exception:
        return []


def default_windows_printer() -> str:
    try:
        import win32print

        return win32print.GetDefaultPrinter()
    except Exception:
        return ""


def print_labels_windows(boxes: Iterable[BoxEtiqueta], printer_name: str | None = None, template: dict | None = None) -> int:
    try:
        import win32con
        import win32ui
        from PIL import ImageWin
    except Exception as exc:
        raise RuntimeError("Para imprimir en Windows instala pywin32. Puedes guardar PNG para pruebas.") from exc

    labels = expand_labels(tuple(boxes))
    if not labels:
        raise ValueError("No hay etiquetas que imprimir.")
    printer = printer_name or default_windows_printer()
    if not printer:
        raise ValueError("Selecciona una impresora.")

    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(printer)
    printable_width = hdc.GetDeviceCaps(win32con.HORZRES)
    printable_height = hdc.GetDeviceCaps(win32con.VERTRES)
    physical_width = hdc.GetDeviceCaps(win32con.PHYSICALWIDTH) or printable_width
    physical_height = hdc.GetDeviceCaps(win32con.PHYSICALHEIGHT) or printable_height
    offset_x = hdc.GetDeviceCaps(win32con.PHYSICALOFFSETX)
    offset_y = hdc.GetDeviceCaps(win32con.PHYSICALOFFSETY)
    dpi_x = max(hdc.GetDeviceCaps(win32con.LOGPIXELSX), 1)
    dpi_y = max(hdc.GetDeviceCaps(win32con.LOGPIXELSY), 1)

    hdc.StartDoc("Etiquetas pesos")
    try:
        for box in labels:
            image = render_label(box, dpi=DEFAULT_DPI, template=template).convert("RGB")
            rect = calculate_centered_print_rect(
                physical_width,
                physical_height,
                printable_width,
                printable_height,
                offset_x,
                offset_y,
                dpi_x,
                dpi_y,
                image.width,
                image.height,
            )
            dib = ImageWin.Dib(image)
            hdc.StartPage()
            dib.draw(hdc.GetHandleOutput(), rect)
            hdc.EndPage()
    finally:
        hdc.EndDoc()
        hdc.DeleteDC()
    return len(labels)


def validate_workday(day: date) -> tuple[bool, str]:
    return True, ""


def holidays_for_year(year: int, path: Path = FESTIVOS_PATH) -> dict[date, str]:
    return {}


def calculate_exit_date(entry_date: date, days_in_salt: int) -> date:
    return entry_date + timedelta(days=days_in_salt)


def parse_partida_file(path: Path, legend: dict[str, str]) -> list[Pieza]:
    raise NotImplementedError("Esta aplicacion no lee fichero TXT; selecciona el articulo manualmente.")


def build_boxes(*_args, **_kwargs) -> ResultadoGeneracion:
    raise NotImplementedError("Esta aplicacion genera etiquetas de pesos manuales.")

from __future__ import annotations

from datetime import date

from app_etiquetado_pesos import EtiquetadoPesosApp
from logica_etiquetas import BoxEtiqueta, _label_values, load_salazon_ranges, unique_article_options


def test_article_options_display_only_names(tmp_path) -> None:
    config = tmp_path / "config_salazon.csv"
    config.write_text(
        "CODIGO FAC;Nombre del producto;Dias SAL;Unidades/Box\n"
        "1001;JAMON CURADO 8-10;8;12\n"
        "1001;JAMON CURADO 10-12;9;12\n"
        "1002;PALETA CURADA 5-7;7;16\n",
        encoding="utf-8",
    )

    options = unique_article_options(config)

    assert options == [
        ("1001", "JAMON CURADO", "JAMON CURADO"),
        ("1002", "PALETA CURADA", "PALETA CURADA"),
    ]


def test_article_options_group_percentages_and_keep_ranges_associated(tmp_path) -> None:
    config = tmp_path / "config_salazon.csv"
    config.write_text(
        "CODIGO FAC;Nombre del producto;Dias SAL;Unidades/Box\n"
        "1001;JAMON RESERVA 50% 7-8 kg;8;12\n"
        "1001;JAMON RESERVA 100% 8 - 9 kg;9;12\n"
        "1001;JAMON RESERVA 100% 9-10 kg;10;12\n"
        "1002;JAMON RESERVA ESPECIAL 75 % 7,5\u20138,5 kg;8;12\n",
        encoding="utf-8",
    )

    records = load_salazon_ranges(config)

    assert unique_article_options(config) == [
        ("1001", "JAMON RESERVA", "JAMON RESERVA \u2014 50%, 100%"),
        ("1002", "JAMON RESERVA ESPECIAL", "JAMON RESERVA ESPECIAL \u2014 75%"),
    ]
    assert [(item.articulo_nombre, item.porcentaje, item.range_label) for item in records] == [
        ("JAMON RESERVA", "50%", "7 - 8 kg"),
        ("JAMON RESERVA", "100%", "8 - 9 kg"),
        ("JAMON RESERVA", "100%", "9 - 10 kg"),
        ("JAMON RESERVA ESPECIAL", "75%", "7,5 - 8,5 kg"),
    ]


def test_article_without_percentage_or_range_is_loaded(tmp_path) -> None:
    config = tmp_path / "config_salazon.csv"
    config.write_text(
        "CODIGO FAC;Nombre del producto;Dias SAL;Unidades/Box\n"
        "1003;PALETA CURADA;7;16\n",
        encoding="utf-8",
    )

    record = load_salazon_ranges(config)[0]

    assert record.articulo_nombre == "PALETA CURADA"
    assert record.porcentaje == ""
    assert record.range_label == ""


def test_article_options_remove_less_than_and_greater_than_weight_bounds(tmp_path) -> None:
    config = tmp_path / "config_salazon.csv"
    config.write_text(
        "CODIGO FAC;Nombre del producto;Dias SAL;Unidades/Box\n"
        "2001;JAMON CEBO IBERICO <13 100%;8;12\n"
        "2001;JAMON CEBO IBERICO +19 100%;8;12\n",
        encoding="utf-8",
    )

    records = load_salazon_ranges(config)

    assert unique_article_options(config) == [
        ("2001", "JAMON CEBO IBERICO", "JAMON CEBO IBERICO \u2014 100%"),
    ]
    assert [item.range_label for item in records] == ["< 13 kg", "> 19 kg"]


class _StringValue:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value


def test_article_selection_keeps_code_lookup_hidden_from_display() -> None:
    app = EtiquetadoPesosApp.__new__(EtiquetadoPesosApp)
    app.article_values = [("1001", "JAMON CURADO", "JAMON CURADO")]
    app.var_articulo = _StringValue("1001")

    assert app._selected_article() == ("1001", "JAMON CURADO", "JAMON CURADO")


def test_selected_range_preserves_percentage_position_in_label_name(tmp_path) -> None:
    config = tmp_path / "config_salazon.csv"
    config.write_text(
        "CODIGO FAC;Nombre del producto;Dias SAL;Unidades/Box\n"
        "1001;JAMON CEBO 50% IBERICO 7-8 kg;8;12\n"
        "1001;JAMON CEBO 100% IBERICO 7-8 kg;8;12\n",
        encoding="utf-8",
    )
    app = EtiquetadoPesosApp.__new__(EtiquetadoPesosApp)
    app.article_values = unique_article_options(config)
    app.salazon_ranges = load_salazon_ranges(config)
    app.var_articulo = _StringValue("JAMON CEBO IBERICO \u2014 50%, 100%")
    app.var_rango = _StringValue("7 - 8 kg \u2014 100%")
    app.var_albaran = _StringValue("A-1")
    app.var_partida = _StringValue("P-1")
    app.var_etiquetas = _StringValue("1")
    app.range_values = list(app.salazon_ranges)

    label = app._build_label()
    values = _label_values(label)

    assert label.articulo_nombre == "JAMON CEBO 100% IBERICO"
    assert label.rango_pesos == "7 - 8 kg"
    assert label.porcentaje == "100%"
    assert values["articulo_nombre"] == "JAMON CEBO 100% IBERICO"
    assert values["rango_pesos"] == "7 - 8 kg"
    assert values["porcentaje"] == "100%"


def test_label_values_do_not_add_a_missing_range_to_the_article_name() -> None:
    label = BoxEtiqueta(
        box_numero=1,
        lote="P-1",
        articulo_codigo="1001",
        articulo_nombre="JAMON RESERVA",
        fecha_recepcion=date.today(),
        fecha_entrada=date.today(),
        fecha_salida=date.today(),
        dia_salida="",
        dias_sal=0,
        unidades=0,
        total_piezas_rango=0,
        rango_min=7.0,
        rango_max=8.0,
        rango_real_min=7.0,
        rango_real_max=8.0,
        etiquetas=1,
        pesos=(),
        rango_pesos="7 - 8 kg",
    )

    values = _label_values(label)

    assert values["articulo_nombre"] == "JAMON RESERVA"
    assert values["rango_pesos"] == "7 - 8 kg"

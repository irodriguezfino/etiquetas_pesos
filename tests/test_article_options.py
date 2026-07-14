from __future__ import annotations

from app_etiquetado_pesos import EtiquetadoPesosApp
from logica_etiquetas import unique_article_options


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

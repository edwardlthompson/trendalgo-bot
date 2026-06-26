from trendalgo.export.tax import tax_csv


def test_tax_csv_header() -> None:
    csv_text = tax_csv([{"pair": "ETH/USD", "profit_abs": 5.0}])
    assert csv_text.startswith("pair,")
